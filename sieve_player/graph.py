"""The runtime: what the graph says, computed and memoized.

A Graph is built from a document, a decoder and the tools the document's names resolve to. It
snapshots the document on `sync()`, which the window calls after any change, so a worker thread
mid-computation works from one consistent plan and the next computation sees the new one. Params
are read from the document's nodes; the runtime holds none of its own. A node is computed as None
when nothing reaches it: no wire, an unresolved tool, or a wire whose types do not fit.
"""
import threading
import time
from collections import OrderedDict, deque
from contextlib import contextmanager
from dataclasses import dataclass

import numpy as np

from . import density
from .document import INPUT, video_output, video_scale
from .plan import _key, base_key, plan, shared_fold, walked

WINDOW = 64     # rows a running mean spans; the decoder's step and seek means keep their own literal, see Decoder._mean


def _mean(mean, x, n):
    return x if mean is None else mean + (x - mean) / min(n, WINDOW)


def _rate(hits, misses):
    return hits / (hits + misses) if hits + misses else None


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

    def put(self, k, v, owner=None):
        """`v` under `k`, pinned to `owner` when one is given; a key already held is left as it is."""
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
            self.bytes += self._size(v)
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
            return g._compute(self._plan, self._sources[input], row)
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


@dataclass(frozen=True, slots=True)
class Event:
    """What the probe emits, one per run, read or boundary; see Graph.probe(). Every field is
    required, so a consumer building or reading one by position, or one missing a field, fails
    where it stands instead of misreading its neighbour."""
    node: str | None    # the node that ran, or read; None on a boundary
    row: int | None
    key: str | None     # the node's raw key, what the memo holds under
    kind: str           # "run" | "fold" | "error" | "cancel" | "cache" | "step" | "seek" | "sync" | "evict" | "uncache" | "progress" | "dump"
    bytes: int          # the result's; what an eviction freed
    ms: float           # wall, exclusive of the runs this one opened
    t: float            # start, on the probe's clock (perf_counter); orders events across threads
    thread: str         # the emitting thread's name
    cpu_ms: float       # the thread's CPU time over the same span, exclusive likewise; wall far above it is a wait. On
                        # Windows thread_time ticks at the scheduler quantum (~16 ms), so one event's is 0 or a tick and
                        # only a sum over many events is a figure
    serves: str | None  # "scrub" | "walk": what the worker was doing; None off the worker (bench, tests)
    length: int | None  # progress only: rows in the window, `row` being the rows done
    keys: dict | None   # sync only: every node's key under the new plan, band included; diff two to see what a drag changed


