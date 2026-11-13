"""The runtime: what the graph says, computed and memoized.

A Graph is built from a document, a decoder and the tools the document's names resolve to. It
snapshots the document on `sync()`, which the window calls after any change, so a worker thread
mid-computation works from one consistent plan and the next computation sees the new one. Params
are read from the document's nodes; the runtime holds none of its own. A node is computed as None
when nothing reaches it: no wire, an unresolved tool, or a wire whose types do not fit.
"""
import threading
from collections import OrderedDict

import numpy as np

from . import density
from .document import INPUT, video_output
from .plan import _key, base_key, facts, plan, shared_fold, walked
from .stream import Emitter

def inband(v, band):
    """Where `v` lies between the band's lo and hi; outside them once lo is above hi, the band
    inside out, as the handles are read in both domains."""
    lo, hi = band
    return (v >= lo) & (v <= hi) if lo <= hi else (v >= lo) | (v <= hi)


def banded(v, band):
    """`v` with every value outside `band` set to zero, inside it when lo is above hi. Only a plane
    of values is banded; a mask, a field or None passes through."""
    if not isinstance(v, np.ndarray) or v.ndim != 2 or v.dtype == bool:
        return v
    return np.where(inband(v, band), v, np.zeros((), v.dtype))


def gated(result, band):
    """A series node's result as the player hands it out: the tool's dict with "gate", the rows its
    signal keeps under the node's band, and `fed`, what a series node downstream reads: the result's
    "rows", one table a row, with each gated-out row emptied, when it has them, else the signal with
    the rest zeroed. A result without a signal passes through ungated, and feeds nothing."""
    if not isinstance(result, dict) or "signal" not in result:
        return result, None
    signal = np.asarray(result["signal"])
    gate = np.ones(len(signal), bool) if band is None else inband(signal, band)
    if "rows" in result:
        fed = np.empty(len(result["rows"]), object)
        fed[:] = [r if g else r[:0] for r, g in zip(result["rows"], gate)]
        return {**result, "gate": gate}, fed
    return {**result, "gate": gate}, np.where(gate, signal, np.zeros((), signal.dtype))


def fed_row(share, band):
    """What a series node downstream is stepped with from one row's `share` of a stepping node's
    result: the row `gated` would feed at that index, the table emptied or the signal zeroed when
    the signal is outside `band`; None for a share without a signal."""
    if not isinstance(share, dict) or "signal" not in share:
        return None
    signal = np.asarray(share["signal"])
    kept = band is None or bool(inband(signal, band))
    if "rows" in share:
        return share["rows"] if kept else share["rows"][:0]
    return share["signal"] if kept else signal.dtype.type(0)


def nbytes(v):
    """The bytes `v` holds: an array's own and, through an object field or an object array, every
    array behind it, since `ndarray.nbytes` counts a contour as its eight-byte pointer; 64 for
    anything else that is not None."""
    if v is None:
        return 0
    if not isinstance(v, np.ndarray):
        return 64
    if not v.dtype.hasobject:
        return v.nbytes
    held = [x for n in v.dtype.names if v.dtype[n] == object for x in v[n].ravel()] if v.dtype.names else v.ravel()
    return v.nbytes + sum(nbytes(x) for x in held)


