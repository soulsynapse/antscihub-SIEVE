"""cv2 BGR decoder with two cursors on one file: the walk's, which only ever steps, and the scrub's,
which takes the display's jumps so they never land on the walk's. A sequential read steps the cursor
in use; a short jump ahead reads through, since a seek decodes from the last keyframe anyway and
costs what the decoder has measured it to cost here; anything else seeks. A seek lands one row
short and reads through it, because the tools that difference frames ask for row - 1 right after
row, and that second ask would otherwise be a second seek."""
import os
import sys
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
_EXPAND = np.clip(np.round((np.arange(256) - 16) * 255 / 219), 0, 255).astype(np.uint8)   # limited-range luma to full


class EndOfStream(IndexError):
    """A read past the last row the stream has, which may be short of the container's claim. The
    only IndexError the worker closes a walk on; a tool's own IndexError is a failure."""


def _quiet():
    return QUIET or os.environ.get("OPENCV_LOG_LEVEL", "").upper() in _QUIET_LEVELS


def _luma_range(path):
    """(usable, limited) for the luma plane of row 0: usable when it is the shape of the converted
    frame, limited when cv2's own conversion, which knows the stream's range, sits at a slope near
    219/255 above it. A flat row that cannot tell is taken as limited, the camera norm."""
    raw, rgb = cv2.VideoCapture(path, cv2.CAP_FFMPEG), cv2.VideoCapture(path, cv2.CAP_FFMPEG)
    try:
        raw.set(cv2.CAP_PROP_CONVERT_RGB, 0)
        ok, y = raw.read()
        ok2, bgr = rgb.read()
    finally:
        raw.release()
        rgb.release()
    if not (ok and ok2) or y.ndim != 2 or y.shape != bgr.shape[:2]:
        return False, False
    y = y.ravel()[::97].astype(np.float64)
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).ravel()[::97].astype(np.float64)
    var = y.var()
    if var < 25.0:
        return True, True
    slope = ((y - y.mean()) * (g - g.mean())).mean() / var
    return True, slope > 1.08


UNINDEXED = ("{name} has no index: a raw stream cannot be counted or seeked; remux it into a container first, "
             "ffmpeg -framerate FPS -i {name} -c copy {stem}.mp4")


def _facts(cap, path):
    """(width, height, fps, count) of an open capture; IOError when its container claims no rows."""
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if n <= 0:
        name = os.path.basename(str(path))
        raise IOError(UNINDEXED.format(name=name, stem=os.path.splitext(name)[0]))
    return int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)), cap.get(cv2.CAP_PROP_FPS) or 30.0, n


@lru_cache(maxsize=16)
def _probe(path, mtime):
    cap = cv2.VideoCapture(path, cv2.CAP_FFMPEG)
    try:
        if not cap.isOpened():
            raise IOError(f"cannot open {path}")
        return _facts(cap, path)
    finally:
        cap.release()


def probe(src):
    """(width, height, fps, count) via cv2, cached per path and mtime. The count is the container's
    claim, which the decoder corrects down when the stream ends short of it; a file whose container
    claims none, a raw stream, raises IOError, as the decoder does."""
    src = str(src)
    return _probe(src, os.stat(src).st_mtime)


class _Cursor:
    __slots__ = ("cap", "pos", "path", "luma")      # pos: the row the next step reads; None once a step has failed, so the next read seeks

    def __init__(self, path, luma):
        self.path, self.luma, self.cap = path, luma, None
        self.reopen()

    def reopen(self, luma=None):
        """A fresh capture at row 0, the luma plane's or BGR's: the only way to change what it decodes
        to, since the plugin garbles every frame after CAP_PROP_CONVERT_RGB is flipped on a capture
        that has read one."""
        if self.cap is not None:
            self.cap.release()
        if luma is not None:
            self.luma = luma
        self.cap = cv2.VideoCapture(self.path, cv2.CAP_FFMPEG)
        self.cap.set(cv2.CAP_PROP_CONVERT_RGB, 0 if self.luma else 1)
        self.pos = 0


