"""The one thread that runs tools: the ladder, a scrub, then a bake's change of state, then a bake row behind
a finished window, then the window walk, then the clip walk, and the condition it waits on. Each rung is a
job, _Scrub, _Bake and two _Walk, holding its own state and doing one thing with a turn; the GUI side sets a
job's ask under the lock and the scheduler takes it and tells the job to begin, once. The window walk keeps
the densities, and each walk reports its rows to the probe in its own lane; the clip walk runs behind a finished window so what is viewed never
waits on it, a frame change abandons it and its rows, and it is what a series bake writes from. A stack holds
images by shape, one row each, and tables in an object array, one table a row, so a walked node handing out a
table never reads as a graph changing shape; there is none without a series chain, and either range stops at
STACK_BYTES. Each row steps the chain's prefix, the nodes the plan says step, once; the rest runs whole over the
prefix's accumulated result at each cadence row. A frame bake streams rows into a store writer, holding only the row it writes."""
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


def _log(text):
    print(f"SIEVE {time.strftime('%H:%M:%S')}: {text}", file=sys.stderr)


def _stack_for(n, out):
    return np.empty(n, object) if out.dtype.fields is not None else np.empty((n,) + out.shape, out.dtype)


def _fits(stack, out):
    """Whether `out` is a row of `stack`: a table into an object stack, an image by shape and dtype."""
    if stack.dtype == object:
        return out.dtype.fields is not None
    return stack.shape[1:] == out.shape and stack.dtype == out.dtype


