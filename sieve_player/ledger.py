"""The ledger: the probe's stream kept over time, with no opinion of it. Wall time is cut into buckets
of one width over a bounded history, and each walk of a lane is one record. It is fed events and
samples and nothing else, holding no graph and importing no Qt, so a dump replays into one. `event`
only queues; the bookkeeping is done by whoever takes a `view()`, or by the emitting thread once the
queue is long and no reader is at it, so an emit never waits on a reader.
"""
import json
import math
import threading
from collections import deque
from contextlib import nullcontext
from dataclasses import dataclass, field, fields, replace

from .trace import OWN, SPANS, TURNS, read_dump

PARTS = 8           # the pieces a walk's range is cut into for a node's cost along it
BACKLOG = 4096      # events queued before the emitting thread folds them itself
FINEST = 2.0 ** -10 # ms; the bottom of a distribution's first bin
OCTAVE = 8          # bins to a doubling of ms
BINS = 26 * OCTAVE  # up to 2 ** 16 ms; a span past either end is counted in the bin at it

_RAN = {"run", "step", "fold", "decode", "seek"}
_FILE = {"decode", "seek", "read"}      # what a served node's file answered, its reader's cache not holding the row
_READS = _FILE | {"cache"}              # the kinds whose wall above CPU is a decoder's own threads at work and no wait


@dataclass
class Bucket:
    """One slice of wall time. A view's buckets are the ledger's own until it next writes one, which
    it copies first, so a reader holds them and never writes them."""
    ms: dict = field(default_factory=dict)          # thread -> {node: ms}, exclusive of the runs a run opened; a consumer's own under "dump" or "monitor"
    rows: dict = field(default_factory=dict)        # lane -> rows finished
    unprobed: float = 0.0                           # ms between a lane's rows that no span covers
    stores: dict = field(default_factory=dict)      # "memo", a cache's key or "<lane> stack" -> (bytes held, limit) at the bucket's last progress
    recomputed: dict = field(default_factory=dict)  # store -> computations and decodes of what it had discarded
    seeks: dict = field(default_factory=dict)       # node -> seeks
    late: float = 0.0                               # the worst lateness sampled, ms
    turns: dict = field(default_factory=dict)       # "slot walked", "paint plot" -> ms: the GUI thread's spans, apart from `ms`
    wait: float = 0.0                               # the tool spans' wall less their CPU, ms; signed, see Walk.wait
    read_wait: float = 0.0                          # the same of the read kinds
    machine: dict = field(default_factory=dict)     # the last "machine" sample in it, as machine.Machine.read gives one; {} with none
    shared: bool = field(default=False, compare=False, repr=False)

    def copy(self):
        return Bucket({t: dict(d) for t, d in self.ms.items()}, dict(self.rows), self.unprobed, dict(self.stores),
                      dict(self.recomputed), dict(self.seeks), self.late, dict(self.turns), self.wait, self.read_wait, self.machine)


_EMPTY = Bucket(shared=True)


@dataclass
class Node:
    """One node over one walk. A row counts once, by the most that happened to the node on it: it
    ran, else its served file answered, else a store held it."""
    runs: dict = field(default_factory=dict)        # (kind, demand, the node the demand named) -> [count, ms, bytes]
    ran: int = 0
    held: int = 0
    served: int = 0
    parts: list = field(default_factory=lambda: [0.0] * PARTS)     # ms in order along the range
    counts: list = field(default_factory=lambda: [0] * PARTS)      # the spans those ms were of
    bins: dict = field(default_factory=dict)        # kind -> the spans of it counted by their ms, BINS bins; see quantile()
    shape: list | None = None                       # of its output, as the last span that carried one had it

    def copy(self):
        return Node({k: list(v) for k, v in self.runs.items()}, self.ran, self.held, self.served, list(self.parts),
                    list(self.counts), {k: list(v) for k, v in self.bins.items()}, self.shape)