class Graph:
    def __init__(self, doc, decoder, tools, memo_bytes=4 << 30):
        self.doc, self.decoder = doc, decoder
        self.tools = tools if hasattr(tools, "get") else {t.NAME: t for t in tools}
        self.fps = decoder.fps
        self.memo = Memo(memo_bytes)
        self._lock = threading.Lock()
        self.on_event = None                # the probe's one consumer; see probe() for the event
        self.halt = False                   # set by whoever is stopping the worker: every Frames read from then on raises Cancelled
        self._probing = threading.local()   # the runs open on this thread, so a run's time excludes its reads
        self._base = None                   # the video node's key: the file and what the decoder hands out; set at sync()
        # The two stores report what they discard into the same stream: the memo's entry by its key and
        # row, the decoder cache's frame by its row under the video's key.
        self.memo.on_evict = lambda k, n: self._emit("evict", None, k[1], k[0], n)
        decoder.on_evict = lambda row, n: self._emit("uncache", None, row, self._base, n)
        self._plan = {}
        self._notes = {}                    # node -> (its key, what the run said): a tool raising, a chain node fed no signal
        self.shown = self.over = self.series = None
        self.chain, self.heads, self.unrun_series = [], [], []
        self.sync()

    @property
    def count(self):
        """The decoder's, read live: a container's header may claim rows the stream lacks, and the
        decoder corrects itself at the first read past the end."""
        return self.decoder.count

    def sync(self):
        """Re-read the document: the plan, pure in the document and the tools (see `plan`), and the
        decoder's output and scale, which the video node's params set."""
        output, scale = video_output(self.doc), video_scale(self.doc)
        self.decoder.output = output        # a change empties its cache; a read in flight under the old plan is cancelled
        self.decoder.scale = scale
        self._base = base_key(self.decoder.path, output, scale)
        p = plan(self.doc, self.tools, self._base)
        with self._lock:
            self._plan = p.entries
            self.shown, self.over = p.shown, p.over
            self.series = p.chain[0] if p.chain else None
            self.heads, self.chain, self.unrun_series = p.heads, p.chain, p.unrun
        self.memo.unpin({e.raw_key for e in p.entries.values() if e.static})
        # A boundary in the stream: what runs next ran under a new plan, whose keys it carries.
        self._emit("sync", None, None, None, 0, keys={nid: e.key for nid, e in p.entries.items()})

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

    def compute(self, nid, row, raw=False):
        """Output of `nid` at `row`, memoized; None for a node nothing reaches. Worker threads only.
        The whole recursion runs in the plan current at the call, so what lands in the memo under a
        key was computed from the graph that key describes. `raw` is the plane before the node's band,
        what its density counts, so the axis holds while a handle moves."""
        with self._lock:
            plan = self._plan
        return self._compute(plan, nid, row, raw)

    def _emit(self, kind, nid, row, key, nbytes, ms=0.0, t=None, cpu_ms=0.0, length=None, keys=None):
        """One Event to `on_event`, stamped here with what every event carries: its start, the
        thread. The probe passes the times it measured; a boundary or an eviction has none and is
        stamped now."""
        if self.on_event is not None:
            self.on_event(Event(nid, row, key, kind, nbytes, ms, time.perf_counter() if t is None else t,
                                threading.current_thread().name, cpu_ms, getattr(self._probing, "serves", None), length, keys))

    def progress(self, done, length):
        """The walk's progress, `done` rows of `length`, as an event; whoever drives the walk, the
        worker or bench.py, says so as each row lands, and a reader takes the rate from the stream."""
        self._emit("progress", None, done, None, 0, length=length)

    def serving(self, what):
        """What the events this thread emits from here on served, "scrub" or "walk"; the worker says
        at the top of each loop, since only it knows, and nothing else sets it."""
        self._probing.serves = what

    @contextmanager
    def probe(self, nid, row, key):
        """Times the run inside and hands `on_event` one Event, its ms wall time exclusive of the
        runs it opened in turn, so a cold row charges the decode to the video node and each tool its
        own work. The body sets `kind` and `bytes` on the yielded
        list, what only the call site knows: a tool's kind is "run", since a memo hit is not a run
        and emits nothing; the video read's is "cache", "step" or "seek", read off the decoder's
        counters; a body that raises emits "error", or "cancel" for Cancelled, with the time it took and
        no bytes, so a reader tells a failed run from one that returned. Nothing when `on_event` is unset. `sync()` emits a "sync" event into the same
        stream, a boundary with no node, row or time, and the memo and decoder cache emit "evict"
        and "uncache" with the bytes freed. The worker wraps a series tool's run in this; `_compute`
        wraps a frame tool's and the video node's read."""
        if self.on_event is None:
            yield [None, 0]
            return
        stack = self._probing.__dict__.setdefault("stack", [])
        stack.append([0.0, 0.0])             # wall and CPU the runs opened inside this one took
        ev = ["run", 0]
        t, c = time.perf_counter(), time.thread_time()
        try:
            yield ev
        except Cancelled:
            ev[0] = "cancel"                 # the graph moved on under the run; not the tool's fault
            raise
        except BaseException:
            ev[0] = "error"                  # the body raised: a tool failed, or the read ran off the stream's end
            raise
        finally:
            total, cpu = time.perf_counter() - t, time.thread_time() - c
            inner, inner_cpu = stack.pop()
            if stack:
                stack[-1][0] += total
                stack[-1][1] += cpu
            self._emit(ev[0], nid, row, key, ev[1], (total - inner) * 1000, t, (cpu - inner_cpu) * 1000)

    def _compute(self, plan, nid, row, raw=False):
        e = plan.get(nid)
        if e is None or e.kind in ("series", "selector") or not e.fed:
            return None
        if e.kind == "video":
            d = self.decoder
            with self.probe(nid, row, e.raw_key) as ev:
                decodes, seeks = d.decodes, d.seeks
                v = d.read(row)
                ev[0] = "seek" if d.seeks != seeks else "step" if d.decodes != decodes else "cache"
                ev[1] = v.nbytes
            return v
        mk = (e.raw_key, None if e.static else row)
        v = self.memo.get(mk)
        if v is None:
            with self.probe(nid, row, e.raw_key) as ev:
                try:
                    v = e.tool.run(Frames(self, plan, nid, e.srcs, e.src_key, e.types), row, e.params)
                except Cancelled:
                    raise
                except Exception as exc:
                    if not hasattr(exc, "sieve_node"):
                        exc.sieve_node = nid
                        self.note(nid, f"raised at row {row}: {type(exc).__name__}: {exc}")
                    raise
                ev[1] = Memo._size(v)
            self.memo.put(mk, v, owner=e.raw_key if e.static else None)
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
            plane = self._compute(plan, nid, row, raw=True)
            if not density.is_plane(plane):
                return None
            with self.probe(nid, row, k[0]) as ev:
                v = density.fold(plane)
                ev[0], ev[1] = "fold", v.nbytes
            self.memo.put(k, v, owner=e.raw_key if e.static else None)
        return v

    def peek(self, row, nid=None):
        """Memo-only read of the shown node, or of `nid`, at `row`; None if it isn't there. GUI-safe."""
        with self._lock:
            e = self._plan.get(self.shown if nid is None else nid)
        if e is None or not e.fed:
            return None
        if e.kind == "video":
            return self.decoder.cached(row)
        v = self.memo.get((e.raw_key, None if e.static else row))
        return v if v is None or e.band is None else banded(v, e.band)


