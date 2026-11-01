"""cv2 BGR decoder with two cursors on one file: the walk's, which only ever steps, and the scrub's,
which takes the display's jumps so they never land on the walk's. A sequential read steps the cursor
in use; a short jump ahead reads through, since a seek decodes from the last keyframe anyway and
costs what the decoder has measured it to cost here; anything else seeks. A seek lands one row
short and reads through it, because the tools that difference frames ask for row - 1 right after
row, and that second ask would otherwise be a second seek."""
import threading
import time
from collections import OrderedDict
from contextlib import contextmanager

import cv2
import numpy as np

LOOKBEHIND = 1          # rows a seek lands short of its target and reads through
SEEK_GUESS = 12.0       # steps a seek is taken to cost until one has been measured here


class _Cursor:
    __slots__ = ("cap", "pos")

    def __init__(self, path):
        self.cap = cv2.VideoCapture(path)
        self.pos = 0


class Decoder:
    def __init__(self, path, cache_bytes=4 << 30):
        self.path = str(path)
        walk = _Cursor(self.path)
        if not walk.cap.isOpened():
            raise IOError(f"cannot open {path}")
        self.cap = walk.cap
        self.count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
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
        """What read() hands out: "bgr" as decoded, or "gray", converted before it is cached, so the
        cache holds a third of the bytes and no node downstream has to. Setting it empties the cache."""
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
                cur = self._cursors[self._use] = _Cursor(self.path)
            ahead = row - cur.pos
            if not 0 <= ahead <= self._read_through():
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
        ok, bgr = cur.cap.read()
        self.decodes += 1
        if not ok:
            row, cur.pos = cur.pos, -1
            if row < self.count:
                self.count = row  # container header lied; trust the stream
            raise IndexError(f"row {row} past end of {self.path}")
        self.step_ms = self._mean(self.step_ms, (time.perf_counter() - t) * 1000, self.decodes)
        f = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY) if self._output == "gray" else bgr
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
