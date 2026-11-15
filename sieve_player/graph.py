"""The runtime: what the graph says, computed and memoized.

A Graph is built from a document, a decoder and the tools the document's names resolve to. It
snapshots the document on `sync()`, which the window calls after any change, so a worker thread
mid-computation works from one consistent plan and the next computation sees the new one. Params
are read from the document's nodes; the runtime holds none of its own. A node is computed as None
when nothing reaches it: no wire, an unresolved tool, or a wire whose types do not fit.
"""
import os
import threading
from collections import OrderedDict
from contextlib import ExitStack, contextmanager

import numpy as np

from . import density
from .decoder import Decoder, EndOfStream, footage_print
from .document import INPUT, VIDEO_TOOL, video_output
from .plan import _key, base_key, facts, plan
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
    what it was computing is for a plan that is gone, so the read raises instead of serving it.
    The worker drops the row;
    a tool that catches Exception around a read should let this one through."""


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
    """The Decoders open on served files, one per path, opened on the worker at the first read and
    kept while a node serves the path. `keep()` retires the rest at sync and `reap()` closes them on
    the worker between computations, since a close from the GUI thread would pull a file from under
    a read in flight. A file open here cannot be replaced or removed on Windows, so whoever writes
    over one has the node held off (Graph.hold_off) and tries again until the reap has closed it."""

    def __init__(self):
        self._held, self._retired = {}, []
        self._lock = threading.Lock()

    def get(self, path, cache_bytes, output):
        """The Decoder on `path`, opened here when none is, handing out `output`: IOError when it
        cannot be opened. Worker threads only."""
        with self._lock:
            d = self._held.get(path)
        if d is None:
            d = Decoder(path, cache_bytes=cache_bytes)
            d.output = output
            with self._lock:
                self._held[path] = d
        return d

    def held(self, path):
        """The Decoder open on `path`, or None; never opens one. GUI-safe."""
        with self._lock:
            return self._held.get(path)

    def keep(self, paths):
        with self._lock:
            self._retired += [self._held.pop(k) for k in list(self._held) if k not in paths]

    def decoders(self):
        """Every Decoder held. GUI-safe."""
        with self._lock:
            return list(self._held.values())

    def reap(self):
        """Closes the retired readers; the worker's alone, between computations, since a close under a read in flight pulls the file from it."""
        assert threading.current_thread().name == "worker", "Readers.reap off the worker thread"
        with self._lock:
            gone = list(self._retired)
        for r in gone:
            r.close()
        with self._lock:
            self._retired = [r for r in self._retired if all(r is not g for g in gone)]

    def close(self):
        """Closes every reader, held or retired: for the owner once the worker has stopped."""
        with self._lock:
            gone, self._held, self._retired = [*self._retired, *self._held.values()], {}, []
        for r in gone:
            r.close()