class Decoder:
    """Opens an indexed container; a file that will not open, or whose container claims no rows (a
    raw stream, which cannot be seeked), raises IOError saying which."""

    def __init__(self, path, cache_bytes=4 << 30):
        self.path = str(path)
        walk = _Cursor(self.path, luma=False)
        if not walk.cap.isOpened():
            raise IOError(f"cannot open {path}")
        cap = walk.cap
        try:
            self.width, self.height, self.fps, self.count = _facts(cap, self.path)
        except IOError:
            cap.release()
            raise
        fmt = int(cap.get(cv2.CAP_PROP_CODEC_PIXEL_FORMAT)).to_bytes(4, "little", signed=True)
        self.luma = fmt in LUMA_FORMATS and _quiet()
        self._limited = None    # measured at the first gray read, two decodes of row 0
        self._output = "bgr"
        self._cursors = {"walk": walk, "scrub": None}   # the scrub's opens on its first use
        self._use = "walk"
        self._cache = OrderedDict()
        self._cache_bytes, self._cache_limit = 0, cache_bytes
        self._cache_lock = threading.Lock()     # the dict only: a GUI peek never waits on a decode
        self._cap_lock = threading.Lock()       # the captures and the cursor in use
        self.decodes = self.seeks = 0
        self.reads = self.cache_hits = 0        # read() calls, and those the cache answered
        self.evictions = 0                      # frames the cache dropped for room
        self.step_ms = self.seek_ms = None      # running means of what a step and a seek cost on this file
        self.on_evict = None                    # (row, bytes) for each frame the cache drops, after the lock
        self._inexact_said = False

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
        """What read() hands out, before it is cached: "bgr" as decoded; "gray", full range; or
        "luma", the decoder's own plane in the stream's range, 16 to 235 on most camera files. On an
        8-bit 4:2:0 stream with QUIET set both grays come from the plane and skip the YUV-to-BGR
        conversion, gray through a lookup table when the stream is limited range; otherwise both are
        converted from BGR. Setting it empties the cache."""
        return self._output

    @output.setter
    def output(self, value):
        if value not in ("bgr", "gray", "luma"):
            raise ValueError(f"decoder output {value!r}; one of bgr, gray, luma")
        with self._cache_lock:
            if value == self._output:
                return
            self._output, self._cache_bytes = value, 0
            self._cache.clear()

    @property
    def limited(self):
        """Whether the luma plane is limited range, measured on row 0 the first time it is asked."""
        if self._limited is None:
            self.luma, self._limited = _luma_range(self.path) if self.luma else (False, False)
        return self._limited

    def _luma_read(self):
        return self.luma and self._output != "bgr"

    def _fits(self, f):
        # a frame of the other kind, decoded before a switch and landing after it, is not served
        return (f.ndim == 2) == (self._output != "bgr")

    def cached(self, row):
        """Cache-only read; never touches a capture. Safe from the GUI thread."""
        with self._cache_lock:
            f = self._cache.get(row)
            return f if f is None or self._fits(f) else None

    def empty(self):
        """Drops every cached frame and tells `on_evict` of none. Any thread."""
        with self._cache_lock:
            self._cache.clear()
            self._cache_bytes = 0

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
                cur.reopen(self._luma_read())   # here, under the lock a read holds, never from the setter
            if cur.pos is None or not 0 <= row - cur.pos <= self._read_through():
                t = time.perf_counter()
                self._seek(cur, max(0, row - LOOKBEHIND))
                f = self._step(cur)
                self.seeks += 1
                self.seek_ms = self._mean(self.seek_ms, (time.perf_counter() - t) * 1000, self.seeks)
            while cur.pos <= row:
                f = self._step(cur)
        return f

    def _seek(self, cur, target):
        """Puts the cursor at or before `target`, where the plugin reports it landed: a container that
        seeks inexactly lands on a keyframe near the target, so the landing is read back, a landing past
        the target is retried further back, and the rows between are stepped through by read()."""
        back = 0
        while True:
            cur.cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, target - back))
            landed = int(cur.cap.get(cv2.CAP_PROP_POS_FRAMES))
            if landed < 0:
                cur.pos = max(0, target - back)
                return
            if landed != target and not self._inexact_said:
                self._inexact_said = True
                print(f"{os.path.basename(self.path)}: a seek to row {target} landed on {landed}; the container seeks "
                      "inexactly, so rows are stepped through from where each seek lands", file=sys.stderr)
            if landed <= target or target - back == 0:
                cur.pos = landed
                return
            back = 2 * (back or landed - target)

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
            row, cur.pos = cur.pos, None
            if 0 <= row < self.count:
                # the only record of why, since dev/console.py hushes libav's; SIEVE_C_STDERR=1 shows it
                print(f"{os.path.basename(self.path)}: the stream ended at row {row} of the container's {self.count}, "
                      f"at {cur.cap.get(cv2.CAP_PROP_POS_MSEC) / 1000:.3f} s; the count is now {row}", file=sys.stderr)
                self.count = row
            raise EndOfStream(f"row {row} past end of {self.path}")
        self.step_ms = self._mean(self.step_ms, (time.perf_counter() - t) * 1000, self.decodes)
        if self._output != "bgr" and f.ndim == 3:
            f = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        elif self._output == "gray" and self.limited:
            f = cv2.LUT(f, _EXPAND)
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
            self.evictions += len(gone)
        if self.on_evict is not None:
            for r, n in gone:
                self.on_evict(r, n)

    def close(self):
        for cur in self._cursors.values():
            if cur is not None:
                cur.cap.release()
