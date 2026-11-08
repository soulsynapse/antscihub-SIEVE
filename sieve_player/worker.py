"""The one thread that runs tools. Serves display requests first, walks the loop window, bakes a node
one row at a time in the time the window leaves, and walks the whole clip when asked after that.

The window walk and the clip walk are one job, _Walk, over two ranges: the window's keeps the
densities and reports to the probe, the clip's runs behind a finished window walk so what is viewed
never waits on it, and a frame change abandons it and its rows, and a bake whose key it changed. A
stack holds images by shape, one row each, and tables in an object array, one table a row, so a
walked node handing out a table never reads as a graph changing shape; there is none without a series chain, and either
range stops at STACK_BYTES. Each row steps the chain's prefix, the nodes the plan says step, once; the rest runs whole over
the prefix's accumulated result at each cadence row. A bake on a frame wire streams the node's input into a store writer, holding only the row it writes; on a series wire it writes from the clip walk's result."""
import os
import sys
import threading
import time
import traceback
from dataclasses import dataclass, field, replace

import numpy as np
from PySide6.QtCore import QThread, Signal

from . import density
from .decoder import EndOfStream
from .document import INPUT
from .graph import Cancelled, Memo, Series, fed_row, gated, nbytes
from .store import Sidecar, current, kinds, writer

STACK_BYTES = 512 << 20   # the most a walk's stack and stepped results, the window's or the clip's, may take, as nbytes counts them
STOP_PATIENCE_MS = 10_000  # how long stop() waits before saying on stderr what it is waiting for
LOW_DISK = 256 << 20      # a bake stops, whole, when the store's disk has less than this free, rather than when the writer hits the wall


@dataclass
class _Stepped:
    """A stepping node's progress over a range: the key it is stepped under, the state its tool
    returned last, its result accumulated over `rows` rows, and the bytes the result holds."""
    key: str
    state: object = None
    fields: dict = field(default_factory=dict)
    rows: int = 0
    bytes: int = 0


@dataclass
class _Walk:
    """One range of the walk, the window's or the clip's: what it was asked under and walked under,
    the rows it holds, and the signals its progress, chain result and refusal go out on."""
    name: str
    densities: bool     # whether the walk folds and hands out each frame node's plane densities
    probes: bool        # whether its rows reach the probe as progress events; the monitor's walk scope is the window's
    progress: object    # Signal(int, int): rows done, rows in the range
    ready: object       # Signal(object, int, float): the chain's {node: result}, start, fps
    refused: object     # Signal(str): the range closed short, and why
    asked: int = 0      # bumped under the worker's lock by anything that restarts this range
    gen: int = -1       # what the stack was walked under
    start: int = 0
    length: int = 0
    i: int = 0
    bytes: int = 0
    stack: object = None
    dens: dict = field(default_factory=dict)      # node -> (length, BINS) counts, for the planes the walk computes
    # fold id -> (the stack's buffer, rows, that head's own folding of the stack); the buffer is held, not
    # its id, since a freed buffer's address comes back for the next stack of the same shape
    folded: dict = field(default_factory=dict)
    stepped: dict = field(default_factory=dict)   # node -> _Stepped

    def begin(self, gen, start, length):
        """Starts over under `gen` over `length` rows from `start`, dropping every row held."""
        self.gen, self.start, self.length = gen, start, length
        self.drop()

    def drop(self):
        self.i = self.bytes = 0
        self.stack, self.dens, self.folded, self.stepped = None, {}, {}, {}

    def pending(self):
        return self.asked != self.gen or self.i < self.length


@dataclass
class _Bake:
    """A bake in progress: the node, the key its file is named by, the rows it writes and the writer."""
    nid: str
    key: str
    kind: str           # the kind flowing into the node, what the file holds
    series: bool        # written from the clip walk's result, not row by row
    src: str
    rows: range         # the plate rows, the tool's answer; its step is the increment
    writer: object
    side: Sidecar       # to write at the landing, its shape the writer's to learn
    store: object       # the Store it lands in: a store chosen while it runs is the next bake's
    t0: float = field(default_factory=time.perf_counter)
    i: int = 0
    held: list = field(default_factory=list)