class _Scrub:
    name = "scrub"      # the lane its events are in

    def __init__(self, graph, rowReady, failed):
        self.graph, self.rowReady, self.failed = graph, rowReady, failed
        self.row = None

    def turn(self, row):
        self.row = row
        g = self.graph
        with g.decoder.scrub():   # the display's jump lands on its own cursor, not the walk's
            g.compute(g.shown, row)
            if g.over is not None:
                g.compute(g.over, row)
        self.rowReady.emit(row)

    def cancelled(self):
        pass

    def ended(self):
        pass            # the display asked past the end; the window follows the count and asks again

    def raised(self, exc):
        self.failed.emit(self.row, getattr(exc, "sieve_node", ""))


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
    """One range of the walk, the window's or the clip's: the graph it walks, what it was asked under
    and walked under, the rows it holds, and the signals its progress, chain result and refusal go out on."""
    graph: object
    name: str           # "window" or "clip": the lane its events are in
    every: int          # the cadence, in rows, at which the chain's result goes out
    progress: object    # Signal(int, int): rows done, rows in the range
    ready: object       # Signal(object, int, float): the chain's {node: result}, start, fps
    refused: object     # Signal(str): the range closed short, and why
    failed: object      # Signal(int, str): a tool raised at this row, on this node
    densities: object = None    # Signal(object, int) the window's plane densities go out on; None, and the walk folds none
    bake: object = None # the _Bake this range writes for, the clip's alone: told the result at the end and a refusal
    asked: bool = False # set under the worker's lock by anything that restarts this range; the scheduler takes it
    ask: tuple = (0, 0) # (start, length) the range was asked over; the clip's is the clip
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

    def begin(self, start, length):
        """Starts over `length` rows from `start`, dropping every row held, and tells the probe a walk began."""
        self.start, self.length = start, length
        self.drop()
        if length:
            self.graph.began(start, length)

    def drop(self):
        self.i = self.bytes = 0
        self.stack, self.dens, self.folded, self.stepped = None, {}, {}, {}

    def turn(self):
        g = self.graph
        row = self.start + self.i
        headed = g.walk is None      # a served series node heads the chain: the rows are its file's, and nothing is walked for them
        out = None if headed else np.asarray(g.walk_row(row))
        planes = {nid: v for nid in g.frame_nodes() if (v := g.density(nid, row)) is not None} if self.densities is not None and not headed else {}
        stacked = bool(g.chain) and not headed      # without a chain nothing reads the stack, and the rows are not held
        if self.i and ((self.stack is not None) != stacked or (stacked and not _fits(self.stack, out))
                       or planes.keys() != self.dens.keys()):
            self.drop()      # the nodes or the shape changed under the walk; start over
            g.began(self.start, self.length)
            return
        if not self.i:
            if stacked and self.length * nbytes(out) > STACK_BYTES:
                self.refuse(f"the {self.name}'s stack would be {self.length * nbytes(out) / 2**30:.1f} GB; "
                            f"{', '.join(g.heads)} do not share a fold()")
                return
            self.stack = _stack_for(self.length, out) if stacked else None
            self.dens = {nid: np.zeros((self.length, density.BINS), np.uint32) for nid in planes}
        if stacked:
            self.stack[self.i] = out
            self.bytes += nbytes(out)
        for nid, v in planes.items():
            self.dens[nid][self.i] = v
        self.step(self.i + 1)
        self.i += 1
        if self.bytes > STACK_BYTES:
            self.refuse(f"the {self.name}'s stack reached {self.bytes / 2**30:.1f} GB at row {row}; the rows walked stand")
            return
        self.progress.emit(self.i, self.length)
        g.progress(self.i, self.length)
        if self.i == self.length or self.i % self.every == 0:
            self.emit()

    def step(self, rows):
        """Brings every node the plan steps up to `rows` of the range; one whose raw key is not the
        one it was stepped under starts over from the range's first row. A head is handed the stacked
        row through its own fold() when the stack holds the rows unfolded, or its file's row when it
        serves a bake; a chain node what its source's share feeds under the source's band."""
        g = self.graph
        chain = g.series_chain()
        heads, shared = set(g.heads), g.fold is not None
        bands = {nid: band for nid, _, _, band, _ in chain}
        stepping = [(nid, g.entry(nid), params, src) for nid, _, params, _, src in chain if g.entry(nid).steps]
        for nid in [n for n in self.stepped if n not in {s[0] for s in stepping}]:
            self.bytes -= self.stepped.pop(nid).bytes
        for nid, e, params, src in stepping:
            held = self.stepped.get(nid)
            if held is None or held.key != e.raw_key:
                if held is not None:
                    self.bytes -= held.bytes
                held = self.stepped[nid] = _Stepped(e.raw_key)
            fold = None if shared or nid not in heads else getattr(e.tool, "fold", None)
            for r in range(held.rows, rows):
                if e.bake is not None:
                    row = g.baked_series(nid)[self.start + r]
                elif nid in heads:
                    row = self.stack[r] if fold is None else fold(self.stack[r])
                else:
                    up = self.stepped[src]
                    row = fed_row({f: a[r] for f, a in up.fields.items()}, bands[src])
                with g.demand("walk", nid), g.probe(nid, self.start + r, e.raw_key) as ev:
                    try:
                        held.state, share = e.tool.step(held.state, row, r, params)
                    except Exception as exc:
                        exc.sieve_node = nid
                        g.note(nid, f"raised stepping row {self.start + r}: {type(exc).__name__}: {exc}")
                        raise
                    ev[0], ev[1] = "step", sum(nbytes(v) for v in share.values())
                for f, v in share.items():
                    a = held.fields.get(f)
                    if a is None:
                        a = held.fields[f] = np.empty(self.length, object if isinstance(v, np.ndarray) else np.asarray(v).dtype)
                    a[r] = v
                held.rows = r + 1
                held.bytes += ev[1]
                self.bytes += ev[1]
            g.note(nid, "")

    def emit(self):
        if not self.i:
            return
        g = self.graph
        if self.densities is not None:
            self.densities.emit({nid: d[: self.i] for nid, d in self.dens.items()}, self.start)
        results = None
        if self.stack is not None or served_head(g):
            self.step(self.i)
            stepped = {nid: {f: a[: self.i] for f, a in h.fields.items()} for nid, h in self.stepped.items()}
            results = run_chain(g, None if self.stack is None else self.stack[: self.i], self.start, self.i, self.folded, stepped)
        if results is not None:
            self.ready.emit(results, self.start, g.fps)
        if self.bake is not None and self.i == self.length:
            self.bake.from_clip(results)

    def halt(self):
        """Stopped: the rows it has stand, and the count says so."""
        self.length = self.i
        self.progress.emit(self.i, self.length)

    def close(self):
        """Returns the exception the chain raised over the rows held, if it did, the range closed
        with its progress alone: the handlers that close on a tool's first raise must not raise on
        its second."""
        self.halt()
        self.graph.progress(self.i, self.length)
        try:
            self.emit()
        except Exception as exc:
            traceback.print_exc()
            return exc

    def refuse(self, why):
        exc = self.close()
        if exc is not None:
            self.failed.emit(self.start + self.i, getattr(exc, "sieve_node", ""))
        self.refused.emit(why)
        if self.bake is not None:
            self.bake.abandon(f"the clip walk was refused: {why}")

    def cancelled(self):
        pass            # the graph moved on under the row: the next turn reads the new state

    def ended(self):
        exc = self.close()
        if exc is not None:
            self.failed.emit(self.start + self.i, getattr(exc, "sieve_node", ""))

    def raised(self, exc):
        row = self.start + self.i
        again = self.close()
        self.failed.emit(row, getattr(again, "sieve_node", getattr(exc, "sieve_node", "")))


