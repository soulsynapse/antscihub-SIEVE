"""cv2 BGR decoder with two cursors on one file: the walk's, which only ever steps, and the scrub's,
which takes the display's jumps so they never land on the walk's. A sequential read steps the cursor
in use; a short jump ahead reads through, since a seek decodes from the last keyframe anyway and
costs what the decoder has measured it to cost here; anything else seeks. A seek lands one row
short and reads through it, because the tools that difference frames ask for row - 1 right after
row, and that second ask would otherwise be a second seek."""
import os
import threading
import time
from collections import OrderedDict
from contextlib import contextmanager
from functools import lru_cache

import cv2
import numpy as np

LOOKBEHIND = 1          # rows a seek lands short of its target and reads through
SEEK_GUESS = 12.0       # steps a seek is taken to cost until one has been measured here
LUMA_FORMATS = {b"I420"}    # planar 8-bit 4:2:0: unconverted, cv2 hands out the luma plane as rows x cols
QUIET = False   # play() sets it once C-level stderr goes nowhere; the plugin warns on every unconverted frame otherwise
_QUIET_LEVELS = {"OFF", "DISABLED", "SILENT", "FATAL", "ERROR", "0", "1", "2"}


def _quiet():
    return QUIET or os.environ.get("OPENCV_LOG_LEVEL", "").upper() in _QUIET_LEVELS


def frame_count(path, cap=None):
    """Rows in the file: the container's claim, or, for a raw stream that makes none, the packets
    demuxed without decoding."""
    own = cap is None
    cap = cap or cv2.VideoCapture(str(path), cv2.CAP_FFMPEG)
    try:
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if n > 0:
            return n
        scan = cv2.VideoCapture(str(path), cv2.CAP_FFMPEG)
        scan.set(cv2.CAP_PROP_FORMAT, -1)
        n = 0
        while scan.read()[0]:
            n += 1
        scan.release()
        return n
    finally:
        if own:
            cap.release()


@lru_cache(maxsize=16)
def _probe(path, mtime):
    cap = cv2.VideoCapture(path, cv2.CAP_FFMPEG)
    try:
        if not cap.isOpened():
            raise IOError(f"cannot open {path}")
        return (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                cap.get(cv2.CAP_PROP_FPS) or 30.0, frame_count(path, cap))
    finally:
        cap.release()


def probe(src):
    """(width, height, fps, count) via cv2, cached per path and mtime. The count is the container's
    claim, or a packet scan of a raw stream; the decoder trusts the stream over either."""
    src = str(src)
    return _probe(src, os.stat(src).st_mtime)


class _Cursor:
    __slots__ = ("cap", "pos", "path", "luma")

    def __init__(self, path, luma):
        self.path, self.luma, self.cap = path, luma, None
        self.reopen()

    def reopen(self):
        """A fresh capture at row 0; the only way back in a stream with no index."""
        if self.cap is not None:
            self.cap.release()
        self.cap = cv2.VideoCapture(self.path, cv2.CAP_FFMPEG)
        self.pos = 0
        self.convert(not self.luma)

    def convert(self, on):
        self.luma = not on
        self.cap.set(cv2.CAP_PROP_CONVERT_RGB, 1 if on else 0)


