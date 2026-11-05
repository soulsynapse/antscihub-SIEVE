"""The one thread that runs tools. Serves display requests first, walks the loop window, and walks the
whole clip when asked in the time the window leaves.

The clip walk is the window walk over the clip without the densities, behind a finished window
walk so what is viewed never waits on it; a frame change abandons it and its rows. A stack holds
images by shape, one row each, and tables in an object array, one table a row, so a walked node
that hands out a table never reads as a graph changing shape under the walk. The clip's chain runs
over the rows so far only once the walk has run CHAIN_SHARE times as long as the chain's last run,
so a chain of per-row loops never makes the walk quadratic in the clip.
"""
import sys
import threading
import time
import traceback

import numpy as np
from PySide6.QtCore import QThread, Signal

from . import density
from .decoder import EndOfStream
from .graph import Cancelled, Memo, Series, gated, nbytes

CLIP_BYTES = 512 << 20    # the most a clip walk's stack may take, as nbytes counts it
CHAIN_SHARE = 9           # walking between two clip chain runs takes at least this many times the last run
STOP_PATIENCE_MS = 10_000  # how long stop() waits before saying on stderr what it is waiting for


def _stack_for(n, out):
    return np.empty(n, object) if out.dtype.fields is not None else np.empty((n,) + out.shape, out.dtype)


def _fits(stack, out):
    """Whether `out` is a row of `stack`: a table into an object stack, an image by shape and dtype."""
    if stack.dtype == object:
        return out.dtype.fields is not None
    return stack.shape[1:] == out.shape and stack.dtype == out.dtype