class Memo:
    """LRU bounded by bytes, as `nbytes` counts them. Image-shaped entries (ndim >= 2) are evicted
    before small ones. An entry put with an owner is pinned: never evicted, counted toward the
    limit, and gone only through `unpin`, which drops every pinned entry whose owner is not in
    `keep`, so whatever a STATIC node has memoized under any key outlives any walk and goes with
    its plan. Each eviction goes to `on_evict(key, bytes)` when set, after the lock is dropped."""

    def __init__(self, limit_bytes):
        self.limit = limit_bytes
        self.bytes = 0
        self._big, self._small, self._pinned = OrderedDict(), OrderedDict(), {}     # pinned: key -> (owner, value)
        self._lock = threading.Lock()
        self.hits = self.misses = self.evictions = 0
        self.on_evict = None

    _size = staticmethod(nbytes)

    def get(self, k):
        with self._lock:
            if k in self._pinned:
                self.hits += 1
                return self._pinned[k][1]
            for d in (self._big, self._small):
                v = d.get(k)
                if v is not None:
                    d.move_to_end(k)
                    self.hits += 1
                    return v
            self.misses += 1
            return None

    def empty(self):
        """Drops every entry, pinned ones with the rest, and tells `on_evict` of none: what is
        emptied on purpose was not discarded for room."""
        with self._lock:
            self._big.clear()
            self._small.clear()
            self._pinned.clear()
            self.bytes = 0

    def unpin(self, keep):
        gone = []
        with self._lock:
            for k in [k for k, (owner, _) in self._pinned.items() if owner not in keep]:
                _, old = self._pinned.pop(k)
                self.bytes -= self._size(old)
                gone.append((k, self._size(old)))
        if self.on_evict is not None:
            for ok, n in gone:
                self.on_evict(ok, n)

    def put(self, k, v, owner=None, size=None):
        """`v` under `k`, pinned to `owner` when one is given; a key already held is left as it is.
        `size` is `nbytes(v)` when the caller has already counted it."""
        gone = []
        with self._lock:
            if k in self._big or k in self._small or k in self._pinned:
                return
            if owner is not None:
                self._pinned[k] = (owner, v)
            elif isinstance(v, np.ndarray) and v.ndim >= 2:
                self._big[k] = v
            else:
                self._small[k] = v
            self.bytes += self._size(v) if size is None else size
            while self.bytes > self.limit:
                src = self._big or self._small
                if not src:
                    break
                ok, old = src.popitem(last=False)
                self.bytes -= self._size(old)
                self.evictions += 1
                gone.append((ok, self._size(old)))
        if self.on_evict is not None:
            for ok, n in gone:
                self.on_evict(ok, n)


class Cancelled(Exception):
    """A run read a frame after the graph had moved on under it, or while the worker was stopping:
    what it was computing is for a plan that is gone, so the read raises instead of serving it. The
    worker drops the row; a tool that catches Exception around a read should let this one through."""


class Frames:
    """What a frame tool's run() gets: frames(r) is the output of the node its first input reads,
    at row r, and frames(r, name) that of another of its INPUTS; frames.type(name) is what the node
    wired into that input produces, for a tool whose EXPECTS admits types its run() must tell
    apart. `key` changes whenever anything upstream of any input does. It reads through the plan the computation began in, so one run()
    sees one graph even if the document is synced under it; but a read made once the node's raw key
    under the current plan differs from the one it began under, or once the graph is halted,
    raises Cancelled, so a run of many reads, a composite over the clip, dies at its next read
    rather than finishing work nothing will take."""

    def __init__(self, graph, plan, nid, sources, key, types=None):
        self._graph, self._plan, self._nid, self._sources = graph, plan, nid, sources
        self._raw_key, self._types = plan[nid].raw_key, types or {}
        self.key, self.fps, self.count = key, graph.fps, graph.count

    def type(self, input=INPUT):
        return self._types.get(input)

    def __call__(self, row, input=INPUT):
        g = self._graph
        now = g._plan.get(self._nid)
        if g.halt or now is None or now.raw_key != self._raw_key:
            raise Cancelled(f"{self._nid} at row {row}: the graph moved on")
        try:
            return g._compute(self._plan, self._sources[input], row, reader=self._nid)
        except Exception as exc:
            if not hasattr(exc, "sieve_node"):
                exc.sieve_node = self._sources[input]     # a read that fails is the read node's, never the reader's
            raise


class Series:
    """What a series tool's run() gets: data is (T, ...), the read node stacked over the window, each
    row through the tool's fold() first when it has one; or, for a series node reading another, what
    `gated` fed from the upstream result: its (T,) signal, or its rows, under the band."""

    def __init__(self, data, key, start, fps):
        self.data, self.key, self.start, self.fps = data, key, start, fps


