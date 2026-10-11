"""The one thread that runs tools. Walks the loop window; serves display requests first."""
import threading
import traceback

import numpy as np
from PySide6.QtCore import QThread, Signal

from .chain import Series


class Worker(QThread):
    rowReady = Signal(int)                    # a requested row is now in the memo
    walked = Signal(int, int)                 # rows done, rows in window
    seriesReady = Signal(object, int, float)  # result, start, fps

    def __init__(self, chain, every=30):
        super().__init__()
        self.chain, self.every = chain, every
        self._cv = threading.Condition()
        self._want = None
        self._stop = False
        self._gen = 0                         # bumped by anything that restarts the walk
        self._series_dirty = False
        self._window = (0, 0)
        self._walk_gen = -1
        self._start = self._length = self._i = 0
        self._stack = None

    # -- GUI-side calls --------------------------------------------------
    def request_row(self, row):
        with self._cv:
            self._want = row
            self._cv.notify()

    def set_window(self, start, length):
        with self._cv:
            self._window = (start, length)
            self._gen += 1
            self._cv.notify()

    def invalidate(self):
        """A frame tool changed: restart the walk from the window start."""
        with self._cv:
            self._gen += 1
            self._cv.notify()

    def rerun_series(self):
        """Only the series tool changed: rerun it on the stack we already have."""
        with self._cv:
            self._series_dirty = True
            self._cv.notify()

    def stop(self):
        with self._cv:
            self._stop = True
            self._cv.notify()
        self.wait()

    # -- thread side -----------------------------------------------------
    def _pending(self):
        return self._gen != self._walk_gen or self._i < self._length

    def run(self):
        while True:
            with self._cv:
                while not (self._stop or self._want is not None or self._series_dirty or self._pending()):
                    self._cv.wait()
                if self._stop:
                    return
                want, self._want = self._want, None
                gen, (start, length) = self._gen, self._window
                dirty, self._series_dirty = self._series_dirty, False
            try:
                if want is not None:
                    self.chain.compute(self.chain.last, want)
                    self.rowReady.emit(want)
                    continue
                if gen != self._walk_gen:
                    self._walk_gen, self._i, self._stack = gen, 0, None
                    self._start = max(0, min(start, self.chain.count - 1))
                    self._length = max(0, min(length, self.chain.count - self._start))
                if dirty and self._i:
                    self._emit_series()
                    continue
                if self._i < self._length:
                    out = np.asarray(self.chain.compute(self.chain.last, self._start + self._i))
                    if self._stack is None:
                        self._stack = np.empty((self._length,) + out.shape, dtype=out.dtype)
                    self._stack[self._i] = out
                    self._i += 1
                    self.walked.emit(self._i, self._length)
                    if self._i % self.every == 0 or self._i == self._length:
                        self._emit_series()
            except IndexError:
                self._length = self._i  # stream ended early; close the window there
                self._emit_series()
            except Exception:
                traceback.print_exc()

    def _emit_series(self):
        tool = self.chain.series_tool
        if tool is None or not self._i:
            return
        series = Series(self._stack[: self._i], self.chain.key(self.chain.last), self._start, self.chain.fps)
        result = tool.run(series, self.chain.get_series_params())
        self.seriesReady.emit(result, self._start, self.chain.fps)
