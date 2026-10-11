"""cv2 gray decoder: one cursor, sequential reads step it, anything else seeks."""
import threading
from collections import OrderedDict

import cv2
import numpy as np


class Decoder:
    def __init__(self, path, cache_rows=256):
        self.path = str(path)
        self.cap = cv2.VideoCapture(self.path)
        if not self.cap.isOpened():
            raise IOError(f"cannot open {path}")
        self.count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._cursor = 0
        self._cache = OrderedDict()
        self._cache_rows = cache_rows
        self._lock = threading.Lock()
        self.decodes = 0
        self.seeks = 0

    def cached(self, row):
        """Cache-only read; never touches the capture. Safe from the GUI thread."""
        with self._lock:
            return self._cache.get(row)

    def read(self, row) -> np.ndarray:
        with self._lock:
            f = self._cache.get(row)
            if f is not None:
                self._cache.move_to_end(row)
                return f
            if row != self._cursor:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, row)
                self.seeks += 1
            ok, bgr = self.cap.read()
            self.decodes += 1
            if not ok:
                self._cursor = -1
                if row < self.count:
                    self.count = row  # container header lied; trust the stream
                raise IndexError(f"row {row} past end of {self.path}")
            self._cursor = row + 1
            g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            self._cache[row] = g
            while len(self._cache) > self._cache_rows:
                self._cache.popitem(last=False)
            return g

    def close(self):
        self.cap.release()