def _log(text):
    print(f"SIEVE {time.strftime('%H:%M:%S')}: {text}", file=sys.stderr)


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
    failed = Signal(int, str)                 # a tool raised at this row, on this node; a walk closes at the rows it has, as a refused one does, a display request is dropped
    clipWalked = Signal(int, int)             # rows done, rows in the clip; done == total when the clip walk is not running
    clipReady = Signal(object, int, float)    # as seriesReady, over the clip walk's rows; {} when the walk was abandoned
    clipRefused = Signal(str)                 # the clip walk did not start, or stopped short of the clip, and why
    walkRefused = Signal(str)                 # the window walk closed short of the window, and why: its stack passed STACK_BYTES
    shortened = Signal(int)                   # the stream ended short of the container's claim: the count as the decoder now has it
    baked = Signal(str, int, int)             # a bake's progress: the node, rows written, rows to write
    bakeDone = Signal(str, object)            # the node's bake landed, as the Bake the node is to save (document.land)
    bakeRefused = Signal(str, str)            # the bake did not start or did not finish, and why; the node's standing says the same

    def __init__(self, graph, every=30, store=None):
        """`every` is the cadence, in rows walked, at which either range runs its chain; `store`, a
        store.Store, is where a bake lands, the current one unless another is handed in."""
        super().__init__()
        self.graph, self.every, self.store = graph, every, current() if store is None else store
        self._cv = threading.Condition()
        self._want = None
        self._stop = False
        self._series_dirty = False
        self._window = (0, 0)
        self._win = _Walk("window", True, True, self.walked, self.seriesReady, self.walkRefused)
        self._clip = _Walk("clip", False, False, self.clipWalked, self.clipReady, self.clipRefused)
        self._clip_on = False                 # whether a clip walk is wanted
        self._bake_gen, self._bake_walk_gen = 0, 0   # bumped by bake, cancel_bake and invalidate; what the thread last acted on
        self._bake_ask = (None, "", "")               # (the node to bake, or None, its document's name, and why the one running is to go)
        self._bake = None                             # the _Bake in progress

    # -- GUI-side calls --------------------------------------------------
    def bake(self, nid, document=""):
        """Write `nid`'s input to the store over its range, after the window is walked; one bake at a
        time. `document` is the name the sidecar records as the one that first wrote the file."""
        with self._cv:
            self._bake_ask = (nid, document, "superseded by another bake")
            self._bake_gen += 1
            self._cv.notify()

    def cancel_bake(self):
        with self._cv:
            self._bake_ask = (None, "", "cancelled")
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
            self._win.asked += 1
            self._cv.notify()

    def invalidate(self):
        """A frame tool changed: restart the walk from the window start, and drop the clip walk,
        whose rows were of a graph that is gone. A bake in progress goes only when its key did,
        a change upstream of it; one elsewhere in the graph leaves it writing, and a series bake
        asks for its clip walk again."""
        with self._cv:
            self._win.asked += 1
            self._clip.asked += 1
            self._clip_on = False
            b = self._bake
            if b is not None:
                e = self.graph.entry(b.nid)
                if e is None or e.key != b.key:
                    self._bake_ask = (None, "", "abandoned: a tool upstream changed")
                    self._bake_gen += 1
                elif b.series:
                    self._clip_on = True
            self._cv.notify()

    def rerun_series(self):
        """Only the series tool changed: rerun it on the stack we already have, and on the clip's."""
        with self._cv:
            self._series_dirty = True
            self._cv.notify()

    def walk_clip(self):
        """Walk the whole clip, from its first row, once the window is walked."""
        with self._cv:
            self._clip.asked += 1
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
        win, clip = self._win, self._clip
        while True:
            with self._cv:
                while not (self._stop or self._want is not None or self._series_dirty or win.pending()
                           or clip.pending() or self._bake_pending()):
                    self._cv.wait()
                if self._stop:
                    self._bake_fail("the video was closed")
                    return
                want, self._want = self._want, None
                gen, (start, length) = win.asked, self._window
                dirty = False
                if want is None:
                    dirty, self._series_dirty = self._series_dirty, False
                clip_gen, clip_on = clip.asked, self._clip_on
                bake_gen, (bake_ask, bake_doc, bake_why) = self._bake_gen, self._bake_ask
            which = "window"
            self.graph.readers.reap()
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
                        self._bake_begin(bake_ask, bake_doc)
                    continue
                b = self._bake
                if b is not None and not b.series and not dirty and gen == win.gen and win.i >= win.length:
                    which = "bake"
                    self.graph.serving("bake")
                    self._bake_one()
                    continue
                count = self.graph.count
                if not (self.graph.fed(self.graph.walk) or self._served_head()):
                    # nothing reaches a walked node and no served series node heads the chain: nothing to do until the next change
                    if gen != win.gen:
                        s = max(0, min(start, count - 1))
                        win.begin(gen, s, max(0, min(length, count - s)))
                        win.i = win.length
                    if clip_gen != clip.gen:
                        clip.begin(clip_gen, 0, 0)
                        clip.ready.emit({}, 0, self.graph.fps)
                        clip.progress.emit(0, 0)
                    elif clip.i < clip.length:
                        clip.length = clip.i
                        clip.progress.emit(clip.i, clip.length)
                    continue
                if gen != win.gen:
                    s = max(0, min(start, count - 1))
                    win.begin(gen, s, max(0, min(length, count - s)))
                if dirty and win.i:
                    self._emit(win)
                    if clip.i:
                        self._emit(clip)
                    continue
                if win.i < win.length:
                    self._walk_one(win)
                    continue
                which = "clip"
                if clip_gen != clip.gen:
                    clip.begin(clip_gen, 0, count if clip_on else 0)
                    if not clip_on:
                        clip.ready.emit({}, 0, self.graph.fps)
                    clip.progress.emit(clip.i, clip.length)
                elif not clip_on and clip.i < clip.length:
                    clip.length = clip.i        # stopped: the rows it has stand, and the count says so
                    clip.progress.emit(clip.i, clip.length)
                    self._bake_fail("the clip walk was stopped short of the clip")
                if clip_on and clip.i < clip.length:
                    self._walk_one(clip)
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
                else:
                    job = clip if which == "clip" else win
                    exc = self._close(job)
                    if exc is not None:
                        self.failed.emit(job.start + job.i, getattr(exc, "sieve_node", ""))
            except Exception as e:
                traceback.print_exc()
                nid = getattr(e, "sieve_node", "")
                if want is not None:
                    self.failed.emit(want, nid)
                elif which == "bake":
                    b = self._bake
                    row = b.rows[b.i] if b is not None and b.i < len(b.rows) else "?"
                    self._bake_fail(f"{nid or 'the writer'} raised at row {row}: {type(e).__name__}: {e}")
                else:
                    job = clip if which == "clip" else win
                    row = job.start + job.i
                    again = self._close(job)
                    self.failed.emit(row, getattr(again, "sieve_node", nid))

    def _walk_one(self, job):
        row = job.start + job.i
        headed = self.graph.walk is None      # a served series node heads the chain: the rows are its file's, and nothing is walked for them
        out = None if headed else np.asarray(self.graph.walk_row(row))
        planes = {nid: v for nid in self.graph.frame_nodes() if (v := self.graph.density(nid, row)) is not None} if job.densities and not headed else {}
        stacked = bool(self.graph.chain) and not headed      # without a chain nothing reads the stack, and the rows are not held
        if job.i and ((job.stack is not None) != stacked or (stacked and not _fits(job.stack, out))
                      or planes.keys() != job.dens.keys()):
            job.drop()      # the nodes or the shape changed under the walk; start over
            return
        if not job.i:
            if stacked and job.length * nbytes(out) > STACK_BYTES:
                self._refuse_walk(job, f"the {job.name}'s stack would be {job.length * nbytes(out) / 2**30:.1f} GB; "
                                       f"{', '.join(self.graph.heads)} do not share a fold()")
                return
            job.stack = _stack_for(job.length, out) if stacked else None
            job.dens = {nid: np.zeros((job.length, density.BINS), np.uint32) for nid in planes}
        if stacked:
            job.stack[job.i] = out
            job.bytes += nbytes(out)
        for nid, v in planes.items():
            job.dens[nid][job.i] = v
        self._step(job, job.i + 1)
        job.i += 1
        if job.bytes > STACK_BYTES:
            self._refuse_walk(job, f"the {job.name}'s stack reached {job.bytes / 2**30:.1f} GB at row {row}; the rows walked stand")
            return
        job.progress.emit(job.i, job.length)
        if job.probes:
            self.graph.progress(job.i, job.length)
        if job.i == job.length or job.i % self.every == 0:
            self._emit(job)

    def _step(self, job, rows):
        """Brings every node the plan steps up to `rows` of the range; one whose raw key is not the
        one it was stepped under starts over from the range's first row. A head is handed the stacked
        row through its own fold() when the stack holds the rows unfolded, or its file's row when it
        serves a bake; a chain node what its source's share feeds under the source's band."""
        chain = self.graph.series_chain()
        heads, shared = set(self.graph.heads), self.graph.fold is not None
        bands = {nid: band for nid, _, _, band, _ in chain}
        stepping = [(nid, self.graph.entry(nid), params, src) for nid, _, params, _, src in chain if self.graph.entry(nid).steps]
        for nid in [n for n in job.stepped if n not in {s[0] for s in stepping}]:
            job.bytes -= job.stepped.pop(nid).bytes
        for nid, e, params, src in stepping:
            held = job.stepped.get(nid)
            if held is None or held.key != e.raw_key:
                if held is not None:
                    job.bytes -= held.bytes
                held = job.stepped[nid] = _Stepped(e.raw_key)
            fold = None if shared or nid not in heads else getattr(e.tool, "fold", None)
            for r in range(held.rows, rows):
                if e.bake is not None:
                    row = self.graph.baked_series(nid)[job.start + r]
                elif nid in heads:
                    row = job.stack[r] if fold is None else fold(job.stack[r])
                else:
                    up = job.stepped[src]
                    row = fed_row({f: a[r] for f, a in up.fields.items()}, bands[src])
                with self.graph.probe(nid, job.start + r, e.raw_key) as ev:
                    try:
                        held.state, share = e.tool.step(held.state, row, r, params)
                    except Exception as exc:
                        exc.sieve_node = nid
                        self.graph.note(nid, f"raised stepping row {job.start + r}: {type(exc).__name__}: {exc}")
                        raise
                    ev[0], ev[1] = "step", sum(nbytes(v) for v in share.values())
                for f, v in share.items():
                    a = held.fields.get(f)
                    if a is None:
                        a = held.fields[f] = np.empty(job.length, object if isinstance(v, np.ndarray) else np.asarray(v).dtype)
                    a[r] = v
                held.rows = r + 1
                held.bytes += ev[1]
                job.bytes += ev[1]
            self.graph.note(nid, "")

    def _close(self, job):
        """Returns the exception the chain raised over the rows held, if it did, the range closed
        with its progress alone: the handlers that close on a tool's first raise must not raise on
        its second."""
        job.length = job.i
        job.progress.emit(job.i, job.length)
        if job.probes:
            self.graph.progress(job.i, job.length)
        try:
            self._emit(job)
        except Exception as exc:
            traceback.print_exc()
            return exc

    def _refuse_walk(self, job, why):
        exc = self._close(job)
        if exc is not None:
            self.failed.emit(job.start + job.i, getattr(exc, "sieve_node", ""))
        job.refused.emit(why)
        if job is self._clip:
            self._bake_fail(f"the clip walk was refused: {why}")

    def _served_head(self):
        return any(self.graph.entry(h).bake is not None for h in self.graph.heads)

    def _emit(self, job):
        if not job.i:
            return
        if job.densities:
            self.densityReady.emit({nid: d[: job.i] for nid, d in job.dens.items()}, job.start)
        results = None
        if job.stack is not None or self._served_head():
            self._step(job, job.i)
            stepped = {nid: {f: a[: job.i] for f, a in h.fields.items()} for nid, h in job.stepped.items()}
            results = self._run_chain(None if job.stack is None else job.stack[: job.i], job.start, job.i, job.folded, stepped)
        if results is not None:
            job.ready.emit(results, job.start, self.graph.fps)
        if job is self._clip and self._bake is not None and self._bake.series and job.i == job.length:
            self._bake_series(results)

    # -- baking ----------------------------------------------------------
    def _bake_begin(self, nid, document=""):
        """Starts a bake of `nid`'s input, or refuses it with the reason in the node's standing: a
        node serving its bake, an input unwired or unfed, a kind with no writer, a range that names
        no row, a store that cannot be written. The rows and quality are the tool's to read off its
        params, through its `bake` facet. A series bake asks for the clip walk and writes when it completes."""
        g = self.graph
        e = g.entry(nid)
        if e is not None and e.bake is not None:
            return self._refuse(nid, "serving its bake; go live to rebake")
        if e is None or e.src is None:
            return self._refuse(nid, "in is unwired")
        if not e.fed:
            return self._refuse(nid, e.standing or f"in waits on {e.src}")
        kind = e.types.get(INPUT)
        w = writer(kind)
        if w is None:
            return self._refuse(nid, f"no writer for {kind}; a bake writes {', '.join(kinds())}")
        try:
            rows, quality = e.tool.bake(e.params, g.count)
        except (TypeError, ValueError) as exc:
            return self._refuse(nid, f"the range does not read: {exc}")
        if not rows:
            return self._refuse(nid, f"the range names no row of the clip's {g.count}")
        inc = rows.step
        store = self.store
        why = store.probe()
        if why:
            return self._refuse(nid, why)
        ext, cls = w
        path, side = store.place(e.key, ext), store.sidecar(e.key)
        if side is not None and os.path.exists(path):
            # the store has this key already, from this document or another sharing the chain: served, not encoded again
            g.note(nid, "")
            self.baked.emit(nid, len(rows), len(rows))
            _log(f"bake {nid}: {e.key} is in the store at {store.folder}, written {side.written}; serving it")
            return self.bakeDone.emit(nid, side.bake(g.count))
        g.readers.release(e.key)        # a reader left on a file of this key would hold it against the landing on Windows
        side = Sidecar(e.key, kind, document, nid, [rows[0], rows[-1]], inc, g.fps, g.fps / inc, [], quality)
        self._bake = _Bake(nid, e.key, kind, e.kind == "series", e.src, rows, cls(path, kind, g.fps / inc, quality), side, store)
        g.note(nid, "")
        self.baked.emit(nid, 0, len(rows))
        _log(f"bake {nid}: {kind} rows {rows[0]}..{rows[-1]} every {inc}, {quality}, key {e.key} -> {store.folder}, "
             f"{store.free() >> 20} MB free")
        if self._bake.series:
            with self._cv:
                self._clip.asked += 1
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
        elif b.i % self.every == 0 and (free := b.store.free()) < LOW_DISK:
            self._bake_fail(f"stopped at row {row}: the disk under {b.store.folder} has {free >> 20} MB free")

    def _bake_series(self, results):
        """Writes a series bake from the clip walk's result for the node: its rows, or its signal.
        The result must be the chain the bake was asked under; a series change meanwhile, which
        reruns the chain without restarting the walk, would otherwise be written under the old key."""
        b = self._bake
        if self.graph.key(b.nid) != b.key:
            return self._bake_fail("abandoned: a tool upstream changed")
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
        """The document is the GUI's to write: the Bake goes out on bakeDone and no node is touched here."""
        b = self._bake
        try:
            b.writer.close()
            side = b.store.write_sidecar(replace(b.side, shape=list(b.writer.shape or ())))
        except Exception as exc:
            if os.path.exists(b.writer.path) and b.store.sidecar(b.key) is None:
                os.remove(b.writer.path)        # landed without its sidecar: not ours, so not left
            return self._bake_fail(f"could not land the file: {type(exc).__name__}: {exc}")
        self._bake = None
        _log(f"bake {b.nid}: landed {b.key} after {time.perf_counter() - b.t0:.0f} s, {len(b.rows)} rows, "
             f"{os.path.getsize(b.writer.path) >> 20} MB")
        self.bakeDone.emit(b.nid, side.bake(self.graph.count))

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
        _log(f"bake {b.nid}: {why}; nothing written, after {time.perf_counter() - b.t0:.0f} s and {b.i} rows")
        self._refuse(b.nid, why)

    def _run_chain(self, stack, start, done, folds, stepped=None):
        """The series chain over `stack`, the walked node's rows from `start`, `done` of them so
        far, with `folds` the stack's own cache of each head's folding and `stepped` the result
        accumulated over those rows for each node the walk stepped, which runs nothing here:
        {node: result}, each gated and keyed; None when there is no chain."""
        chain = self.graph.series_chain()
        if not chain:
            return None
        results, feeds, fps = {}, {}, self.graph.fps
        heads, folded = set(self.graph.heads), self.graph.fold is not None
        buffer = None if stack is None else stack.base if stack.base is not None else stack
        for nid, tool, params, band, src in chain:
            if stepped is not None and nid in stepped:
                results[nid], feeds[nid] = gated(stepped[nid], band)
                self.graph.note(nid, "")
                if isinstance(results[nid], dict):
                    results[nid] = {**results[nid], "key": self.graph.key(nid), "plate": self.graph.plate}
                continue
            if nid in heads and self.graph.entry(nid).bake is not None:
                series = Series(self.graph.baked_series(nid)[start: start + done], self.graph.key(nid), start, fps)
            elif nid in heads and stack is None:
                continue        # a head with nothing walked for it: its standing says why
            elif nid in heads:
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
                results[nid] = {**results[nid], "key": self.graph.key(nid), "plate": self.graph.plate}   # beside its gate: what a tool that writes a file records
        return results