@dataclass
class Walk:
    """One pass of a lane over its range, opened by a "begin" event and holding everything the lane
    emitted until the next: the chain's run after the last row is this walk's. One that finished no
    row before the next began leaves no record, so a drag's restarts do not push the walks before
    them out of the history. A stream that marks no beginning opens one at a progress that goes back,
    with `start` unknown."""
    lane: str | None
    start: int | None       # the range's first row
    length: int
    plan: dict | None       # the facts of the last sync before it began; None when the ledger saw none
    keys: dict | None       # that sync's keys: two walks are under one plan when these are equal
    t0: float
    t1: float               # its last progress
    done: int = 0
    replanned: bool = False                         # it went on after a later sync: what it holds is of more than one plan
    nodes: dict = field(default_factory=dict)       # node -> Node
    recomputed: dict = field(default_factory=dict)  # store -> count, as a bucket's
    recomputed_ms: dict = field(default_factory=dict)   # store -> what those took
    unprobed: float = 0.0                           # ms between its rows that no span covers, as the buckets'
    wait: float = 0.0                               # its tool spans' wall less their CPU, ms; summed signed, one span's being a tick's noise either way
    read_wait: float = 0.0                          # the same of its reads, where it is the decoder's threads
    selected: list = field(default_factory=list)    # the nodes the player had selected as it began and while it walked

    def copy(self):
        return replace(self, nodes={n: v.copy() for n, v in self.nodes.items()}, recomputed=dict(self.recomputed),
                       recomputed_ms=dict(self.recomputed_ms), selected=list(self.selected))


@dataclass
class View:
    """What a reader is handed, its own to hold while the stream continues. Bucket `i` of `buckets`
    covers [(first + i) * width, (first + i + 1) * width) seconds on the probe's clock, with none
    missing between the first and the last; `walks` is oldest first, the last of each lane perhaps
    still walking."""
    width: float
    first: int
    buckets: list
    walks: list


class _Lane:
    def __init__(self):
        self.walk = None
        self.kinds = {}         # node -> the kinds it emitted since the lane's last progress
        self.t = None           # the lane's last progress or begin
        self.at = 0.0           # its thread's ms accounted for then
        self.synced = False     # a sync landed since the walk began


