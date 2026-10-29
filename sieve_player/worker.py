"""The one thread that runs tools. Walks the loop window; serves display requests first."""
import threading
import traceback

import numpy as np
from PySide6.QtCore import QThread, Signal

from .graph import Series


class Worker(QThread):
    rowReady = Signal(int)                    # a requested row is now in the memo
    walked = Signal(int, int)                 # rows done, rows in window
    seriesReady = Signal(object, int, float)  # {node: result} for the series chain, start, fps
    failed = Signal(int)                      # a tool raised at this row; the walk is abandoned

    def __init__(self, graph, every=30):
        super().__init__()
        self.graph, self.every = graph, every
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
                    self.graph.compute(self.graph.shown, want)
                    if self.graph.over is not None:
                        self.graph.compute(self.graph.over, want)
                    self.rowReady.emit(want)
                    continue
                if not self.graph.fed(self.graph.walk):
                    self._walk_gen, self._i = gen, self._length   # nothing reaches the walked node; wait for the next change
                    continue
                if gen != self._walk_gen:
                    self._walk_gen, self._i, self._stack = gen, 0, None
                    self._start = max(0, min(start, self.graph.count - 1))
                    self._length = max(0, min(length, self.graph.count - self._start))
                if dirty and self._i:
                    self._emit_series()
                    continue
                if self._i < self._length:
                    out = np.asarray(self.graph.compute(self.graph.walk, self._start + self._i))
                    if self._stack is not None and (self._stack.shape[1:] != out.shape or self._stack.dtype != out.dtype):
                        self._stack, self._i = None, 0   # the node or its shape changed under the walk; start over
                        continue
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
                if want is None:
                    self.failed.emit(self._start + self._i)
                    self._i = self._length  # abandon this walk; the next gen bump restarts it

    def _emit_series(self):
        chain = self.graph.series_chain()
        if not chain or not self._i:
            return
        results, start, fps = {}, self._start, self.graph.fps
        for i, (nid, tool, params, src) in enumerate(chain):
            if i == 0:
                series = Series(self._stack[: self._i], self.graph.key(src), start, fps)
            elif isinstance(results.get(src), dict) and "signal" in results[src]:
                series = Series(np.asarray(results[src]["signal"]), self.graph.key(src), start, fps)
            else:
                continue            # the upstream tool did not hand out the signal it declared, or was skipped itself
            results[nid] = tool.run(series, params)
        self.seriesReady.emit(results, start, fps)
