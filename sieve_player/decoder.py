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
    def __init__(self, path, cache_bytes=256 << 20):
        self.path = str(path)
        walk = _Cursor(self.path)
        if not walk.cap.isOpened():
            raise IOError(f"cannot open {path}")
        self.cap = walk.cap
        self.count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._cursors = {"walk": walk, "scrub": None}   # the scrub's opens on its first use
        self._use = "walk"
        self._cache = OrderedDict()
        self._cache_bytes, self._cache_limit = 0, cache_bytes
        self._cache_lock = threading.Lock()     # the dict only: a GUI peek never waits on a decode
        self._cap_lock = threading.Lock()       # the captures and the cursor in use
        self.decodes = self.seeks = 0
        self.step_ms = self.seek_ms = None      # running means of what a step and a seek cost on this file

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

    def cached(self, row):
        """Cache-only read; never touches a capture. Safe from the GUI thread."""
        with self._cache_lock:
            return self._cache.get(row)

    def read(self, row) -> np.ndarray:
        f = self.cached(row)
        if f is not None:
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
        self._put(cur.pos, bgr)
        cur.pos += 1
        return bgr

    @staticmethod
    def _mean(mean, x, n):
        return x if mean is None else mean + (x - mean) / min(n, 64)

    def _put(self, row, bgr):
        with self._cache_lock:
            if row in self._cache:
                self._cache.move_to_end(row)
                return
            self._cache[row] = bgr
            self._cache_bytes += bgr.nbytes
            while self._cache_bytes > self._cache_limit and len(self._cache) > 1:
                _, old = self._cache.popitem(last=False)
                self._cache_bytes -= old.nbytes

    def close(self):
        for cur in self._cursors.values():
            if cur is not None:
                cur.cap.release()