class Ledger:
    """`width` is a bucket's seconds, `history` the buckets kept, `walks` the records kept, and
    `discards` how many discarded (key, row) are remembered for telling a recomputation. `event` and
    `sample` may be called from any thread and never wait; a sample other than "late" and "machine" is not kept.
    `timed()` gives the context an emitting thread folds inside, for whoever attached the ledger to
    time its bookkeeping there, the ledger holding no graph to emit a span through."""

    def __init__(self, width=0.25, history=2400, walks=64, discards=1 << 17, timed=nullcontext):
        self.width, self.history, self._discards, self._timed = width, history, discards, timed
        self._q = deque()
        self._lock = threading.Lock()   # held to fold and to take a view; an emitter that finds it taken leaves the folding
        self._buckets, self._newest = {}, None
        self._walks = deque(maxlen=walks)
        self._lanes = {}
        self._plan = self._keys = self._selected = None
        self._nest = {}                 # thread -> [(start, end)] of the spans whose opening run has not emitted yet
        self._spent = {}                # thread -> ms accounted for: every span's, and the unprobed time given out
        self._gone = {}                 # (key, row) a store discarded -> the store

    def event(self, ev):
        self._q.append(ev)
        if len(self._q) > BACKLOG and self._lock.acquire(blocking=False):
            try:
                with self._timed():
                    self._fold()
            finally:
                self._lock.release()

    def sample(self, name, value, t):
        self._q.append((name, value, t))

    def view(self):
        with self._lock:
            self._fold()
            walking = {id(lane.walk) for lane in self._lanes.values()}
            walks = [w.copy() if id(w) in walking else w for w in self._walks]
            if self._newest is None:
                return View(self.width, 0, [], walks)
            first = min(self._buckets)
            buckets = [self._buckets.get(i, _EMPTY) for i in range(first, self._newest + 1)]
            for b in buckets:
                b.shared = True
            return View(self.width, first, buckets, walks)

    def _fold(self):
        q = self._q
        while q:
            item = q.popleft()
            if isinstance(item, tuple):
                name, value, t = item
                if name in ("late", "machine") and (b := self._bucket(int(t // self.width))) is not None:
                    if name == "late":
                        b.late = max(b.late, value)
                    else:
                        b.machine = value
            elif item.kind == "progress":
                self._progress(item)
            elif item.kind == "begin":
                self._begin(item, item.row)
            elif item.kind == "sync":
                self._plan, self._keys, self._selected = item.facts, item.keys, (item.facts or {}).get("selected")
                for lane in self._lanes.values():
                    lane.synced = True
            elif item.kind == "watch":
                self._selected = item.node
                for w in (lane.walk for lane in self._lanes.values()):
                    if w is not None and w.done < w.length and item.node is not None and item.node not in w.selected:
                        w.selected.append(item.node)
            elif item.kind in ("evict", "uncache"):
                self._gone[(item.key, item.row)] = "memo" if item.kind == "evict" else item.key
                if len(self._gone) > self._discards:
                    del self._gone[next(iter(self._gone))]
            elif item.kind in TURNS:
                name = f"{item.kind} {item.node}"
                for bucket, share in self._over(item.t, item.t + item.ms / 1000):
                    bucket.turns[name] = bucket.turns.get(name, 0.0) + item.ms * share
            elif item.kind in OWN:      # in the buckets under its thread and accounted for there, and in no walk
                name = item.kind if item.node in (None, item.kind) else f"{item.kind} {item.node}"
                for bucket, share in self._over(item.t, item.t + item.ms / 1000):
                    ms = bucket.ms.setdefault(item.thread, {})
                    ms[name] = ms.get(name, 0.0) + item.ms * share
                self._spent[item.thread] = self._spent.get(item.thread, 0.0) + item.ms
            elif item.kind in SPANS:
                self._span(item)

    def _bucket(self, i):
        """Bucket `i` to write into, or None for one older than the history."""
        if self._newest is None or i > self._newest:
            self._newest = i
            for old in [k for k in self._buckets if k <= i - self.history]:
                del self._buckets[old]
        elif i <= self._newest - self.history:
            return None
        b = self._buckets.get(i)
        if b is None or b.shared:
            b = self._buckets[i] = Bucket() if b is None else b.copy()
        return b

    def _over(self, t0, t1):
        """(bucket, share) for each bucket in the history that [t0, t1] lies in, the shares by overlap."""
        w = self.width
        i0, i1 = int(t0 // w), int(t1 // w)
        for i in range(max(i0, i1 - self.history + 1), i1 + 1):
            part = 1.0 if i0 == i1 else (min(t1, (i + 1) * w) - max(t0, i * w)) / (t1 - t0)
            if part > 0 and (b := self._bucket(i)) is not None:
                yield b, part

    def _begin(self, ev, start):
        lane = self._lanes.setdefault(ev.lane, _Lane())
        old, lane.walk = lane.walk, Walk(ev.lane, start, ev.length, self._plan, self._keys, ev.t, ev.t,
                                         selected=[] if self._selected is None else [self._selected])
        at = None if old is None or old.done else next((i for i, w in enumerate(self._walks) if w is old), None)
        if at is None:
            self._walks.append(lane.walk)
        else:
            self._walks[at] = lane.walk
        lane.kinds, lane.synced = {}, False
        lane.t, lane.at = ev.t, self._spent.get(ev.thread, 0.0)
        return lane

    def _span(self, ev):
        # On one thread a run emits after the runs it opened, each of which names its reader; a span
        # with none is opened by nothing, so the nest holds only what a run still to emit will take.
        nest = self._nest.setdefault(ev.thread, [])
        inner = []
        while nest and nest[-1][0] >= ev.t:
            inner.append(nest.pop())
        end = ev.t + ev.ms / 1000 + sum(b - a for a, b in inner)
        if ev.reader is not None:
            nest.append((ev.t, end))
        at, off, reads = ev.t, ev.ms - ev.cpu_ms, ev.kind in _READS
        for a, b in [*reversed(inner), (end, end)]:
            if a > at:
                for bucket, share in self._over(at, a):
                    ms, piece = bucket.ms.setdefault(ev.thread, {}), (a - at) * 1000 * share
                    ms[ev.node] = ms.get(ev.node, 0.0) + piece
                    if reads:
                        bucket.read_wait += off * piece / ev.ms
                    else:
                        bucket.wait += off * piece / ev.ms
            at = max(at, b)
        self._spent[ev.thread] = self._spent.get(ev.thread, 0.0) + ev.ms
        lane = self._lanes.get(ev.lane)
        walk = None if lane is None else lane.walk
        store = self._gone.pop((ev.key, ev.row), None) if ev.kind in _RAN else None
        if (store is not None or ev.kind == "seek") and (b := self._bucket(int(ev.t // self.width))) is not None:
            if store is not None:
                b.recomputed[store] = b.recomputed.get(store, 0) + 1
            if ev.kind == "seek":
                b.seeks[ev.node] = b.seeks.get(ev.node, 0) + 1
        if walk is None:
            return
        if store is not None:
            walk.recomputed[store] = walk.recomputed.get(store, 0) + 1
            walk.recomputed_ms[store] = walk.recomputed_ms.get(store, 0.0) + ev.ms
        if lane.synced and ev.kind != "cancel":     # a cancelled run was the old plan's
            walk.replanned = True
        if reads:
            walk.read_wait += off
        else:
            walk.wait += off
        node = walk.nodes.setdefault(ev.node, Node())
        run = node.runs.setdefault((ev.kind, ev.demand, ev.asked), [0, 0.0, 0])
        run[0] += 1
        run[1] += ev.ms
        run[2] += ev.bytes
        part = min(PARTS - 1, walk.done * PARTS // max(walk.length, 1))
        node.parts[part] += ev.ms
        node.counts[part] += 1
        bins = node.bins.get(ev.kind)
        if bins is None:
            bins = node.bins[ev.kind] = [0] * BINS
        bins[min(BINS - 1, max(0, int(math.log2(ev.ms / FINEST) * OCTAVE))) if ev.ms > 0 else 0] += 1
        if ev.shape is not None:
            node.shape = list(ev.shape)
        lane.kinds.setdefault(ev.node, set()).add(ev.kind)

    def _progress(self, ev):
        lane = self._lanes.get(ev.lane)
        if lane is None or lane.walk is None or ev.row < lane.walk.done:
            lane = self._begin(ev, None)
            lane.walk.done, lane.t = ev.row - 1, None       # no beginning was marked: the row is all that is known of it
        walk, facts = lane.walk, ev.facts or {}
        spent = self._spent.get(ev.thread, 0.0)
        if lane.t is not None:
            gap = max(0.0, (ev.t - lane.t) * 1000 - (spent - lane.at))
            for bucket, share in self._over(lane.t, ev.t):
                bucket.unprobed += gap * share
            spent = self._spent[ev.thread] = spent + gap
            walk.unprobed += gap
        lane.t, lane.at = ev.t, spent
        rows = ev.row - walk.done
        walk.done, walk.length, walk.t1 = ev.row, ev.length, ev.t
        walk.replanned = walk.replanned or lane.synced
        b = self._bucket(int(ev.t // self.width))
        if b is not None:
            if rows:
                b.rows[ev.lane] = b.rows.get(ev.lane, 0) + rows
            for store, s in {"memo": facts.get("memo"), **facts.get("caches", {}), f"{ev.lane or 'walk'} stack": facts.get("stack")}.items():
                if s is not None:
                    b.stores[store] = (s["bytes"], s["limit"])
        if rows:
            served = {n for n, f in ((walk.plan or {}).get("nodes") or {}).items() if f["served"]}
            hit = facts.get("hits", {}).keys() | facts.get("fold_hits", {}).keys()
            for nid in lane.kinds.keys() | hit:
                kinds, node = lane.kinds.get(nid, ()), walk.nodes.setdefault(nid, Node())
                if "read" in kinds or nid in served and _FILE & set(kinds):
                    node.served += 1
                elif _RAN & set(kinds):
                    node.ran += 1
                elif "cache" in kinds or nid in hit:
                    node.held += 1
        lane.kinds = {}


def coarsen(view, k):
    """`view` with its buckets merged `k` at a time on the probe's clock, each the reading a bucket
    `k` widths wide would have held: what is summed summed, the lateness the worst, a store and the
    machine as the last bucket that had one found it. The walks are the view's own."""
    if k <= 1:
        return view
    first, out = view.first // k, []
    for i, b in enumerate(view.buckets, view.first):
        if i // k - first == len(out):
            out.append(Bucket())
        if b is _EMPTY:
            continue
        m = out[-1]
        for thread, d in b.ms.items():
            ms = m.ms.setdefault(thread, {})
            for n, v in d.items():
                ms[n] = ms.get(n, 0.0) + v
        for name in ("rows", "recomputed", "seeks", "turns"):
            d = getattr(m, name)
            for key, v in getattr(b, name).items():
                d[key] = d.get(key, 0) + v
        m.stores.update(b.stores)
        m.machine = b.machine or m.machine
        m.unprobed, m.wait, m.read_wait, m.late = m.unprobed + b.unprobed, m.wait + b.wait, m.read_wait + b.read_wait, max(m.late, b.late)
    return View(view.width * k, first, out, view.walks)


def quantile(bins, q):
    """The ms at quantile `q`, 0 to 1, of the spans counted in `bins`, a value of Node.bins: the
    middle of the bin the q-th span fell in, so within a twenty-fourth of it; None with no span."""
    total, seen = sum(bins), 0
    if not total:
        return None
    for i, n in enumerate(bins):
        seen += n
        if n and seen >= q * total:
            return FINEST * 2 ** ((i + 0.5) / OCTAVE)


def replay(path, **kwargs):
    """A Ledger fed the events and samples of the dump at `path`."""
    _, events, samples = read_dump(path)
    ledger = Ledger(**kwargs)
    for ev in events:
        ledger.event(ev)
    for s in samples:
        ledger.sample(s["sample"], s["value"], s["t"])
    return ledger


def save(view, path, **more):
    """Writes `view` to `path` as one JSON file `saved` reads back, with `more` beside it: plain
    values, the document and whatever else a reader of the history needs that no walk's plan holds."""
    def plain(x, also):
        return {f.name: getattr(x, f.name) for f in fields(x) if f.name != "shared"} | also
    out = {"width": view.width, "first": view.first, "more": more,
           "buckets": [plain(b, {"rows": list(b.rows.items())}) for b in view.buckets],     # a lane may be None, which is no JSON key
           "walks": [plain(w, {"nodes": {n: plain(x, {"runs": [[*k, *v] for k, v in x.runs.items()]})
                                         for n, x in w.nodes.items()}}) for w in view.walks]}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f)


def saved(path):
    """(a Ledger holding the buckets and walks `save` wrote to `path`, every walk closed, and the
    `more` written beside them)."""
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    ledger = Ledger(width=d["width"], history=max(len(d["buckets"]), 1), walks=max(len(d["walks"]), 1))
    for i, b in enumerate(d["buckets"], d["first"]):
        ledger._buckets[i] = Bucket(**b | {"rows": {lane: n for lane, n in b["rows"]},
                                           "stores": {k: tuple(v) for k, v in b["stores"].items()}})
        ledger._newest = i
    for w in d["walks"]:
        nodes = {n: Node(**x | {"runs": {tuple(r[:3]): r[3:] for r in x["runs"]}}) for n, x in w["nodes"].items()}
        ledger._walks.append(Walk(**w | {"nodes": nodes}))
    return ledger, d["more"]