class Worker(QThread):
    rowReady = Signal(int)                    # a requested row is computed and peekable
    walked = Signal(int, int)                 # rows done, rows in window
    seriesReady = Signal(object, int, float)  # {node: result} for the series chain, each gated and keyed, start, fps
    densityReady = Signal(object, int)        # {node: (rows, BINS) counts} per plane the walk computes, start
    failed = Signal(int, str)                 # a tool raised at this row, on this node; a walk is abandoned, a display request dropped
    clipWalked = Signal(int, int)             # rows done, rows in the clip; done == total when the clip walk is not running
    clipReady = Signal(object, int, float)    # as seriesReady, over the clip walk's rows; {} when the walk was abandoned
    clipRefused = Signal(str)                 # the clip walk did not start, and why
    shortened = Signal(int)                   # the stream ended short of the container's claim: the count as the decoder now has it

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
        self._dens = {}                       # node -> (length, BINS) counts, for the planes the walk computes
        self._clip_gen, self._clip_walk_gen = 0, 0   # bumped by walk_clip and invalidate; what the clip stack was walked under
        self._clip_on = False                 # whether a clip walk is wanted
        self._clen = self._ci = self._cbytes = 0
        self._cstack = None
        self._clip_due = 0.0                  # when the clip's chain may next run, on perf_counter's clock
        # fold id -> (the stack's buffer, rows, that head's own folding of the stack), one dict per stack; the buffer
        # is held, not its id, since a freed buffer's address comes back for the next stack of the same shape
        self._folded, self._cfolded = {}, {}

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
        """A frame tool changed: restart the walk from the window start, and drop the clip walk,
        whose rows were of a graph that is gone."""
        with self._cv:
            self._gen += 1
            self._clip_gen += 1
            self._clip_on = False
            self._cv.notify()

    def rerun_series(self):
        """Only the series tool changed: rerun it on the stack we already have, and on the clip's."""
        with self._cv:
            self._series_dirty = True
            self._cv.notify()

    def walk_clip(self):
        """Walk the whole clip, from its first row, once the window is walked."""
        with self._cv:
            self._clip_gen += 1
            self._clip_on = True
            self._cv.notify()

    def stop_clip(self):
        """Halt the clip walk where it is; the rows it has stand."""
        with self._cv:
            self._clip_on = False
            self._cv.notify()

    def stop(self):
        """Halts the graph, so a run of many reads dies at its next one, then joins the thread."""
        self.graph.halt = True
        with self._cv:
            self._stop = True
            self._cv.notify()
        if not self.wait(STOP_PATIENCE_MS):
            print(f"worker still running {STOP_PATIENCE_MS // 1000} s after stop: a tool in a loop no read interrupts", file=sys.stderr)
            self.wait()

    # -- thread side -----------------------------------------------------
    def _pending(self):
        return self._gen != self._walk_gen or self._i < self._length

    def _clip_pending(self):
        return self._clip_gen != self._clip_walk_gen or self._ci < self._clen

    def run(self):
        threading.current_thread().name = "worker"      # what the probe's events name as their thread
        try:
            self._serve()
        except BaseException:
            traceback.print_exc()   # _serve answers for a tool's exceptions; one reaching here ends the thread, and `finished` says so
            raise

    def _serve(self):
        while True:
            with self._cv:
                while not (self._stop or self._want is not None or self._series_dirty or self._pending()
                           or self._clip_pending()):
                    self._cv.wait()
                if self._stop:
                    return
                want, self._want = self._want, None
                gen, (start, length) = self._gen, self._window
                dirty = False
                if want is None:
                    dirty, self._series_dirty = self._series_dirty, False
                clip_gen, clip_on = self._clip_gen, self._clip_on
            which = "window"
            try:
                if want is not None:
                    self.graph.serving("scrub")
                    with self.graph.decoder.scrub():   # the display's jump lands on its own cursor, not the walk's
                        self.graph.compute(self.graph.shown, want)
                        if self.graph.over is not None:
                            self.graph.compute(self.graph.over, want)
                    self.rowReady.emit(want)
                    continue
                self.graph.serving("walk")
                if not self.graph.fed(self.graph.walk):
                    self._walk_gen, self._i = gen, self._length   # nothing reaches the walked node; wait for the next change
                    if clip_gen != self._clip_walk_gen:
                        self._clip_walk_gen, self._ci, self._clen, self._cstack, self._cbytes = clip_gen, 0, 0, None, 0
                        self.clipReady.emit({}, 0, self.graph.fps)
                        self.clipWalked.emit(0, 0)
                    elif self._ci < self._clen:
                        self._clen = self._ci
                        self.clipWalked.emit(self._ci, self._clen)
                    continue
                if gen != self._walk_gen:
                    self._walk_gen, self._i, self._stack, self._dens, self._folded = gen, 0, None, {}, {}
                    self._start = max(0, min(start, self.graph.count - 1))
                    self._length = max(0, min(length, self.graph.count - self._start))
                if dirty and self._i:
                    self._emit_series()
                    if self._ci:
                        self._emit_clip()
                    continue
                if self._i < self._length:
                    self._walk_one()
                    continue
                which = "clip"
                if clip_gen != self._clip_walk_gen:
                    self._clip_walk_gen, self._ci, self._cstack, self._cbytes, self._clip_due = clip_gen, 0, None, 0, 0.0
                    self._cfolded = {}
                    self._clen = self.graph.count if clip_on else 0
                    if not clip_on:
                        self.clipReady.emit({}, 0, self.graph.fps)
                    self.clipWalked.emit(self._ci, self._clen)
                elif not clip_on and self._ci < self._clen:
                    self._clen = self._ci       # stopped: the rows it has stand, and the count says so
                    self.clipWalked.emit(self._ci, self._clen)
                if clip_on and self._ci < self._clen:
                    self._clip_one()
            except Cancelled:
                continue        # the graph moved on under the row, or we are stopping: the loop reads the new state
            except EndOfStream:
                self.shortened.emit(self.graph.count)
                if want is not None:
                    pass            # the display asked past the end; the window follows the count and asks again
                elif which == "window":
                    self._length = self._i  # stream ended early; close the window there
                    self.walked.emit(self._i, self._length)
                    self.graph.progress(self._i, self._length)
                    self._emit_series()
                else:
                    self._clen = self._ci
                    self.clipWalked.emit(self._ci, self._clen)
                    self._emit_clip()
            except Exception as e:
                traceback.print_exc()
                nid = getattr(e, "sieve_node", "")
                if want is not None:
                    self.failed.emit(want, nid)
                elif which == "window":
                    self.failed.emit(self._start + self._i, nid)
                    self._i = self._length  # abandon this walk; the next gen bump restarts it
                else:
                    self.failed.emit(self._ci, nid)
                    self._clen = self._ci
                    self.clipWalked.emit(self._ci, self._clen)

    def _walk_one(self):
        row = self._start + self._i
        out = np.asarray(self.graph.walk_row(row))
        planes = {nid: v for nid in self.graph.frame_nodes() if (v := self.graph.density(nid, row)) is not None}
        if self._stack is not None and (not _fits(self._stack, out) or planes.keys() != self._dens.keys()):
            self._stack, self._dens, self._i = None, {}, 0   # the nodes or the shape changed under the walk; start over
            return
        if self._stack is None:
            self._stack = _stack_for(self._length, out)
            self._dens = {nid: np.zeros((self._length, density.BINS), np.uint32) for nid in planes}
        self._stack[self._i] = out
        for nid, v in planes.items():
            self._dens[nid][self._i] = v
        self._i += 1
        self.walked.emit(self._i, self._length)
        self.graph.progress(self._i, self._length)
        if self._i % self.every == 0 or self._i == self._length:
            self._emit_series()

    def _clip_one(self):
        out = np.asarray(self.graph.walk_row(self._ci))
        if self._cstack is not None and not _fits(self._cstack, out):
            self._cstack, self._ci, self._cbytes = None, 0, 0
            return
        if self._cstack is None:
            if self._clen * nbytes(out) > CLIP_BYTES:
                self.clipRefused.emit(f"the clip's stack would be {self._clen * nbytes(out) / 2**30:.1f} GB; "
                                      f"{', '.join(self.graph.heads)} do not share a fold()")
                self._clen = 0
                self.clipWalked.emit(0, 0)
                return
            self._cstack = _stack_for(self._clen, out)
        self._cstack[self._ci] = out
        self._cbytes += nbytes(out)
        self._ci += 1
        if self._cbytes > CLIP_BYTES:
            self._clen = self._ci       # tables grew past the first row's forecast: the rows it has stand, as after stop_clip
            self.clipWalked.emit(self._ci, self._clen)
            self._emit_clip()
            self.clipRefused.emit(f"the clip's stack reached {self._cbytes / 2**30:.1f} GB at row {self._ci}; the rows walked stand")
            return
        self.clipWalked.emit(self._ci, self._clen)
        if self._ci == self._clen or (self._ci % self.every == 0 and time.perf_counter() >= self._clip_due):
            self._emit_clip()

    def _emit_series(self):
        if not self._i:
            return
        self.densityReady.emit({nid: d[: self._i] for nid, d in self._dens.items()}, self._start)
        results = self._run_chain(self._stack[: self._i], self._start, self._i, self._folded)
        if results is not None:
            self.seriesReady.emit(results, self._start, self.graph.fps)

    def _emit_clip(self):
        if not self._ci:
            return
        t = time.perf_counter()
        results = self._run_chain(self._cstack[: self._ci], 0, self._ci, self._cfolded)
        self._clip_due = time.perf_counter() + CHAIN_SHARE * (time.perf_counter() - t)
        if results is not None:
            self.clipReady.emit(results, 0, self.graph.fps)

    def _run_chain(self, stack, start, done, folds):
        """The series chain over `stack`, the walked node's rows from `start`, `done` of them so
        far, with `folds` the stack's own cache of each head's folding: {node: result}, each gated
        and keyed; None when there is no chain."""
        chain = self.graph.series_chain()
        if not chain:
            return None
        results, feeds, fps = {}, {}, self.graph.fps
        heads, folded = set(self.graph.heads), self.graph.fold is not None
        buffer = stack.base if stack.base is not None else stack
        for nid, tool, params, band, src in chain:
            if nid in heads:
                fold = None if folded else getattr(tool, "fold", None)
                if fold is not None:
                    held = folds.get(id(fold))
                    if held is None or held[0] is not buffer or held[1] != len(stack):
                        held = (buffer, len(stack), np.stack([fold(row) for row in stack]) if len(stack) else np.zeros((0, 0)))
                        folds[id(fold)] = held
                series = Series(stack if fold is None else held[2], self.graph.key(src), start, fps)
            elif feeds.get(src) is not None:
                series = Series(feeds[src], self.graph.key(src), start, fps)
            else:
                self.graph.note(nid, f"{src} handed out no signal")
                continue
            with self.graph.probe(nid, start + done - 1, self.graph.key(nid)) as ev:
                try:
                    results[nid], feeds[nid] = gated(tool.run(series, params), band)
                except Exception as exc:
                    exc.sieve_node = nid
                    self.graph.note(nid, f"raised over {done} rows from {start}: {type(exc).__name__}: {exc}")
                    raise
                ev[1] = Memo._size(results[nid])
            self.graph.note(nid, "")
            if isinstance(results[nid], dict):
                results[nid] = {**results[nid], "key": self.graph.key(nid)}   # the node's key beside its gate: what a tool that writes a file records
        return results
