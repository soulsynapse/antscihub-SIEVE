"""The runtime: what the graph says, computed and memoized.

A Graph is built from a document, a decoder and the tools the document's names resolve to. It
snapshots the document on `sync()`, which the window calls after any change, so a worker thread
mid-computation works from one consistent plan and the next computation sees the new one. Params
are read from the document's nodes; the runtime holds none of its own. A node is computed as None
when nothing reaches it: no wire, an unresolved tool, or a wire whose types do not fit.
"""
import threading
from collections import OrderedDict
from contextlib import ExitStack, contextmanager
from typing import NamedTuple

import numpy as np

from . import density
from .cut import computed_in
from .cut import read as read_of_cut
from .decoder import CLEAR, Decoder, EndOfStream, footage_print_by_stamp, letting_go
from .document import INPUT, VIDEO_TOOL, video_output
from .registry import by_name, computed, names_cut_files, reach_of
from .plan import _key, base_key, facts, plan
from .stream import Emitter
from .wire import ROWS, is_table, nbytes, own_bytes

NEAR = 8    # rows about the row a walk under way is at that the stores let go of last of all: what a tool reading beside its row reads


def inband(v, band):
    """Where `v` lies between the band's lo and hi; outside them once lo is above hi, the band
    inside out, as the handles are read in both domains."""
    lo, hi = band
    return (v >= lo) & (v <= hi) if lo <= hi else (v >= lo) | (v <= hi)


def banded(v, band):
    """`v` with every value outside `band` set to zero, inside it when lo is above hi. Only a plane
    of values is banded; a mask, a field or None passes through. The plane handed back is read-only."""
    if not isinstance(v, np.ndarray) or v.ndim != 2 or v.dtype == bool:
        return v
    out = np.where(inband(v, band), v, np.zeros((), v.dtype))
    out.setflags(write=False)
    return out


def kept(signal, band):
    """The rows of `signal` that `band` keeps, every row with None; a NaN, a row absent, is kept by none."""
    s = np.asarray(signal)
    present = ~np.isnan(s) if s.dtype.kind == "f" else np.ones(len(s), bool)
    return present if band is None else present & inband(s, band)


def absent_dtype(signal):
    """The dtype a signal is handed downstream in, one that holds NaN."""
    return signal.dtype if signal.dtype.kind == "f" else np.dtype(np.float64)


def gated(result, band, type):
    """A series node's result as the player hands it out, the node producing `type`: the tool's dict
    with "gate", the rows its signal keeps under the node's band, and `fed`, what a series node
    downstream reads, every gated-out row absent: where the type is a table, the result's tables,
    one a row, None at a gated-out row; else the signal as a masked array, a gated-out row masked
    and NaN beneath, so a tool that drops the mask reads NaN there and never a zero. A result
    without a signal passes through ungated, and feeds nothing."""
    if not isinstance(result, dict) or "signal" not in result:
        return result, None
    signal = np.asarray(result["signal"])
    gate = kept(signal, band)
    if is_table(type):
        fed = np.empty(len(result[ROWS]), object)
        fed[:] = result[ROWS]
        fed[~gate] = None
        return {**result, "gate": gate}, fed
    return {**result, "gate": gate}, np.ma.MaskedArray(np.where(gate, signal, np.nan).astype(absent_dtype(signal)), mask=~gate)


class Ref(NamedTuple):
    """What the memo holds for a result that is another store's array: the key that store holds it
    under, its row there, None for a static node's, and, in the memo, what it read of its cut."""
    key: str
    row: int | None
    read: tuple = (None, None)


def _address(e, row, cut=None):
    """(the cut `e`'s value at `row` is computed in, by cut.computed_in, `cut` its reader's; the
    memo key the value is held under): its raw key, its row, None for a static node's, and what it
    read of that cut, by cut.read, a static node reading its whole extent."""
    c = computed_in(e.cuts, cut, row)
    rows = None if c is None else c.extent.rows
    if e.static:
        return c, (e.raw_key, None, read_of_cut(rows, (None, None), 0))
    return c, (e.raw_key, row, read_of_cut(rows, e.reach, row))


def _same(v, a):
    """Whether `v` is the array `a`, whole: one buffer read one way, whether or not one object."""
    return v is a or (v.shape == a.shape and v.strides == a.strides and v.dtype == a.dtype
                      and v.__array_interface__["data"][0] == a.__array_interface__["data"][0])


