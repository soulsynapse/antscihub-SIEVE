"""The one thread that runs tools. Serves display requests first, walks the loop window, bakes a node
one row at a time in the time the window leaves, and walks the whole clip when asked after that.

The clip walk is the window walk over the clip without the densities, behind a finished window
walk so what is viewed never waits on it; a frame change abandons it and its rows, and a bake. A
stack holds images by shape, one row each, and tables in an object array, one table a row, so a
walked node handing out a table never reads as a graph changing shape; there is none without a
series chain, and either walk stops at STACK_BYTES. The clip's chain runs over the rows so far only
once the walk has run CHAIN_SHARE times as long as the chain's last run. A bake on a frame wire
streams the node's input into a store writer, holding only the row it writes; on a series wire it writes from the clip walk's result."""
import os
import sys
import threading
import time
import traceback
from dataclasses import dataclass, field

import numpy as np
from PySide6.QtCore import QThread, Signal

from . import density, store
from .decoder import EndOfStream
from .document import INPUT
from .graph import Cancelled, Memo, Series, gated, nbytes

STACK_BYTES = 512 << 20   # the most a walk's stack, the window's or the clip's, may take, as nbytes counts it
CHAIN_SHARE = 9           # walking between two clip chain runs takes at least this many times the last run
STOP_PATIENCE_MS = 10_000  # how long stop() waits before saying on stderr what it is waiting for


@dataclass
class _Bake:
    """A bake in progress: the node, the key its file is named by, the rows it writes and the writer."""
    nid: str
    key: str
    kind: str           # the kind flowing into the node, what the file holds
    series: bool        # written from the clip walk's result, not row by row
    src: str
    rows: list
    writer: object
    fields: dict        # the sidecar's, less what the writer learns
    i: int = 0
    held: list = field(default_factory=list)