@dataclass
class _Writing:
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


class _Bake:
    """The bake job: the ask the GUI side left, taken by the scheduler, and the _Writing in progress.
    `store` is where the next bake lands and may be replaced between bakes; `ask_clip` asks the worker
    for the clip walk a series bake writes from."""
    name = "bake"       # the lane its events are in

    def __init__(self, graph, every, store, baked, bakeDone, bakeRefused, ask_clip):
        self.graph, self.every, self.store, self.ask_clip = graph, every, store, ask_clip
        self.baked, self.bakeDone, self.bakeRefused = baked, bakeDone, bakeRefused
        self.asked = False
        self.ask = (None, "", "")       # (the node to bake, or None, its document's name, and why the one running is to go)
        self.at = None                  # the _Writing in progress
        self.starting = None            # the node begin() last tried to start: what a raise before `at` exists is refused on

    def due(self):
        """Whether a frame bake has a row to write; a series bake waits on the clip walk."""
        return self.at is not None and not self.at.series and self.at.i < len(self.at.rows)

    def begin(self, nid, document, why):
        self.abandon(why)
        self.starting = nid
        if nid is not None:
            self.start(nid, document)

    def start(self, nid, document=""):
        """Starts a bake of `nid`'s input, or refuses it with the reason in the node's standing: a
        node serving its bake, an input unwired or unfed, a kind with no writer, a range that names
        no row, a store that cannot be written. The rows and quality are the tool's to read off its
        params, through its `bake` facet. A series bake asks for the clip walk and writes when it completes."""
        g = self.graph
        e = g.entry(nid)
        if e is not None and e.bake is not None:
            return self.refuse(nid, "serving its bake; go live to rebake")
        if e is None or e.src is None:
            return self.refuse(nid, "in is unwired")
        if not e.fed:
            return self.refuse(nid, e.standing or f"in waits on {e.src}")
        kind = e.types.get(INPUT)
        wr = writer(kind)
        if wr is None:
            return self.refuse(nid, f"no writer for {kind}; a bake writes {', '.join(kinds())}")
        try:
            rows, quality = e.tool.bake(e.params, g.count)
        except (TypeError, ValueError) as exc:
            return self.refuse(nid, f"the range does not read: {exc}")
        if not rows:
            return self.refuse(nid, f"the range names no row of the clip's {g.count}")
        inc = rows.step
        store = self.store
        why = store.probe()
        if why:
            return self.refuse(nid, why)
        ext, cls = wr
        path, side = store.place(e.key, ext), store.sidecar(e.key)
        if side is not None and os.path.exists(path):
            # the store has this key already, from this document or another sharing the chain: served, not encoded again
            g.note(nid, "")
            self.baked.emit(nid, len(rows), len(rows))
            _log(f"bake {nid}: {e.key} is in the store at {store.folder}, written {side.written}; serving it")
            return self.bakeDone.emit(nid, side.bake(g.count))
        g.readers.release(e.key)        # a reader left on a file of this key would hold it against the landing on Windows
        side = Sidecar(e.key, kind, document, nid, [rows[0], rows[-1]], inc, g.fps, g.fps / inc, [], quality)
        self.at = _Writing(nid, e.key, kind, e.kind == "series", e.src, rows, cls(path, kind, g.fps / inc, quality), side, store)
        g.note(nid, "")
        self.baked.emit(nid, 0, len(rows))
        _log(f"bake {nid}: {kind} rows {rows[0]}..{rows[-1]} every {inc}, {quality}, key {e.key} -> {store.folder}, "
             f"{store.free() >> 20} MB free")
        if self.at.series:
            self.ask_clip()

    def refuse(self, nid, why):
        self.graph.note(nid, why)
        self.bakeRefused.emit(nid, why)

    def turn(self):
        b = self.at
        row = b.rows[b.i]
        v = self.graph.compute(b.src, row, demand="bake")
        if v is None:
            return self.abandon(f"nothing reaches {b.src} at row {row}")
        b.writer.write(v)
        b.i += 1
        self.baked.emit(b.nid, b.i, len(b.rows))
        if b.i == len(b.rows):
            self.finish()
        elif b.i % self.every == 0 and (free := b.store.free()) < LOW_DISK:
            self.abandon(f"stopped at row {row}: the disk under {b.store.folder} has {free >> 20} MB free")

    def from_clip(self, results):
        """Writes a series bake from the clip walk's result for the node: its rows, or its signal.
        The result must be the chain the bake was asked under; a series change meanwhile, which
        reruns the chain without restarting the walk, would otherwise be written under the old key."""
        b = self.at
        if b is None or not b.series:
            return
        if self.graph.key(b.nid) != b.key:
            return self.abandon("abandoned: a tool upstream changed")
        r = None if results is None else results.get(b.nid)
        if not isinstance(r, dict) or "signal" not in r:
            return self.abandon(f"the clip walk handed {b.nid} no signal")
        data = r["rows"] if "rows" in r else r["signal"]
        try:
            for b.i, row in enumerate(b.rows, 1):
                b.writer.write(data[row])
        except Exception as exc:
            return self.abandon(f"the writer raised at row {b.rows[b.i - 1]}: {type(exc).__name__}: {exc}")
        self.baked.emit(b.nid, b.i, len(b.rows))
        self.finish()

    def finish(self):
        """The document is the GUI's to write: the Bake goes out on bakeDone and no node is touched here."""
        b = self.at
        try:
            b.writer.close()
            side = b.store.write_sidecar(replace(b.side, shape=list(b.writer.shape or ())))
        except Exception as exc:
            if os.path.exists(b.writer.path) and b.store.sidecar(b.key) is None:
                os.remove(b.writer.path)        # landed without its sidecar: not ours, so not left
            return self.abandon(f"could not land the file: {type(exc).__name__}: {exc}")
        self.at = None
        _log(f"bake {b.nid}: landed {b.key} after {time.perf_counter() - b.t0:.0f} s, {len(b.rows)} rows, "
             f"{os.path.getsize(b.writer.path) >> 20} MB")
        self.bakeDone.emit(b.nid, side.bake(self.graph.count))

    def abandon(self, why):
        """Abandons the bake in progress, if any, leaving no file, with `why` in the node's standing."""
        b = self.at
        if b is None:
            return
        self.at = None
        try:
            b.writer.abort()
        except OSError:
            pass
        _log(f"bake {b.nid}: {why}; nothing written, after {time.perf_counter() - b.t0:.0f} s and {b.i} rows")
        self.refuse(b.nid, why)

    def cancelled(self):
        self.abandon("abandoned: the graph moved on")

    def ended(self):
        self.abandon(f"the stream ended at row {self.graph.count}, inside the range")

    def raised(self, exc):
        b = self.at
        if b is None:
            if self.starting is not None:
                self.refuse(self.starting, f"did not start: {type(exc).__name__}: {exc}")
            return
        row = b.rows[b.i] if b.i < len(b.rows) else "?"
        self.abandon(f"{getattr(exc, 'sieve_node', '') or 'the writer'} raised at row {row}: {type(exc).__name__}: {exc}")