def to_hold(v, handed, pinned):
    """What the memo holds for a run's result `v`, `handed` being [(array, Ref)] of the stores'
    arrays the run read: the Ref where `v` is one of them, whole, and is not to be pinned; a copy
    where it is one to be pinned, shares memory with one, or is part of a larger array; else `v`.
    An array is handed back read-only."""
    if not isinstance(v, np.ndarray):
        return v
    ref = next((r for a, r in handed if _same(v, a)), None)
    if ref is not None and not pinned:
        return ref
    owner = v
    while isinstance(owner, np.ndarray) and owner.base is not None:
        owner = owner.base
    if (ref is not None or not isinstance(owner, np.ndarray) or owner.nbytes != v.nbytes
            or any(np.may_share_memory(v, a) for a, _ in handed)):
        v = v.copy()
    v.setflags(write=False)
    return v


class Memo:
    """LRU bounded by bytes, each entry's as it was put with. Image-shaped entries (ndim >= 2) are
    evicted before small ones. An entry put with an owner is pinned: never evicted, counted toward
    the limit, and gone only through `unpin`, which drops every pinned entry whose owner is not in
    `keep`, so whatever a STATIC node has memoized under any key outlives any walk and goes with
    its plan. Each eviction goes to `on_evict(key, bytes)` when set, after the lock is dropped.
    With `order` set it keeps some image-shaped entries back: `order()` is asked once the memo is
    past its limit, under the memo's lock, for a function of a key, None for an entry that goes as
    any does and a rank for one kept back, and they go as decoder.letting_go says, those kept back
    only when no other is left and then until CLEAR of the limit is clear."""

    def __init__(self, limit_bytes):
        self.limit = limit_bytes
        self.order = None
        self.bytes = 0
        self._big, self._small, self._pinned = OrderedDict(), OrderedDict(), {}     # pinned: key -> (owner, value)
        self._sizes = {}        # key -> the bytes its entry was put with
        self._lock = threading.Lock()
        self.hits = self.misses = self.evictions = 0
        self.on_evict = None

    def get(self, k, count=True):
        """The entry under `k`, or None; a hit or a miss is counted unless `count` is False, for a
        caller that says by `counted` whether the read was answered."""
        with self._lock:
            if k in self._pinned:
                self.hits += count
                return self._pinned[k][1]
            for d in (self._big, self._small):
                v = d.get(k)
                if v is not None:
                    d.move_to_end(k)
                    self.hits += count
                    return v
            self.misses += count
            return None

    def counted(self, hit):
        with self._lock:
            if hit:
                self.hits += 1
            else:
                self.misses += 1

    def empty(self):
        """Drops every entry, pinned ones with the rest, and tells `on_evict` of none: what is
        emptied on purpose was not discarded for room."""
        with self._lock:
            self._big.clear()
            self._small.clear()
            self._pinned.clear()
            self._sizes.clear()
            self.bytes = 0

    def unpin(self, keep):
        gone = []
        with self._lock:
            for k in [k for k, (owner, _) in self._pinned.items() if owner not in keep]:
                del self._pinned[k]
                n = self._sizes.pop(k)
                self.bytes -= n
                gone.append((k, n))
        if self.on_evict is not None:
            for ok, n in gone:
                self.on_evict(ok, n)

    def put(self, k, v, owner=None, size=None):
        """`v` under `k`, pinned to `owner` when one is given; a key already held is left as it is.
        `size` is the bytes `v` holds as wire.nbytes counts a row of its type, its own with none."""
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
            self._sizes[k] = own_bytes(v) if size is None else size
            self.bytes += self._sizes[k]
            if self.bytes > self.limit and self.order is not None:
                for ok in letting_go(self._big, self.order(), lambda: self.bytes > self.limit,
                                     lambda: self.bytes > self.limit - self.limit // CLEAR):
                    del self._big[ok]
                    n = self._sizes.pop(ok)
                    self.bytes -= n
                    self.evictions += 1
                    gone.append((ok, n))
            while self.bytes > self.limit:
                src = self._big or self._small
                if not src:
                    break
                ok, _ = src.popitem(last=False)
                n = self._sizes.pop(ok)
                self.bytes -= n
                self.evictions += 1
                gone.append((ok, n))
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
    at row r, read-only, and frames(r, name) that of another of its INPUTS; frames.type(name) is what the node
    wired into that input produces, for a tool whose EXPECTS admits types its run() must tell
    apart. `key` changes whenever anything upstream of any input does, and `cut` is the record of the cut
    the node runs in: of its inputs' cuts, the one `cut`, the cut its value is computed in, is or was made
    from; with none, their one, or None for several. Each read is of the input in that cut, and a read at a row
    outside the cut's rows or before the footage's first is None, absent as no row is; `rows` is
    (first, the row past the last) of the cut's rows, (0, count) for the whole footage, and `count`
    the footage's rows whatever the cut. It reads through the plan the computation began in, so one run()
    sees one graph even if the document is synced under it; but a read made once the node's raw key
    under the current plan differs from the one it began under, or once the graph is halted,
    raises Cancelled, so a run of many reads, a composite over the clip, dies at its next read
    rather than finishing work nothing will take. Made with the `row` its run is asked at, a read of
    a row outside what the tool's `reach_in_rows` says raises ValueError."""

    def __init__(self, graph, plan, nid, sources, key, types=None, row=None, cut=None):
        self._graph, self._plan, self._nid, self._sources, self._in = graph, plan, nid, sources, cut
        before, after = reach_of(plan[nid].tool, plan[nid].computed)
        self._reads = None if row is None else (None if before is None else row - before, None if after is None else row + after)
        self._raw_key, self._types = plan[nid].raw_key, types or {}
        self.key, self.fps, self.count = key, graph.fps, graph.count
        reads = plan[nid].reads
        self.cut = computed_in(reads, cut, row) if cut is not None else reads[0] if len(reads) == 1 else None
        self._within = None if self.cut is None else self.cut.extent.rows
        self.rows = self._within or (0, self.count)
        self.handed = []        # [(array, Ref)]: each array a read handed the run that a store holds, and where

    def named(self, ref, default=None):
        """The array handed under `ref`, or `default` where the run read none there."""
        return next((a for a, r in self.handed if r == ref), default)

    def type(self, input=INPUT):
        return self._types.get(input)

    def __call__(self, row, input=INPUT):
        g = self._graph
        now = g._plan.get(self._nid)
        if g.halt or now is None or now.raw_key != self._raw_key:
            raise Cancelled(f"{self._nid} at row {row}: the graph moved on")
        if self._reads is not None and ((self._reads[0] is not None and row < self._reads[0]) or (self._reads[1] is not None and row > self._reads[1])):
            raise ValueError(f"read row {row}, outside the rows its tool's reach_in_rows says it reads")
        if row < 0 or (self._within is not None and not self._within[0] <= row < self._within[1]):
            return None
        src = self._sources[input]
        try:
            v = g._compute(self._plan, src, row, raw=True, reader=self._nid, cut=self._in)
        except Exception as exc:
            if not hasattr(exc, "sieve_node"):
                exc.sieve_node = src     # a read that fails is the read node's, never the reader's
            raise
        e = self._plan.get(src)
        out = v if e is None or e.band is None else banded(v, e.band)
        if out is v and isinstance(v, np.ndarray):
            memoized = e.kind == "frame" and e.file is None
            self.handed.append((v, Ref(*_address(e, row, self._in)[1]) if memoized else Ref(e.raw_key, row)))
        return out


class Series:
    """What a series tool's run() gets: data is (T, ...), the read node stacked over the window, each
    row through the tool's fold() first when it has one; or, for a series node reading another, what
    `gated` fed from the upstream result: its (T,) signal, or its rows, under the band. `cut` is the
    record of the cut the node runs in, None where whoever made the series said none."""

    def __init__(self, data, key, start, fps, cut=None):
        self.data, self.key, self.start, self.fps, self.cut = data, key, start, fps, cut


class Readers:
    """The Decoders open on served files, one per path, opened on the worker at the first read and
    kept while a node serves the path. `keep()` retires the rest at sync and `reap()` closes them on
    the worker between computations, since a close from the GUI thread would pull a file from under
    a read in flight. A file open here cannot be replaced or removed on Windows, so a tool never
    writes over a file its cut_file has answered with."""

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

    def open_paths(self):
        """Every path a Decoder here has open, held or retired and not yet reaped. GUI-safe."""
        with self._lock:
            return {*self._held, *(r.path for r in self._retired)}

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
    def __init__(self, doc, decoder, tools, memo_bytes=4 << 30, stream=None, cut_result=None, keeper=None):
        """`stream` is the Emitter it emits through, one of its own when none is handed;
        `cut_result` is what `plan` is handed under that name at every sync, asked on the thread
        that syncs. `keeper`, a result_keeper.Keeper, is asked a frame node's row on a memo miss
        before its tool runs and told each row a tool made; one thread computes on a Graph with one."""
        self.doc, self.decoder, self.cut_result, self.keeper = doc, decoder, cut_result, keeper
        self.tools = by_name(tools)
        self.readers = Readers()
        self._lately = []                   # the served files' Decoders in the order they were last read, latest first
        self._in_use = set()                # the files the cutting nodes' tools named at the last sync, see cut_files_named
        self._failing, self._failed = {}, {}    # node -> what its tool's cut_file or cut_files raised: at the sync under way, and at the last
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
        self._held_rows = (0, 0)            # (start, rows) the stores let go of last, by holds()
        self._shown_at = None               # the row the display is at, by looks_at()
        self._walks_at = {}                 # lane -> the row its walk is at, by walk_row() until rests(); the worker's thread's, replaced whole and never changed
        self.memo.order = self._memo_order
        decoder.order = self._row_order
        self._plan = {}
        self._notes = {}                    # node -> (its key, what the run said): a tool raising, a chain node fed no signal
        self.shown = self.over = self.series = None
        self.chain, self.heads, self.unrun_series = [], [], []
        self._watched = ()                  # what the plot shows, by watch()
        self._painted = ()                  # the nodes whose draw() the display paints, by paints()
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
        reads, asked now: `up` is that footage as (path, print), None for the open video. A str,
        what was said, where the tool raises FileNotFoundError or the file it names is gone: the
        node is to serve a file and has none, and `plan` does not run it. None for a tool that
        raises anything else or answers with none, and a file that cannot be read."""
        node = self.doc.node(nid)
        tool, of = self.tools[node.tool], up or (self.decoder.path, self.decoder.footage_print)
        try:
            path = tool.cut_file(*of, computed(tool, node.params))
            return None if path is None else (str(path), footage_print_by_stamp(path))
        except FileNotFoundError as exc:
            return str(exc)
        except Exception as exc:       # a tool's rule is user code; one that fails serves nothing, and the node's standing says so
            self._failing[nid] = f"cut_file raised: {type(exc).__name__}: {exc}"
            return None

    def _named(self, entries):
        """Every file a node of `entries` whose tool has the cut_files facet names of the footage
        it reads, whether or not the plan would serve one there; a tool that raises names none."""
        out = set()
        for nid, e in entries.items():
            if names_cut_files(e.tool):
                try:
                    out |= {str(p) for p in e.tool.cut_files(*self._footage(entries, nid), e.computed)}
                except Exception as exc:
                    self._failing.setdefault(nid, f"cut_files raised: {type(exc).__name__}: {exc}")
        return out

    def cut_files_named(self):
        """Every file a cutting node of the last sync's plan would serve under some choice of its
        params were it served, as its tool's cut_files answered of the footage `footage` says it
        reads. The thread that syncs."""
        return set(self._in_use)

    def cut_files_in_use(self):
        """`cut_files_named` and every served file still open here. The thread that syncs."""
        return self._in_use | self.readers.open_paths()

    def sync(self):
        """Re-read the document: the plan, pure in the document, the tools, the decoder's count and
        what the cutting nodes' tools answer now (see `plan`), and the decoders' output, which the
        video node's param sets. A count lowered since is the caller's to sync again for."""
        output = video_output(self.doc)
        self.decoder.output = output        # a change empties its cache; a read in flight under the old plan is cancelled
        self._base = base_key(self.decoder.footage_print, output)
        self._failing = {}
        p = plan(self.doc, self.tools, self._base, self.cut_file, self.cut_result, footage=self.decoder.footage_print, count=self.decoder.count)
        self._in_use = self._named(p.entries)
        self.readers.keep({e.file[0] for e in p.entries.values() if e.file is not None})
        for d in self.readers.decoders():
            d.output = output
        with self._lock:
            self._plan, self._whole, self._failed = p.entries, p, self._failing
            self._files = {e.raw_key: e.file[0] for e in p.entries.values() if e.file is not None}
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
            d.order = self._row_order
        return d

    def holds(self, start, rows):
        """The `rows` rows from `start` are what the stores let go of last: the window's. Any thread."""
        self._held_rows = (start, rows)

    def looks_at(self, row):
        """The display is at `row`. Any thread."""
        self._shown_at = row

    def rests(self):
        """This thread's lane's walk is at no row: it finished, was stopped, or begins again. Worker threads only."""
        self._walks_at = {lane: row for lane, row in self._walks_at.items() if lane != self.stream.lane}

    def _row_order(self):
        """A store's order of its rows, as Memo.order: None for a row outside holds() and more than
        NEAR rows from every lane's walk, and for one kept back (where, how far), where 0 within
        NEAR rows of a walk and 1 inside holds(), the higher going first, and of two alike the one
        further from every row something is at, the display's and each walk's."""
        (start, rows), shown, walks = self._held_rows, self._shown_at, tuple(self._walks_at.values())
        end, every = start + rows, walks if shown is None else (*walks, shown)

        def order(row):
            near = any(abs(row - a) <= NEAR for a in walks)
            if not near and not start <= row < end:
                return None
            return (0 if near else 1, min([abs(row - a) for a in every], default=0))
        return order

    def _memo_order(self):
        """`_row_order` of a memo key's row, None too for an entry under a key no node of the plan
        has, and inside holds() a node the display does not read going before one it does: the
        shown node, the overlay's and those whose draw() it paints."""
        rows, plan = self._row_order(), self._plan
        live = {e.raw_key for e in plan.values()}
        read = {plan[nid].raw_key for nid in (self.shown, self.over, *self._painted) if nid in plan}

        def order(k):
            if k[0] not in live:
                return None
            if k[1] is None:
                return (1, k[0] not in read, 0)
            where = rows(k[1])
            return where and (where[0], where[0] == 1 and k[0] not in read, where[1])
        return order

    def footage(self, nid):
        """The file `nid`'s inputs are frames of: the one the nearest cutting node above it serves,
        else the open video. GUI-safe."""
        with self._lock:
            plan = self._plan
        return self._footage(plan, nid)[0]

    def _footage(self, entries, nid):
        """`footage` under the plan's `entries`, as (path, footage print)."""
        e = entries.get(nid)
        served = next((f for r in (() if e is None else e.reads) if (f := r.served()) is not None), None)
        return served or (self.decoder.path, self.decoder.footage_print)

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
        """One line on why `nid` does not run, else what its tool raised when the last sync asked
        it for its cut files, else what its run said under its current key, else "". The plan's
        reasons: an input unwired, mismatched or waiting on an unfed node, a file it is to serve
        and has not, a series node off the chain, a cycle. The notes: a tool raising, a chain node fed no signal."""
        with self._lock:
            e = self._plan.get(nid)
            note = self._notes.get(nid)
            failed = self._failed.get(nid)
        if e is None:
            return ""
        if e.standing or failed:
            return e.standing or failed
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

    def walk_row(self, row, p=None, cut=None, nid=None):
        """The walked node `nid`, the plan's first with none, at `row` as the worker stacks it:
        through its heads' shared fold() when they have one, so what the window holds is what the
        series tools asked for and never the frame; under the Plan `p`, the current one with none,
        and computed in `cut`, as compute's. Worker threads only."""
        p = p or self.snapshot()
        nid = p.walk if nid is None else nid
        fold = p.fold_for(nid)
        self._walks_at = {**self._walks_at, self.stream.lane: row}
        with self.demand("walk", nid):
            out = self._compute(p.entries, nid, row, cut=cut)
        return out if fold is None or out is None else fold(out)

    def drawing(self, p=None):
        """The fed frame nodes among those paints() was told of, in its order: what the display
        reads at its row beside the shown node, on the walked path or off it; under the Plan `p`,
        the current one with none."""
        entries = (p or self.snapshot()).entries
        with self._lock:
            painted = self._painted
        return [nid for nid in painted if (e := entries.get(nid)) is not None and e.kind == "frame" and e.fed]

    def paints(self, nodes):
        """`nodes` are those whose draw() the display paints; any thread."""
        with self._lock:
            self._painted = tuple(nodes)

    def watch(self, nodes):
        """`nodes` are what the plot shows, the selection and the pinned; any thread."""
        with self._lock:
            self._watched = tuple(nodes)

    def folded(self, p=None):
        """The fed frame nodes among those watch() was told of, in its order: what the window walk
        folds a density for, a branch the walk does not reach among them; under the Plan `p`, the
        current one with none. Whether a node's output is a plane is density()'s to say, at a row."""
        entries = (p or self.snapshot()).entries
        with self._lock:
            watched = self._watched
        return [nid for nid in watched if (e := entries.get(nid)) is not None and e.kind == "frame" and e.fed]

    @property
    def series_tool(self):
        with self._lock:
            return self._plan[self.series].tool if self.series else None

    def series_params(self):
        with self._lock:
            return dict(self._plan[self.series].params) if self.series else {}

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

    def compute(self, nid, row, raw=False, demand="display", p=None, cut=None):
        """Output of `nid` at `row`, memoized; None for a node nothing reaches, and at a row outside
        the cut it is computed in, absent there as no row is. Worker threads only.
        The whole recursion runs in the Plan `p`, the one current at the call with none, so what
        lands in the memo under a key was computed from the graph that key describes. `raw` is the
        plane before the node's band, what its density counts, so the axis holds while a handle
        moves. `demand` is what the caller answers, the display unless it says otherwise. `cut` is the
        cut of the node's that the value is computed in, by cut.computed_in, the one holding `row` with none."""
        plan = (p or self.snapshot()).entries
        with self.demand(demand, nid):
            return self._compute(plan, nid, row, raw, cut=cut)

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

    def _held(self, v):
        """`v`, or the array the store a Ref names holds, through as many Refs as lie between;
        None where that store has let it go. Never computes. GUI-safe."""
        with self._lock:
            files = self._files
        while isinstance(v, Ref):
            if v.key == self._base:
                return self.decoder.cached(v.row)
            if v.key in files:
                d = self.readers.held(files[v.key])
                return None if d is None else d.cached(v.row)
            v = self.memo.get((v.key, v.row, v.read), count=False)
        return v

    def _memoized(self, mk):
        """(the memo's entry under `mk`, the array it stands for): one hit where there is an array,
        one miss where there is none, a reference whose store let the array go among them."""
        got = self.memo.get(mk, count=False)
        v = self._held(got)
        self.memo.counted(v is not None)
        return got, v

    def _compute(self, plan, nid, row, raw=False, reader=None, cut=None):
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
            v.setflags(write=False)
            return v
        c, mk = _address(e, row, cut)
        if c is None or not c.extent.holds(row):
            return None
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
            v.setflags(write=False)
            return v if raw or e.band is None else banded(v, e.band)
        got, v = self._memoized(mk)
        if v is None and got is None and self.keeper is not None and (v := self.keeper.ask(e, row, c)) is not None:
            self.memo.put(mk, v, size=nbytes(e.produces, v))
        if v is None:
            frames = Frames(self, plan, nid, e.srcs, e.src_key, e.types, row, c)
            with self.probe(nid, row, e.raw_key, reader) as ev:
                try:
                    v = e.tool.run(frames, row, e.computed)
                except Cancelled:
                    raise
                except Exception as exc:
                    if not hasattr(exc, "sieve_node"):
                        exc.sieve_node = nid
                        self.note(nid, f"raised at row {row}: {type(exc).__name__}: {exc}")
                    raise
                ev[2] = getattr(v, "shape", None)
                if isinstance(got, Ref):    # its store let the array go: the memo holds the reference still, and nothing more
                    ev[1], v = 0, frames.named(got, v)
                else:
                    held = to_hold(v, frames.handed, e.static)
                    size = ev[1] = nbytes(e.produces, held)
                    v = frames.named(held) if isinstance(held, Ref) else held
            if not isinstance(got, Ref):
                self.memo.put(mk, held, owner=e.raw_key if e.static else None, size=size)
                if self.keeper is not None:
                    self.keeper.made(e, row, c, held)
        elif self.stream.on_event is not None:
            self._hit(nid, 0)
        return v if raw or e.band is None else banded(v, e.band)

    def density(self, nid, row, p=None):
        """`nid`'s plane at `row` folded to (BINS,) counts, memoized under its own key and probed on
        the node as a "fold"; None when the output is not a plane or its cut does not hold `row`; under the Plan `p`, the current
        one with none. Worker threads only."""
        plan = (p or self.snapshot()).entries
        e = plan.get(nid)
        if e is None or e.kind != "frame" or not e.fed:
            return None
        c, mk = _address(e, row)
        if c is None or not c.extent.holds(row):
            return None
        k = (_key(e.raw_key, "fold"), *mk[1:])
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
        c, mk = _address(e, row)
        if c is None or not c.extent.holds(row):
            return None
        if e.file is not None:
            d = self.readers.held(e.file[0])
            v = None if d is None else d.cached(row)
            return v if v is None or e.band is None else banded(v, e.band)
        v = self._memoized(mk)[1]
        return v if v is None or e.band is None else banded(v, e.band)