def _bound(text, default):
    """A row bound off a param: `default` when blank, else the integer it names; ValueError otherwise."""
    text = str(text).strip()
    return default if text == "" else int(text)


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
    clipRefused = Signal(str)                 # the clip walk did not start, or stopped short of the clip, and why
    walkRefused = Signal(str)                 # the window walk closed short of the window, and why: its stack passed STACK_BYTES
    shortened = Signal(int)                   # the stream ended short of the container's claim: the count as the decoder now has it
    baked = Signal(str, int, int)             # a bake's progress: the node, rows written, rows to write
    bakeDone = Signal(str, str)               # the node is baked, under this key; its mode says so
    bakeRefused = Signal(str, str)            # the bake did not start or did not finish, and why; the node's standing says the same

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
        self._start = self._length = self._i = self._bytes = 0
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
        self._bake_gen, self._bake_walk_gen = 0, 0   # bumped by bake, cancel_bake and invalidate; what the thread last acted on
        self._bake_ask = (None, "")                   # (the node to bake, or None, and why the one running is to go)
        self._bake = None                             # the _Bake in progress

    # -- GUI-side calls --------------------------------------------------
    def bake(self, nid):
        """Write `nid`'s input to the store over its range, after the window is walked; one bake at a time."""
        with self._cv:
            self._bake_ask = (nid, "superseded by another bake")
            self._bake_gen += 1
            self._cv.notify()

    def cancel_bake(self):
        with self._cv:
            self._bake_ask = (None, "cancelled")
            self._bake_gen += 1
            self._cv.notify()

    @property
    def bake_bytes(self):
        """What the bake holds: the row its writer is writing, 0 between rows and with no bake running."""
        b = self._bake
        return 0 if b is None else b.writer.bytes

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
            self._bake_ask = (None, "abandoned: a frame tool changed")
            self._bake_gen += 1
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

    def _bake_pending(self):
        b = self._bake
        return self._bake_gen != self._bake_walk_gen or (b is not None and not b.series and b.i < len(b.rows))

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
                           or self._clip_pending() or self._bake_pending()):
                    self._cv.wait()
                if self._stop:
                    self._bake_fail("the video was closed")
                    return
                want, self._want = self._want, None
                gen, (start, length) = self._gen, self._window
                dirty = False
                if want is None:
                    dirty, self._series_dirty = self._series_dirty, False
                clip_gen, clip_on = self._clip_gen, self._clip_on
                bake_gen, (bake_ask, bake_why) = self._bake_gen, self._bake_ask
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
                if bake_gen != self._bake_walk_gen:
                    self._bake_walk_gen = bake_gen
                    self._bake_fail(bake_why)
                    if bake_ask is not None:
                        self._bake_begin(bake_ask)
                    continue
                b = self._bake
                if b is not None and not b.series and not dirty and gen == self._walk_gen and self._i >= self._length:
                    which = "bake"
                    self.graph.serving("bake")
                    self._bake_one()
                    continue
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
                    self._walk_gen, self._i, self._bytes, self._stack, self._dens, self._folded = gen, 0, 0, None, {}, {}
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
                    self._bake_fail("the clip walk was stopped short of the clip")
                if clip_on and self._ci < self._clen:
                    self._clip_one()
            except Cancelled:
                if which == "bake":
                    self._bake_fail("abandoned: the graph moved on")
                continue        # the graph moved on under the row, or we are stopping: the loop reads the new state
            except EndOfStream:
                self.shortened.emit(self.graph.count)
                if want is not None:
                    pass            # the display asked past the end; the window follows the count and asks again
                elif which == "bake":
                    self._bake_fail(f"the stream ended at row {self.graph.count}, inside the range")
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
                elif which == "bake":
                    b = self._bake
                    row = b.rows[b.i] if b is not None and b.i < len(b.rows) else "?"
                    self._bake_fail(f"{nid or 'the writer'} raised at row {row}: {type(e).__name__}: {e}")
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
        stacked = bool(self.graph.chain)      # without a chain nothing reads the stack, and the rows are not held
        if self._i and ((self._stack is not None) != stacked or (stacked and not _fits(self._stack, out))
                        or planes.keys() != self._dens.keys()):
            self._stack, self._dens, self._i, self._bytes = None, {}, 0, 0   # the nodes or the shape changed under the walk; start over
            return
        if not self._i:
            if stacked and self._length * nbytes(out) > STACK_BYTES:
                self._refuse_walk(f"the window's stack would be {self._length * nbytes(out) / 2**30:.1f} GB; "
                                  f"{', '.join(self.graph.heads)} do not share a fold()")
                return
            self._stack = _stack_for(self._length, out) if stacked else None
            self._dens = {nid: np.zeros((self._length, density.BINS), np.uint32) for nid in planes}
        if stacked:
            self._stack[self._i] = out
            self._bytes += nbytes(out)
        for nid, v in planes.items():
            self._dens[nid][self._i] = v
        self._i += 1
        if self._bytes > STACK_BYTES:
            self._refuse_walk(f"the window's stack reached {self._bytes / 2**30:.1f} GB at row {row}; the rows walked stand")
            return
        self.walked.emit(self._i, self._length)
        self.graph.progress(self._i, self._length)
        if self._i % self.every == 0 or self._i == self._length:
            self._emit_series()

    def _refuse_walk(self, why):
        """Closes the window walk at the rows it has, as a short stream does, and says why."""
        self._length = self._i
        self.walked.emit(self._i, self._length)
        self.graph.progress(self._i, self._length)
        self._emit_series()
        self.walkRefused.emit(why)

    def _clip_one(self):
        out = np.asarray(self.graph.walk_row(self._ci))
        if self._cstack is not None and not _fits(self._cstack, out):
            self._cstack, self._ci, self._cbytes = None, 0, 0
            return
        if self._cstack is None:
            if self._clen * nbytes(out) > STACK_BYTES:
                why = (f"the clip's stack would be {self._clen * nbytes(out) / 2**30:.1f} GB; "
                       f"{', '.join(self.graph.heads)} do not share a fold()")
                self.clipRefused.emit(why)
                self._bake_fail(f"the clip walk was refused: {why}")
                self._clen = 0
                self.clipWalked.emit(0, 0)
                return
            self._cstack = _stack_for(self._clen, out)
        self._cstack[self._ci] = out
        self._cbytes += nbytes(out)
        self._ci += 1
        if self._cbytes > STACK_BYTES:
            self._clen = self._ci       # tables grew past the first row's forecast: the rows it has stand, as after stop_clip
            self.clipWalked.emit(self._ci, self._clen)
            self._emit_clip()
            why = f"the clip's stack reached {self._cbytes / 2**30:.1f} GB at row {self._ci}; the rows walked stand"
            self.clipRefused.emit(why)
            self._bake_fail(f"the clip walk was refused: {why}")
            return
        self.clipWalked.emit(self._ci, self._clen)
        if self._ci == self._clen or (self._ci % self.every == 0 and time.perf_counter() >= self._clip_due):
            self._emit_clip()

    def _emit_series(self):
        if not self._i:
            return
        self.densityReady.emit({nid: d[: self._i] for nid, d in self._dens.items()}, self._start)
        if self._stack is None:
            return
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
        if self._bake is not None and self._bake.series and self._ci == self._clen:
            self._bake_series(results)

    # -- baking ----------------------------------------------------------
    def _bake_begin(self, nid):
        """Starts a bake of `nid`'s input, or refuses it with the reason in the node's standing: an
        input unwired or unfed, a kind with no writer, a range that names no row, a store that
        cannot be written. A series bake asks for the clip walk and writes when it completes."""
        g = self.graph
        e = g.entry(nid)
        if e is None or e.src is None:
            return self._refuse(nid, "in is unwired")
        if not e.fed:
            return self._refuse(nid, e.standing or f"in waits on {e.src}")
        kind = e.types.get(INPUT)
        w = store.writer(kind)
        if w is None:
            return self._refuse(nid, f"no writer for {kind}; a bake writes {', '.join(store.kinds())}")
        try:
            lo, hi = _bound(e.params.get("from", ""), 0), _bound(e.params.get("to", ""), g.count - 1)
            inc = max(1, int(e.params.get("increment", 1)))
        except (TypeError, ValueError) as exc:
            return self._refuse(nid, f"the range does not read: {exc}")
        rows = list(range(max(lo, 0), min(hi, g.count - 1) + 1, inc))
        if not rows:
            return self._refuse(nid, f"rows {lo} to {hi} name no row of the clip's {g.count}")
        folder = store.folder()
        why = store.writable(folder)
        if why:
            return self._refuse(nid, why)
        ext, cls = w
        quality = str(e.params.get("quality", "lossless"))
        fields = dict(kind=kind, document=os.path.basename(g.doc.path or ""), node=nid, rows=[rows[0], rows[-1]],
                      increment=inc, fps=g.fps, written_fps=g.fps / inc, quality=quality)
        self._bake = _Bake(nid, e.key, kind, e.kind == "series", e.src, rows, cls(store.place(e.key, ext, folder), kind, g.fps / inc, quality), fields)
        g.note(nid, "")
        self.baked.emit(nid, 0, len(rows))
        if self._bake.series:
            with self._cv:
                self._clip_gen += 1
                self._clip_on = True

    def _refuse(self, nid, why):
        self.graph.note(nid, why)
        self.bakeRefused.emit(nid, why)

    def _bake_one(self):
        b = self._bake
        row = b.rows[b.i]
        v = self.graph.compute(b.src, row)
        if v is None:
            return self._bake_fail(f"nothing reaches {b.src} at row {row}")
        b.writer.write(v)
        b.i += 1
        self.baked.emit(b.nid, b.i, len(b.rows))
        if b.i == len(b.rows):
            self._bake_finish()

    def _bake_series(self, results):
        """Writes a series bake from the clip walk's result for the node: its rows, or its signal."""
        b = self._bake
        r = None if results is None else results.get(b.nid)
        if not isinstance(r, dict) or "signal" not in r:
            return self._bake_fail(f"the clip walk handed {b.nid} no signal")
        data = r["rows"] if "rows" in r else r["signal"]
        try:
            for b.i, row in enumerate(b.rows, 1):
                b.writer.write(data[row])
        except Exception as exc:
            return self._bake_fail(f"the writer raised at row {b.rows[b.i - 1]}: {type(exc).__name__}: {exc}")
        self.baked.emit(b.nid, b.i, len(b.rows))
        self._bake_finish()

    def _bake_finish(self):
        b = self._bake
        try:
            b.writer.close()
            shape = b.writer.shape
            store.write_sidecar(b.key, os.path.dirname(b.writer.path), **b.fields, shape=list(shape) if shape else [])
        except Exception as exc:
            return self._bake_fail(f"could not land the file: {type(exc).__name__}: {exc}")
        node = self.graph.doc.node(b.nid)
        node.mode, node.baked = "baked", b.key
        self._bake = None
        self.bakeDone.emit(b.nid, b.key)

    def _bake_fail(self, why):
        """Abandons the bake in progress, if any, leaving no file, with `why` in the node's standing."""
        b = self._bake
        if b is None:
            return
        self._bake = None
        try:
            b.writer.abort()
        except OSError:
            pass
        self._refuse(b.nid, why)

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