class Graph:
    def __init__(self, doc, decoder, tools, memo_bytes=4 << 30, stream=None):
        """`stream` is the Emitter it emits through, one of its own when none is handed."""
        self.doc, self.decoder = doc, decoder
        self.tools = tools if hasattr(tools, "get") else {t.NAME: t for t in tools}
        self.readers = Readers()
        self._lately = []                   # the served files' Decoders in the order they were last read, latest first
        self._prints = {}                   # served path -> (its size and mtime when read, its footage print)
        self.without = set()                # nodes whose file is not to be served: held off by whoever is writing over it, see hold_off()
        self.memo = Memo(memo_bytes)
        self._lock = threading.Lock()
        self.halt = False                   # set by whoever is stopping the worker: every Frames read from then on raises Cancelled
        self.stream = stream or Emitter()
        self._base = None                   # the video node's key: the footage and what the decoder hands out; set at sync()
        self._hits = {}                     # lane -> {node: [results the memo held, folds it held]} since that lane's last progress
        # The stores report what they discard into the same stream: the memo's entry by its key and row,
        # the decoder cache's frame by its row under the video's key, a served reader's under the served node's.
        self.memo.on_evict = lambda k, n: self.stream.emit("evict", None, k[1], k[0], n)
        decoder.on_evict = lambda row, n: self.stream.emit("uncache", None, row, self._base, n)
        self._plan = {}
        self._notes = {}                    # node -> (its key, what the run said): a tool raising, a chain node fed no signal
        self.shown = self.over = self.series = None
        self.chain, self.heads, self.unrun_series = [], [], []
        self._watched = ()                  # what the plot shows, by watch()
        self.sync()

    @property
    def count(self):
        """The document's rows: the decoder's, read live, since a container's header may claim rows
        the stream lacks and the decoder corrects itself at the first read past the end, its own or
        a served file's."""
        return self.decoder.count

    @property
    def fps(self):
        return self.decoder.fps

    def cut_file(self, nid, up):
        """(path, footage print) of the file `nid`'s tool says holds its cut of the footage it
        reads, asked now: `up` is that footage as (path, print), None for the open video. None for
        a node in `without`, a tool that raises or answers with none, and a file that cannot be read."""
        if nid in self.without:
            return None
        node = self.doc.node(nid)
        try:
            path = self.tools[node.tool].cut_file(*(up or (self.decoder.path, self.decoder.footage_print)), node.params)
            if path is None:
                return None
            path = str(path)
            st = os.stat(path)
            if self._prints.get(path, (None,))[0] != (st.st_size, st.st_mtime_ns):
                self._prints[path] = ((st.st_size, st.st_mtime_ns), footage_print(path))
        except Exception:       # a tool's rule is user code; one that fails serves nothing
            return None
        return path, self._prints[path][1]

    def hold_off(self, nid, on):
        """While `on`, `nid` serves no file, so one may be written over what it served; sync() after."""
        (self.without.add if on else self.without.discard)(nid)

    def sync(self):
        """Re-read the document: the plan, pure in the document, the tools and what the cutting
        nodes' tools answer now (see `plan`), and the decoders' output, which the video node's
        param sets."""
        output = video_output(self.doc)
        self.decoder.output = output        # a change empties its cache; a read in flight under the old plan is cancelled
        self._base = base_key(self.decoder.footage_print, output)
        p = plan(self.doc, self.tools, self._base, self.cut_file)
        self.readers.keep({e.file[0] for e in p.entries.values() if e.file is not None})
        for d in self.readers.decoders():
            d.output = output
        with self._lock:
            self._plan, self._whole = p.entries, p
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
        """The Decoder on the file `nid` serves; a file that cannot be read is the node's to say, in its standing."""
        try:
            d = self.readers.get(e.file[0], self.decoder.cache_limit, self.decoder.output)
        except OSError as exc:
            exc.sieve_node = nid
            self.note(nid, str(exc))
            raise
        held = self.readers.decoders()
        self._lately = [d, *(o for o in self._lately if o is not d and any(o is h for h in held))]
        left = self.decoder.cache_limit     # shared by the served files' caches, the one read latest first: it may fill the whole of it
        for o in self._lately:
            if o.cache_limit != left:
                o.cache_limit = left
            left = max(0, left - o.cache_bytes)
        if d.on_evict is None:
            key = e.raw_key
            d.on_evict = lambda row, n: self.stream.emit("uncache", None, row, key, n)
        return d

    def footage(self, nid):
        """The file `nid`'s inputs are frames of: the one the nearest cutting node above it serves,
        else the open video. GUI-safe."""
        with self._lock:
            plan = self._plan
        e = plan.get(nid)
        while e is not None and e.piece is not None:
            e = plan[e.piece]
            if e.file is not None:
                return e.file[0]
        return self.decoder.path

    @contextmanager
    def scrubbing(self):
        """Reads inside land on each open decoder's scrub cursor, the plate's and every served file's."""
        with ExitStack() as stack:
            for d in [self.decoder, *self.readers.decoders()]:
                stack.enter_context(d.scrub())
            yield

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
    def snapshot(self):
        """The Plan of the last sync, whole: built there and never touched after, so what is read
        off one is of one graph whatever syncs meanwhile. Any thread."""
        with self._lock:
            return self._whole

    @property
    def walk(self):
        """The node the worker computes over the window: what the series node reads, else what is
        shown. None when the series node is not fed, so its tool never sees a type it does not expect."""
        return self.snapshot().walk

    @property
    def fold(self):
        """The fold the walk stacks rows through: the heads' when every one of them has the same,
        None when they differ or none has one, so that the stack holds the rows as they are."""
        return self.snapshot().fold

    def walk_row(self, row, p=None):
        """The walked node at `row` as the worker stacks it: through the heads' shared fold() when
        they have one, so what the window holds is what the series tools asked for and never the
        frame; under the Plan `p`, the current one with none. Worker threads only."""
        p = p or self.snapshot()
        nid, fold = p.walk, p.fold
        with self.demand("walk", nid):
            out = self._compute(p.entries, nid, row)
        return out if fold is None or out is None else fold(out)

    def drawing(self):
        """The fed frame nodes whose tool has a draw(), in document order: what the display reads
        at its row beside the shown node, on the walked path or off it."""
        with self._lock:
            return [nid for nid, e in self._plan.items() if e.kind == "frame" and e.fed and hasattr(e.tool, "draw")]

    def watch(self, nodes):
        """`nodes` are what the plot shows, the selection and the pinned; any thread."""
        with self._lock:
            self._watched = tuple(nodes)

    def folded(self):
        """The fed frame nodes among those watch() was told of, in its order: what the window walk
        folds a density for, a branch the walk does not reach among them. Whether a node's output
        is a plane is density()'s to say, at a row."""
        with self._lock:
            return [nid for nid in self._watched if (e := self._plan.get(nid)) is not None and e.kind == "frame" and e.fed]

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
        answers, the display unless it says otherwise."""
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
            if e.file is not None and (d := self.readers.held(e.file[0])) is not None:
                caches[e.raw_key] = d
        self.stream.emit("progress", None, done, None, 0, length=length, facts={
            **({} if stack is None else {"stack": {"bytes": stack[0], "limit": stack[1]}}),
            "hits": {nid: h for nid, (h, _) in hits.items() if h}, "fold_hits": {nid: f for nid, (_, f) in hits.items() if f},
            "memo": {"bytes": m.bytes, "limit": m.limit, "hits": m.hits, "misses": m.misses, "discards": m.evictions},
            "caches": {k: {"bytes": d.cache_bytes, "limit": getattr(d, "cache_limit", None), "hits": d.cache_hits,
                           "misses": d.reads - d.cache_hits, "discards": getattr(d, "evictions", 0)} for k, d in caches.items()}})

    def began(self, start, length, by=None):
        """A walk of this thread's lane began, over `length` rows from `start`: a "begin" event with
        the range's first row as its row and, where `by`, one of stream.BEGUN_BY, says what began
        it, that as its facts' "by". Whoever drives the walk says so as it starts or starts over,
        so a reader tells the walk's first row from what the walk before ran after its last. The
        lane's hits not yet reported were the walk before's and are dropped."""
        self._hits.pop(self.stream.lane, None)
        self.stream.emit("begin", None, start, None, 0, length=length, facts=None if by is None else {"by": by})

    def tally(self):
        """What the stores have been asked for and did not hold, off the counters they keep: the
        memo's misses with the reads no cache answered, the plate decoder's and every open served
        file's. Taken before and after a computation, its having moved says the computation ran; a
        miss from another thread between the two is counted with it, the counters being every
        thread's, and it falls when a sync retires a reader."""
        return self.memo.misses + sum(d.reads - d.cache_hits for d in [self.decoder, *self.readers.decoders()])

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
        if e.file is not None:
            d = self._reader(nid, e)
            with self.probe(nid, row, e.raw_key, reader) as ev:
                decodes, seeks = d.decodes, d.seeks
                try:
                    v = d.read(row)
                except EndOfStream:
                    # the file is the plate cut, row for row: where it ends the plate's stream does, which nothing may have read that far to find
                    self.decoder.ends_at(d.count)
                    raise
                ev[0] = "seek" if d.seeks != seeks else "decode" if d.decodes != decodes else "cache"
                ev[1], ev[2] = v.nbytes, v.shape
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
        if e.file is not None:
            d = self.readers.held(e.file[0])
            v = None if d is None else d.cached(row)
            return v if v is None or e.band is None else banded(v, e.band)
        v = self.memo.get((e.raw_key, None if e.static else row))
        return v if v is None or e.band is None else banded(v, e.band)