class Readers:
    """The readers open on served bakes, one per key, opened on the worker at the first read and
    kept while a node serves the key. `keep()` retires the rest at sync and `reap()` closes them on
    the worker between computations, since a close from the GUI thread would pull a file from under
    a read in flight; `release()` closes one so its file can be replaced or removed, which on
    Windows a file open in cv2 refuses."""

    def __init__(self, open_bake):
        self._open, self._held, self._retired = open_bake, {}, []
        self._lock = threading.Lock()

    def get(self, bake, cache_bytes):
        """The reader on `bake`, opened here when none is: IOError when it cannot be. Worker threads only."""
        with self._lock:
            r = self._held.get(bake.key)
        if r is None:
            if self._open is None:
                raise IOError("no store to read the bake from")
            r = self._open(bake, cache_bytes)
            with self._lock:
                self._held[bake.key] = r
        return r

    def held(self, key):
        """The reader open on `key`, or None; never opens one. GUI-safe."""
        with self._lock:
            return self._held.get(key)

    def keep(self, keys):
        with self._lock:
            self._retired += [self._held.pop(k) for k in list(self._held) if k not in keys]

    def decoders(self):
        """The Decoder of each reader held that reads a clip. GUI-safe."""
        with self._lock:
            return [d for r in self._held.values() if (d := getattr(r, "decoder", None)) is not None]

    def reap(self):
        """Closes the retired readers; the worker's alone, between computations, since a close under a read in flight pulls the file from it."""
        assert threading.current_thread().name == "worker", "Readers.reap off the worker thread"
        with self._lock:
            gone, self._retired = self._retired, []
        for r in gone:
            r.close()

    def release(self, key):
        with self._lock:
            r = self._held.pop(key, None)
        if r is not None:
            r.close()

    def close(self):
        """Closes every reader, held or retired: for the owner once the worker has stopped."""
        with self._lock:
            gone, self._held, self._retired = [*self._retired, *self._held.values()], {}, []
        for r in gone:
            r.close()


