"""The runtime: what the graph says, computed and memoized.

A Graph is built from a document, a decoder and the tools the document's names resolve to. It
snapshots the document on `sync()`, which the window calls after any change, so a worker thread
mid-computation works from one consistent plan and the next computation sees the new one. Params
are read from the document's nodes; the runtime holds none of its own. A node is computed as None
when nothing reaches it: no wire, an unresolved tool, or a wire whose types do not fit.
"""
import hashlib
import json
import threading
import time
from collections import OrderedDict, deque
from contextlib import contextmanager
from dataclasses import dataclass

import numpy as np

from .document import OPEN, OVERLAYABLE, VIDEO_PRODUCES, VIDEO_TOOL, fed, is_selector, produces


def _key(*parts):
    return hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:16]


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
    signal keeps under the node's band, and `fed`, the signal with the rest zeroed, which is what a
    series node downstream reads. A result without a signal passes through ungated, and feeds nothing."""
    if not isinstance(result, dict) or "signal" not in result:
        return result, None
    signal = np.asarray(result["signal"])
    gate = inband(signal, OPEN if band is None else band)
    return {**result, "gate": gate}, np.where(gate, signal, np.zeros((), signal.dtype))


class Memo:
    """LRU bounded by bytes. Image-shaped entries (ndim >= 2) are evicted before small ones. Each
    eviction goes to `on_evict(key, bytes)` when set, after the lock is dropped."""

    def __init__(self, limit_bytes):
        self.limit = limit_bytes
        self.bytes = 0
        self._big, self._small = OrderedDict(), OrderedDict()
        self._lock = threading.Lock()
        self.hits = self.misses = self.evictions = 0
        self.on_evict = None

    @staticmethod
    def _size(v):
        return v.nbytes if isinstance(v, np.ndarray) else 64

    def get(self, k):
        with self._lock:
            for d in (self._big, self._small):
                v = d.get(k)
                if v is not None:
                    d.move_to_end(k)
                    self.hits += 1
                    return v
            self.misses += 1
            return None

    def put(self, k, v):
        d = self._big if isinstance(v, np.ndarray) and v.ndim >= 2 else self._small
        gone = []
        with self._lock:
            if k in self._big or k in self._small:
                return
            d[k] = v
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


class Frames:
    """What a frame tool's run() gets: frames(r) is the output of the node it reads, at row r. It
    reads through the plan the computation began in, so one run() sees one graph even if the
    document is synced under it."""

    def __init__(self, graph, plan, source, key):
        self._graph, self._plan, self._source = graph, plan, source
        self.key, self.fps, self.count = key, graph.fps, graph.count

    def __call__(self, row):
        return self._graph._compute(self._plan, self._source, row)


class Series:
    """What a series tool's run() gets: data is (T, ...), the read node stacked over the window, each
    row through the tool's fold() first when it has one; or, for a series node reading another, the
    upstream node's (T,) signal with the rows its band shuts out zeroed."""

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
    kind: str           # "run" | "error" | "cache" | "step" | "seek" | "sync" | "evict" | "uncache" | "progress" | "dump"
    bytes: int          # the result's; what an eviction freed
    ms: float           # wall, exclusive of the runs this one opened
    t: float            # start, on the probe's clock (perf_counter); orders events across threads
    thread: str         # the emitting thread's name
    cpu_ms: float       # the thread's CPU time over the same span, exclusive likewise; wall far above it is a wait
    serves: str | None  # "scrub" | "walk": what the worker was doing; None off the worker (bench, tests)
    length: int | None  # progress only: rows in the window, `row` being the rows done
    keys: dict | None   # sync only: every node's key under the new plan, band included; diff two to see what a drag changed


@dataclass
class _Entry:
    """One node as the plan saw it at sync()."""
    tool: object
    kind: str           # "video" | "frame" | "series" | "selector"
    params: dict
    band: tuple | None  # (lo, hi): what the node's plane, or signal, keeps; see document
    src: str | None     # the node its input wire names
    key: str
    raw_key: str         # the key without the band: what the memo holds
    src_key: str | None
    fed: bool