class Stats:
    """The probe's first consumer. Per node, the last figure and a running mean over the window the
    decoder's means use, blind to key, kind and bytes; beside them the series chain's time per emit,
    the walk's rate in rows per second, read off the progress events, and the decoder's and memo's
    own counters. Making one installs it as the graph's `on_event`, passing each event on to whatever
    was there before, so consumers chain in any order; `event` is its one entry point. `snapshot()`
    is one plain dict, the only thing a reader gets: the window and bench.py read the same and
    neither reaches into the runtime."""

    def __init__(self, graph):
        self.graph = graph
        self._lock = threading.Lock()
        self._nodes = {}                    # nid -> [last ms, mean ms, runs]
        self._walk = deque(maxlen=WINDOW)   # (time, rows done) as the walk reports them
        self._prev = graph.on_event
        graph.on_event = self.event

    def event(self, ev):
        if self._prev is not None:
            self._prev(ev)
        if ev.kind in ("sync", "evict", "uncache", "error", "fold"):
            return                          # the means are the tool's; a fold is not
        with self._lock:
            if ev.kind == "progress":
                if self._walk and ev.row < self._walk[-1][1]:
                    self._walk.clear()      # a new walk; the rate is this one's
                self._walk.append((ev.t, ev.row))
                return
            e = self._nodes.setdefault(ev.node, [0.0, None, 0])
            e[2] += 1
            e[0], e[1] = ev.ms, _mean(e[1], ev.ms, e[2])

    def snapshot(self):
        g, d, m = self.graph, self.graph.decoder, self.graph.memo
        with self._lock:
            nodes = {nid: {"last": last, "mean": mean, "n": n} for nid, (last, mean, n) in self._nodes.items()}
            rate = None
            if len(self._walk) > 1 and self._walk[-1][0] > self._walk[0][0]:
                (t0, r0), (t1, r1) = self._walk[0], self._walk[-1]
                rate = (r1 - r0) / (t1 - t0)
        chain = [nid for nid in g.chain if nid in nodes]
        return {
            "nodes": nodes,
            "series_ms": sum(nodes[nid]["last"] for nid in chain) if chain else None,
            "walk_rows_s": rate, "fps": g.fps,
            "step_ms": d.step_ms, "seek_ms": d.seek_ms, "decodes": d.decodes, "seeks": d.seeks,
            "memo_mb": m.bytes / 2**20, "memo_hit": _rate(m.hits, m.misses), "evictions": m.evictions,
            "cache_mb": d.cache_bytes / 2**20, "cache_hit": _rate(d.cache_hits, d.reads - d.cache_hits),
        }