class Decoder:
    def __init__(self, path, cache_bytes=4 << 30):
        self.path = str(path)
        walk = _Cursor(self.path, luma=False)
        if not walk.cap.isOpened():
            raise IOError(f"cannot open {path}")
        self.cap = walk.cap
        self.indexed = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)) > 0
        self.count = frame_count(self.path, self.cap)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fmt = int(self.cap.get(cv2.CAP_PROP_CODEC_PIXEL_FORMAT)).to_bytes(4, "little", signed=True)
        self.luma = fmt in LUMA_FORMATS and _quiet()
        self._output, self._scale = "bgr", 1.0
        self._cursors = {"walk": walk, "scrub": None}   # the scrub's opens on its first use
        self._use = "walk"
        self._cache = OrderedDict()
        self._cache_bytes, self._cache_limit = 0, cache_bytes
        self._cache_lock = threading.Lock()     # the dict only: a GUI peek never waits on a decode
        self._cap_lock = threading.Lock()       # the captures and the cursor in use
        self.decodes = self.seeks = 0
        self.reads = self.cache_hits = 0        # read() calls, and those the cache answered
        self.step_ms = self.seek_ms = None      # running means of what a step and a seek cost on this file
        self.on_evict = None                    # (row, bytes) for each frame the cache drops, after the lock

    @contextmanager
    def scrub(self):
        """Reads inside run on the scrub cursor; the walk's stays where the walk left it."""
        with self._cap_lock:
            self._use = "scrub"
        try:
            yield
        finally:
            with self._cap_lock:
                self._use = "walk"

    @property
    def output(self):
        """What read() hands out: "bgr" as decoded, or "gray", before it is cached. On an 8-bit 4:2:0
        stream with QUIET set, gray is the decoder's luma plane and the YUV-to-BGR conversion is
        skipped; otherwise it is converted from BGR. Setting it empties the cache."""
        return self._output

    @output.setter
    def output(self, value):
        if value not in ("bgr", "gray"):
            raise ValueError(f"decoder output {value!r}; one of bgr, gray")
        with self._cache_lock:
            if value == self._output:
                return
            self._output, self._cache_bytes = value, 0
            self._cache.clear()

    def _luma_read(self):
        return self.luma and self._output == "gray"

    @property
    def scale(self):
        """The factor frames are resized by before they are cached, 1.0 as decoded; INTER_AREA, as
        tools/rescale does. Setting it empties the cache."""
        return self._scale

    @scale.setter
    def scale(self, value):
        value = float(value)
        if not 0.0 < value <= 1.0:
            raise ValueError(f"decoder scale {value}; in (0, 1]")
        with self._cache_lock:
            if value == self._scale:
                return
            self._scale, self._cache_bytes = value, 0
            self._cache.clear()

    def _shape(self):
        """(rows, cols) a frame has after the scale, as cv2.resize rounds it."""
        s = self._scale
        return (self.height, self.width) if s == 1.0 else (int(round(self.height * s)), int(round(self.width * s)))

    def _fits(self, f):
        # a frame of the other kind or size, decoded before a switch and landing after it, is not served
        return (f.ndim == 2) == (self._output == "gray") and f.shape[:2] == self._shape()

    def cached(self, row):
        """Cache-only read; never touches a capture. Safe from the GUI thread."""
        with self._cache_lock:
            f = self._cache.get(row)
            return f if f is None or self._fits(f) else None

    @property
    def cache_bytes(self):
        return self._cache_bytes

    @property
    def cache_limit(self):
        return self._cache_limit

    def read(self, row) -> np.ndarray:
        self.reads += 1
        f = self.cached(row)
        if f is not None:
            self.cache_hits += 1
            return f
        with self._cap_lock:
            cur = self._cursors[self._use]
            if cur is None:
                cur = self._cursors[self._use] = _Cursor(self.path, self._luma_read())
            if cur.luma != self._luma_read():
                cur.convert(not self._luma_read())   # here, under the lock a read holds, never from the setter
            ahead = row - cur.pos
            if not self.indexed:
                if ahead < 0:
                    cur.reopen()   # a raw stream seeks nowhere: back means from the top
                    self.seeks += 1
            elif not 0 <= ahead <= self._read_through():
                t = time.perf_counter()
                cur.pos = max(0, row - LOOKBEHIND)
                cur.cap.set(cv2.CAP_PROP_POS_FRAMES, cur.pos)
                f = self._step(cur)
                self.seeks += 1
                self.seek_ms = self._mean(self.seek_ms, (time.perf_counter() - t) * 1000, self.seeks)
            while cur.pos <= row:
                f = self._step(cur)
        return f

    def _read_through(self):
        """Rows ahead of the cursor it is cheaper to step through than to seek over."""
        if self.step_ms and self.seek_ms:
            return self.seek_ms / self.step_ms
        return SEEK_GUESS

    def _step(self, cur):
        t = time.perf_counter()
        ok, f = cur.cap.read()
        self.decodes += 1
        if not ok:
            row, cur.pos = cur.pos, -1
            if row < self.count:
                self.count = row  # container header lied; trust the stream
            raise IndexError(f"row {row} past end of {self.path}")
        self.step_ms = self._mean(self.step_ms, (time.perf_counter() - t) * 1000, self.decodes)
        if self._output == "gray" and f.ndim == 3:
            f = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        if self._scale != 1.0:
            f = cv2.resize(f, None, fx=self._scale, fy=self._scale, interpolation=cv2.INTER_AREA)
        self._put(cur.pos, f)
        cur.pos += 1
        return f

    @staticmethod
    def _mean(mean, x, n):
        return x if mean is None else mean + (x - mean) / min(n, 64)

    def _put(self, row, bgr):
        gone = []
        with self._cache_lock:
            if not self._fits(bgr):
                return
            if row in self._cache:
                self._cache.move_to_end(row)
                return
            self._cache[row] = bgr
            self._cache_bytes += bgr.nbytes
            while self._cache_bytes > self._cache_limit and len(self._cache) > 1:
                r, old = self._cache.popitem(last=False)
                self._cache_bytes -= old.nbytes
                gone.append((r, old.nbytes))
        if self.on_evict is not None:
            for r, n in gone:
                self.on_evict(r, n)

    def close(self):
        for cur in self._cursors.values():
            if cur is not None:
                cur.cap.release()