class Graph:
    def __init__(self, doc, decoder, tools, memo_bytes=512 << 20):
        self.doc, self.decoder = doc, decoder
        self.tools = tools if hasattr(tools, "get") else {t.NAME: t for t in tools}
        self.fps, self.count = decoder.fps, decoder.count
        self.memo = Memo(memo_bytes)
        self._lock = threading.Lock()
        self.on_event = None                # the probe's one consumer; see probe() for the event
        self._probing = threading.local()   # the runs open on this thread, so a run's time excludes its reads
        self._base = _key("video", decoder.path, VIDEO_PRODUCES)
        # The two stores report what they discard into the same stream: the memo's entry by its key and
        # row, the decoder cache's frame by its row under the video's key.
        self.memo.on_evict = lambda k, n: self._emit("evict", None, k[1], k[0], n)
        decoder.on_evict = lambda row, n: self._emit("uncache", None, row, self._base, n)
        self._plan = {}
        self.shown = self.over = self.series = None
        self.chain, self.unrun_series = [], []
        self.sync()

    def sync(self):
        """Re-read the document: wiring, params, the flags, which series nodes run."""
        doc, tools = self.doc, self.tools
        keys, raw_keys = {}, {}

        def key_of(nid, stack=()):
            # The raw key names what the tool computes and the memo holds; the key adds the band, which
            # is applied on read, so what downstream sees is keyed by it and the node's own run is not.
            if nid not in keys:
                node = doc.node(nid)
                if node.tool == VIDEO_TOOL:
                    keys[nid] = raw_keys[nid] = self._base
                else:
                    w = doc.source(nid)
                    up = "none" if w is None or w.src in stack else key_of(w.src, (*stack, nid))
                    raw_keys[nid] = _key(up, node.tool, json.dumps(node.params, sort_keys=True))
                    keys[nid] = raw_keys[nid] if node.band is None else _key(raw_keys[nid], node.band)
            return keys[nid]

        plan, series = {}, []
        for n in doc.nodes:
            tool = tools.get(n.tool)
            if n.tool == VIDEO_TOOL:
                kind = "video"
            elif is_selector(tool):
                kind = "selector"       # answers a path, once, before the decoder; never a row
            else:
                kind = getattr(tool, "KIND", "frame")
            w = doc.source(n.id)
            src = w.src if w else None
            plan[n.id] = _Entry(tool, kind, dict(n.params), n.band, src, key_of(n.id), raw_keys[n.id],
                                key_of(src) if src else None, fed(doc, n.id, tools))
            if kind == "series":
                series.append(n.id)
        # The head is the first series node reading a frame node: it runs on the walked stack. The
        # chain is it and every fed series node wired on from a chain node, which run on the
        # upstream result's signal in this order. Any other series node is unrun.
        heads = [s for s in series if plan[s].src is None or plan[plan[s].src].kind != "series"]
        chain = heads[:1]
        for nid in chain:
            chain += [s for s in series if plan[s].src == nid and plan[s].fed and s not in chain]
        with self._lock:
            self._plan = plan
            self.shown = doc.display if doc.display in plan else None
            # The overlay is a node the frame can be heated with: one plane, so only an OVERLAYABLE product.
            self.over = doc.overlay if doc.overlay in plan and produces(doc, tools, doc.overlay) in OVERLAYABLE else None
            self.series = chain[0] if chain else None
            self.chain, self.unrun_series = chain, [s for s in series if s not in chain]
        # A boundary in the stream: what runs next ran under a new plan, whose keys it carries.
        self._emit("sync", None, None, None, 0, keys={nid: e.key for nid, e in plan.items()})

    # -- what the worker and the display ask -------------------------------
    def _walk(self):
        if self.series is None:
            return self.shown
        e = self._plan[self.series]
        return e.src if e.fed else None

    @property
    def walk(self):
        """The node the worker computes over the window: what the series node reads, else what is
        shown. None when the series node is not fed, so its tool never sees a type it does not expect."""
        with self._lock:
            return self._walk()

    def walk_row(self, row):
        """The walked node at `row` as the worker stacks it: through the head's fold() when it has one,
        so what the window holds is what the series tool asked for and never the frame. Worker threads only."""
        with self._lock:
            plan, nid = self._plan, self._walk()
            fold = getattr(plan[self.series].tool, "fold", None) if self.series else None
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
        """[(node, tool, params, band, the node it reads)] in run order: the head first, then each
        series node on from a chain node. The worker feeds the head the stack and the rest the
        upstream result's signal under its band (see `gated`)."""
        with self._lock:
            return [(nid, self._plan[nid].tool, dict(self._plan[nid].params), self._plan[nid].band, self._plan[nid].src)
                    for nid in self.chain]

    def key(self, nid):
        with self._lock:
            return self._plan[nid].key

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
        counters; a body that raises emits "error", with the time it took and no bytes, so a reader
        tells a failed run from one that returned. Nothing when `on_event` is unset. `sync()` emits a "sync" event into the same
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
        mk = (e.raw_key, row)
        v = self.memo.get(mk)
        if v is None:
            with self.probe(nid, row, e.raw_key) as ev:
                v = e.tool.run(Frames(self, plan, e.src, e.src_key), row, e.params)
                ev[1] = Memo._size(v)
            self.memo.put(mk, v)
        return v if raw or e.band is None else banded(v, e.band)

    def peek(self, row, nid=None):
        """Memo-only read of the shown node, or of `nid`, at `row`; None if it isn't there. GUI-safe."""
        with self._lock:
            e = self._plan.get(self.shown if nid is None else nid)
        if e is None or not e.fed:
            return None
        if e.kind == "video":
            return self.decoder.cached(row)
        v = self.memo.get((e.raw_key, row))
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
        if ev.kind in ("sync", "evict", "uncache", "error"):
            return
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