class Graph:
    def __init__(self, doc, decoder, tools, memo_bytes=4 << 30, open_bake=None, stream=None):
        """`open_bake(bake, cache_bytes)` opens a served node's file as a reader, or raises IOError;
        without it a served node's read raises. Whether the file is there is asked where the document
        opens, Store.missing, not here. `stream` is the Emitter it emits through, one of its own when
        none is handed."""
        self.doc, self.decoder = doc, decoder
        self.tools = tools if hasattr(tools, "get") else {t.NAME: t for t in tools}
        self.readers = Readers(open_bake)
        self._rows = None                   # (count, fps) of the file the document is in the row space of; None for the plate's
        self.axis = None                    # the served node whose file that is
        self.off, self.plate = set(), None  # nodes in the other row space; the axis's Plate, for a csv's key line
        self.stale = set()                  # served nodes whose live key is not the one they were baked under; the plan's verdict, shown and never saved
        self.memo = Memo(memo_bytes)
        self._lock = threading.Lock()
        self.halt = False                   # set by whoever is stopping the worker: every Frames read from then on raises Cancelled
        self.stream = stream or Emitter()
        self._base = None                   # the video node's key: the file and what the decoder hands out; set at sync()
        self._hits = {}                     # lane -> {node: [results the memo held, folds it held]} since that lane's last progress
        # The stores report what they discard into the same stream: the memo's entry by its key and row,
        # the decoder cache's frame by its row under the video's key, a served reader's under the served node's.
        self.memo.on_evict = lambda k, n: self.stream.emit("evict", None, k[1], k[0], n)
        decoder.on_evict = lambda row, n: self.stream.emit("uncache", None, row, self._base, n)
        self._plan = {}
        self._notes = {}                    # node -> (its key, what the run said): a tool raising, a chain node fed no signal
        self.shown = self.over = self.series = None
        self.chain, self.heads, self.unrun_series = [], [], []
        self.sync()

    @property
    def count(self):
        """The document's rows: the served file's while the display is behind an unaligned bake,
        else the decoder's, read live, since a container's header may claim rows the stream lacks
        and the decoder corrects itself at the first read past the end."""
        return self._rows[0] if self._rows else self.decoder.count

    @property
    def fps(self):
        return self._rows[1] if self._rows else self.decoder.fps

    def sync(self):
        """Re-read the document: the plan, pure in the document and the tools (see `plan`), and the
        decoder's output, which the video node's param sets."""
        output = video_output(self.doc)
        self.decoder.output = output        # a change empties its cache; a read in flight under the old plan is cancelled
        self._base = base_key(self.decoder.path, output)
        p = plan(self.doc, self.tools, self._base)
        self.readers.keep({e.bake.key for e in p.entries.values() if e.bake is not None})
        with self._lock:
            self._rows, self.axis = p.rows, p.axis
            self.plate = None if p.axis is None else p.entries[p.axis].bake.plate
            self.off, self.stale = {nid for nid, e in p.entries.items() if e.off}, set(p.stale)
            self._plan = p.entries
            self.shown, self.over = p.shown, p.over
            self.series = p.chain[0] if p.chain else None
            self.heads, self.chain, self.unrun_series = p.heads, p.chain, p.unrun
        self.memo.unpin({e.raw_key for e in p.entries.values() if e.static})
        if self.stream.on_event is not None:    # a boundary in the stream: what runs next ran under a new plan, which it carries
            self.stream.sync({nid: e.key for nid, e in p.entries.items()}, facts(p, self.doc.pinned))

    def empty(self):
        """Empties the memo, the decoder's cache and every open reader's, so the next walk runs
        every row; no discard is emitted for them, so the ledger takes none of it for a
        recomputation. Any thread; a row in flight may land in a store after it."""
        self.memo.empty()
        self.decoder.empty()
        for d in self.readers.decoders():
            d.empty()

    def _reader(self, nid, e):
        """The reader on `nid`'s bake; a file that cannot be read is the node's to say, in its standing."""
        try:
            r = self.readers.get(e.bake, self.decoder.cache_limit)
        except OSError as exc:
            exc.sieve_node = nid
            self.note(nid, str(exc))
            raise
        d = getattr(r, "decoder", None)
        if d is not None and d.on_evict is None:
            key = e.raw_key
            d.on_evict = lambda row, n: self.stream.emit("uncache", None, row, key, n)
        return r

    def baked_series(self, nid):
        """A served series node's whole file: its tables one a row, or its float32 signal. Worker threads only."""
        with self._lock:
            e = self._plan.get(nid)
        return self._reader(nid, e).data

    def close(self):
        self.readers.close()

    def standing(self, nid):
        """One line on why `nid` does not run, else what its run said under its current key, else
        "". The plan's reasons: an input unwired, mismatched or waiting on an unfed node, a series
        node off the chain, a cycle. The notes: a tool raising, a chain node fed no signal."""
        with self._lock:
            e = self._plan.get(nid)
            note = self._notes.get(nid)
        if e is None:
            return ""
        if e.standing:
            return e.standing
        return note[1] if note is not None and note[0] == e.key else ""

    def note(self, nid, text):
        """What `nid`'s run said, kept under its current key so a change to the node drops it;
        "" clears. The worker and the display write it; the window reads it through `standing`."""
        with self._lock:
            e = self._plan.get(nid)
            if text and e is not None:
                self._notes[nid] = (e.key, text)
            else:
                self._notes.pop(nid, None)

    # -- what the worker and the display ask -------------------------------
    def _walk(self):
        return walked(self._plan, self.chain, self.shown)

    @property
    def walk(self):
        """The node the worker computes over the window: what the series node reads, else what is
        shown. None when the series node is not fed, so its tool never sees a type it does not expect."""
        with self._lock:
            return self._walk()

    def _fold(self):
        return shared_fold(self._plan, self.heads)

    @property
    def fold(self):
        """The fold the walk stacks rows through: the heads' when every one of them has the same,
        None when they differ or none has one, so that the stack holds the rows as they are."""
        with self._lock:
            return self._fold()

    def walk_row(self, row):
        """The walked node at `row` as the worker stacks it: through the heads' shared fold() when
        they have one, so what the window holds is what the series tools asked for and never the
        frame. Worker threads only."""
        with self._lock:
            plan, nid, fold = self._plan, self._walk(), self._fold()
        with self.demand("walk", nid):
            out = self._compute(plan, nid, row)
        return out if fold is None or out is None else fold(out)

    def frame_nodes(self):
        """Every fed frame node, in document order: what the walk computes at each row beside the
        walked node, so every node's plane can be counted over the window, a branch's too."""
        with self._lock:
            return [nid for nid, e in self._plan.items() if e.kind == "frame" and e.fed]

    @property
    def series_tool(self):
        with self._lock:
            return self._plan[self.series].tool if self.series else None

    def series_params(self):
        with self._lock:
            return dict(self._plan[self.series].params) if self.series else {}

    def series_chain(self):
        """[(node, tool, params, band, the node it reads)] in run order: the heads first, then each
        series node on from a chain node. The worker feeds each head the stack and the rest what
        `gated` fed from the upstream result under its band, its signal or its rows."""
        with self._lock:
            return [(nid, self._plan[nid].tool, dict(self._plan[nid].params), self._plan[nid].band, self._plan[nid].src)
                    for nid in self.chain]

    def key(self, nid):
        with self._lock:
            return self._plan[nid].key

    def entry(self, nid):
        """The plan's Entry for `nid`, or None; built at sync and never touched after, so safe to hold."""
        with self._lock:
            return self._plan.get(nid)

    def source(self, nid):
        """The node `nid`'s first input reads, or None."""
        with self._lock:
            e = self._plan.get(nid)
        return None if e is None else e.src

    def fed(self, nid):
        """Whether the video reaches `nid` through wires whose types fit; None does not."""
        with self._lock:
            e = self._plan.get(nid)
        return e is not None and e.fed

    def compute(self, nid, row, raw=False, demand="display"):
        """Output of `nid` at `row`, memoized; None for a node nothing reaches. Worker threads only.
        The whole recursion runs in the plan current at the call, so what lands in the memo under a
        key was computed from the graph that key describes. `raw` is the plane before the node's band,
        what its density counts, so the axis holds while a handle moves. `demand` is what the caller
        answers, the display unless it says "bake"."""
        with self._lock:
            plan = self._plan
        with self.demand(demand, nid):
            return self._compute(plan, nid, row, raw)

    def progress(self, done, length, stack=None):
        """The walk's progress, `done` rows of `length`, as an event; whoever drives the walk, the
        worker or bench.py, says so as each row lands, and a reader takes the rate from the stream.
        Its facts are what emits no event of its own: "hits" and "fold_hits", per node the results and
        the folds the memo held for this thread's lane since the lane's last progress, and "memo" and
        "caches", each store's bytes, limit, hits, misses and discards now, a cache under the key its
        discards carry, and "stack", the bytes the lane's walk holds and their limit, when `stack` gives
        the two. A lane that reports no progress keeps its count."""
        if self.stream.on_event is None:
            return
        hits = self._hits.pop(self.stream.lane, {})
        with self._lock:
            plan = self._plan
        m = self.memo
        caches = {self._base: self.decoder}
        for e in plan.values():
            if e.bake is not None and (d := getattr(self.readers.held(e.bake.key), "decoder", None)) is not None:
                caches[e.raw_key] = d
        self.stream.emit("progress", None, done, None, 0, length=length, facts={
            **({} if stack is None else {"stack": {"bytes": stack[0], "limit": stack[1]}}),
            "hits": {nid: h for nid, (h, _) in hits.items() if h}, "fold_hits": {nid: f for nid, (_, f) in hits.items() if f},
            "memo": {"bytes": m.bytes, "limit": m.limit, "hits": m.hits, "misses": m.misses, "discards": m.evictions},
            "caches": {k: {"bytes": d.cache_bytes, "limit": getattr(d, "cache_limit", None), "hits": d.cache_hits,
                           "misses": d.reads - d.cache_hits, "discards": getattr(d, "evictions", 0)} for k, d in caches.items()}})

    def began(self, start, length):
        """A walk of this thread's lane began, over `length` rows from `start`: a "begin" event with
        the range's first row as its row. Whoever drives the walk says so as it starts or starts over,
        so a reader tells the walk's first row from what the walk before ran after its last. The
        lane's hits not yet reported were the walk before's and are dropped."""
        self._hits.pop(self.stream.lane, None)
        self.stream.emit("begin", None, start, None, 0, length=length)

    def tally(self):
        """What the stores have been asked for and did not hold, as two counts off the counters they
        keep: the memo's misses with the plate decoder's reads its cache did not answer, and the same
        reads of every served reader open now. Taken before and after a computation, either having
        moved says which the computation was; a miss from another thread between the two is counted
        with it, the counters being every thread's, and the second falls when a sync retires a reader."""
        with self._lock:
            plan = self._plan
        d = self.decoder
        served = 0
        for e in plan.values():
            if e.bake is not None and (r := getattr(self.readers.held(e.bake.key), "decoder", None)) is not None:
                served += r.reads - r.cache_hits
        return self.memo.misses + d.reads - d.cache_hits, served

    def _hit(self, nid, fold):
        self._hits.setdefault(self.stream.lane, {}).setdefault(nid, [0, 0])[fold] += 1

    @property
    def on_event(self):
        """The stream's one consumer, the Emitter's; set here or there, it is one."""
        return self.stream.on_event

    @on_event.setter
    def on_event(self, consumer):
        self.stream.on_event = consumer

    def serving(self, what, lane=None):
        """Emitter.serving, said of this graph's stream by the worker."""
        self.stream.serving(what, lane)

    def demand(self, what, nid):
        """Emitter.demand on this graph's stream."""
        return self.stream.demand(what, nid)

    def probe(self, nid, row, key, reader=None):
        """Emitter.probe on this graph's stream, a body raising Cancelled being its "cancel"."""
        return self.stream.probe(nid, row, key, reader, cancel=Cancelled)

    def _compute(self, plan, nid, row, raw=False, reader=None):
        e = plan.get(nid)
        if e is None or e.kind in ("series", "selector") or not e.fed:
            return None
        if e.kind == "video":
            d = self.decoder
            with self.probe(nid, row, e.raw_key, reader) as ev:
                decodes, seeks = d.decodes, d.seeks
                v = d.read(row)
                ev[0] = "seek" if d.seeks != seeks else "decode" if d.decodes != decodes else "cache"
                ev[1], ev[2] = v.nbytes, v.shape
            return v
        if e.bake is not None:
            r = self._reader(nid, e)
            d = getattr(r, "decoder", None)
            with self.probe(nid, row, e.raw_key, reader) as ev:
                decodes, seeks = (d.decodes, d.seeks) if d else (0, 0)
                v = r.read(row)
                ev[0] = "read" if d is None else "seek" if d.seeks != seeks else "decode" if d.decodes != decodes else "cache"
                ev[1], ev[2] = nbytes(v), getattr(v, "shape", None)
            return v if raw or e.band is None else banded(v, e.band)
        mk = (e.raw_key, None if e.static else row)
        v = self.memo.get(mk)
        if v is None:
            with self.probe(nid, row, e.raw_key, reader) as ev:
                try:
                    v = e.tool.run(Frames(self, plan, nid, e.srcs, e.src_key, e.types), row, e.params)
                except Cancelled:
                    raise
                except Exception as exc:
                    if not hasattr(exc, "sieve_node"):
                        exc.sieve_node = nid
                        self.note(nid, f"raised at row {row}: {type(exc).__name__}: {exc}")
                    raise
                size = ev[1] = Memo._size(v)
                ev[2] = getattr(v, "shape", None)
            self.memo.put(mk, v, owner=e.raw_key if e.static else None, size=size)
        elif self.stream.on_event is not None:
            self._hit(nid, 0)
        return v if raw or e.band is None else banded(v, e.band)

    def density(self, nid, row):
        """`nid`'s plane at `row` folded to (BINS,) counts, memoized under its own key and probed on
        the node as a "fold"; None when the output is not a plane. Worker threads only."""
        with self._lock:
            plan = self._plan
        e = plan.get(nid)
        if e is None or e.kind != "frame" or not e.fed:
            return None
        k = (_key(e.raw_key, "fold"), None if e.static else row)
        v = self.memo.get(k)
        if v is None:
            with self.demand("fold", nid):
                plane = self._compute(plan, nid, row, raw=True)
                if not density.is_plane(plane):
                    return None
                with self.probe(nid, row, k[0]) as ev:
                    v = density.fold(plane)
                    ev[0], ev[1], ev[2] = "fold", v.nbytes, plane.shape
            self.memo.put(k, v, owner=e.raw_key if e.static else None)
        elif self.stream.on_event is not None:
            self._hit(nid, 1)
        return v

    def peek(self, row, nid=None):
        """Memo-only read of the shown node, or of `nid`, at `row`; None if it isn't there. GUI-safe."""
        with self._lock:
            e = self._plan.get(self.shown if nid is None else nid)
        if e is None or not e.fed:
            return None
        if e.kind == "video":
            return self.decoder.cached(row)
        if e.bake is not None:
            d = getattr(self.readers.held(e.bake.key), "decoder", None)
            v = None if d is None else d.cached(row)
            return v if v is None or e.band is None else banded(v, e.band)
        v = self.memo.get((e.raw_key, None if e.static else row))
        return v if v is None or e.band is None else banded(v, e.band)