def served_head(graph):
    """Whether a series node serving its bake heads the chain, so its rows are its file's and nothing is walked for them."""
    return any(graph.entry(h).bake is not None for h in graph.heads)


def run_chain(graph, stack, start, done, folds, stepped=None):
    """The series chain over `stack`, the walked node's rows from `start`, `done` of them so
    far, with `folds` the stack's own cache of each head's folding and `stepped` the result
    accumulated over those rows for each node the walk stepped, which runs nothing here:
    {node: result}, each gated and keyed; None when there is no chain."""
    chain = graph.series_chain()
    if not chain:
        return None
    results, feeds, fps = {}, {}, graph.fps
    heads, folded = set(graph.heads), graph.fold is not None
    buffer = None if stack is None else stack.base if stack.base is not None else stack
    for nid, tool, params, band, src in chain:
        if stepped is not None and nid in stepped:
            results[nid], feeds[nid] = gated(stepped[nid], band)
            graph.note(nid, "")
            if isinstance(results[nid], dict):
                results[nid] = {**results[nid], "key": graph.key(nid), "plate": graph.plate}
            continue
        if nid in heads and graph.entry(nid).bake is not None:
            series = Series(graph.baked_series(nid)[start: start + done], graph.key(nid), start, fps)
        elif nid in heads and stack is None:
            continue        # a head with nothing walked for it: its standing says why
        elif nid in heads:
            fold = None if folded else getattr(tool, "fold", None)
            if fold is not None:
                held = folds.get(id(fold))
                if held is None or held[0] is not buffer or held[1] != len(stack):
                    held = (buffer, len(stack), np.stack([fold(row) for row in stack]) if len(stack) else np.zeros((0, 0)))
                    folds[id(fold)] = held
            series = Series(stack if fold is None else held[2], graph.key(src), start, fps)
        elif feeds.get(src) is not None:
            series = Series(feeds[src], graph.key(src), start, fps)
        else:
            graph.note(nid, f"{src} handed out no signal")
            continue
        with graph.demand("walk", nid), graph.probe(nid, start + done - 1, graph.key(nid)) as ev:
            try:
                results[nid], feeds[nid] = gated(tool.run(series, params), band)
            except Exception as exc:
                exc.sieve_node = nid
                graph.note(nid, f"raised over {done} rows from {start}: {type(exc).__name__}: {exc}")
                raise
            ev[1] = Memo._size(results[nid])
        graph.note(nid, "")
        if isinstance(results[nid], dict):
            results[nid] = {**results[nid], "key": graph.key(nid), "plate": graph.plate}   # beside its gate: what a tool that writes a file records
    return results


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
        self.graph, self.every = graph, every
        self._cv = threading.Condition()
        self._want = None
        self._stop = False
        self._series_dirty = False
        self._clip_on = False                 # whether a clip walk is wanted
        self._scrub = _Scrub(graph, self.rowReady, self.failed)
        self._bake = _Bake(graph, every, current() if store is None else store, self.baked, self.bakeDone, self.bakeRefused, self.walk_clip)
        self._win = _Walk(graph, name="window", every=every, progress=self.walked, ready=self.seriesReady,
                          refused=self.walkRefused, failed=self.failed, densities=self.densityReady)
        self._clip = _Walk(graph, name="clip", every=every, progress=self.clipWalked, ready=self.clipReady,
                           refused=self.clipRefused, failed=self.failed, bake=self._bake)

    @property
    def store(self):
        """Where the next bake lands; a store chosen while one runs is the next bake's."""
        return self._bake.store

    @store.setter
    def store(self, s):
        self._bake.store = s

    # -- GUI-side calls --------------------------------------------------
    def bake(self, nid, document=""):
        """Write `nid`'s input to the store over its range, after the window is walked; one bake at a
        time. `document` is the name the sidecar records as the one that first wrote the file."""
        with self._cv:
            self._bake.ask, self._bake.asked = (nid, document, "superseded by another bake"), True
            self._cv.notify()

    def cancel_bake(self):
        with self._cv:
            self._bake.ask, self._bake.asked = (None, "", "cancelled"), True
            self._cv.notify()

    @property
    def bake_bytes(self):
        """What the bake holds: the row its writer is writing, 0 between rows and with no bake running."""
        b = self._bake.at
        return 0 if b is None else b.writer.bytes

    def request_row(self, row):
        with self._cv:
            self._want = row
            self._cv.notify()

    def set_window(self, start, length):
        with self._cv:
            self._win.ask, self._win.asked = (start, length), True
            self._cv.notify()

    def invalidate(self):
        """A frame tool changed: restart the walk from the window start, and drop the clip walk,
        whose rows were of a graph that is gone. A bake in progress goes only when its key did,
        a change upstream of it; one elsewhere in the graph leaves it writing, and a series bake
        asks for its clip walk again."""
        with self._cv:
            self._win.asked = self._clip.asked = True
            self._clip_on = False
            b = self._bake.at
            if b is not None:
                e = self.graph.entry(b.nid)
                if e is None or e.key != b.key:
                    self._bake.ask, self._bake.asked = (None, "", "abandoned: a tool upstream changed"), True
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
            self._clip.asked = True
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
    def run(self):
        threading.current_thread().name = "worker"      # what the probe's events name as their thread
        try:
            self._serve()
        except BaseException:
            traceback.print_exc()   # _serve answers for a tool's exceptions; one reaching here ends the thread, and `finished` says so
            raise

    def _serve(self):
        """The loop: waits until a rung is due, takes its turn, and reads the asks again."""
        while True:
            with self._cv:
                while not self._stop and (turn := self._turn()) is None:
                    self._cv.wait()
                if self._stop:
                    self._bake.abandon("the video was closed")
                    return
            serves, steps = turn
            self.graph.readers.reap()
            job = None
            try:
                for job, act in steps:
                    self.graph.serving(serves, job.name)
                    act()
            except Cancelled:
                job.cancelled()     # the graph moved on under the row, or we are stopping: the loop reads the new state
            except EndOfStream:
                self.shortened.emit(self.graph.count)
                job.ended()
            except Exception as e:
                traceback.print_exc()
                job.raised(e)

    def _turn(self):
        """The ladder: a scrub, then a bake's change of state, then a bake row behind a finished
        window, then the window walk, then the clip walk. Returns the first rung due as what
        its events serve and the (job, call) steps that are its turn, or None when no rung
        is, which is the condition the loop waits on, so waking means turning. Called under the
        lock; the ask of the rung picked is taken here, so one landing meanwhile is not lost."""
        scrub, bake, win, clip, g = self._scrub, self._bake, self._win, self._clip, self.graph
        if self._want is not None:
            row, self._want = self._want, None
            return "scrub", [(scrub, lambda: scrub.turn(row))]
        if bake.asked:
            ask, bake.asked = bake.ask, False
            return "walk", [(bake, lambda: bake.begin(*ask))]
        count = g.count
        fed = g.fed(g.walk) or served_head(g)
        if win.asked:
            (start, length), win.asked = win.ask, False
            s = max(0, min(start, count - 1))
            n = max(0, min(length, count - s)) if fed else 0   # nothing reaches a walked node and no served series node heads the chain: nothing to walk until the next change
            return "walk", [(win, lambda: win.begin(s, n))]
        if self._series_dirty:
            self._series_dirty = False
            if fed and win.i:
                return "walk", [(win, win.emit)] + ([(clip, clip.emit)] if clip.i else [])
        if bake.due() and win.i >= win.length:
            return "bake", [(bake, bake.turn)]
        if fed and win.i < win.length:
            return "walk", [(win, win.turn)]
        if clip.asked:
            on, clip.asked = self._clip_on, False

            def begin():
                clip.begin(0, count if on and fed else 0)
                if not clip.length:
                    clip.ready.emit({}, 0, g.fps)
                clip.progress.emit(clip.i, clip.length)
            return "walk", [(clip, begin)]
        if clip.i < clip.length:
            if self._clip_on and fed:
                return "walk", [(clip, clip.turn)]
            on = self._clip_on

            def halt():
                clip.halt()
                if not on:
                    bake.abandon("the clip walk was stopped short of the clip")
            return "walk", [(clip, halt)]
        return None
