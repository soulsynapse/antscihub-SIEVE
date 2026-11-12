"""The ledger: the probe's stream kept over time, with no opinion of it. Wall time is cut into buckets
of one width over a bounded history, and each walk of a lane is one record. It is fed events and
samples and nothing else, holding no graph and importing no Qt, so a dump replays into one. `event`
only queues; the bookkeeping is done by whoever takes a `view()`, or by the emitting thread once the
queue is long and no reader is at it, so an emit never waits on a reader.
"""
import threading
from collections import deque
from dataclasses import dataclass, field, replace

from .trace import SPANS, read_dump

PARTS = 8           # the pieces a walk's range is cut into for a node's cost along it
BACKLOG = 4096      # events queued before the emitting thread folds them itself

_RAN = {"run", "step", "fold", "decode", "seek"}
_FILE = {"decode", "seek", "read"}      # what a served node's file answered, its reader's cache not holding the row


@dataclass
class Bucket:
    """One slice of wall time. A view's buckets are the ledger's own until it next writes one, which
    it copies first, so a reader holds them and never writes them."""
    ms: dict = field(default_factory=dict)          # thread -> {node: ms}, exclusive of the runs a run opened
    rows: dict = field(default_factory=dict)        # lane -> rows finished
    unprobed: float = 0.0                           # ms between a lane's rows that no span covers
    stores: dict = field(default_factory=dict)      # "memo" or a cache's key -> (bytes held, limit) at the bucket's last progress
    recomputed: dict = field(default_factory=dict)  # store -> computations and decodes of what it had discarded
    seeks: dict = field(default_factory=dict)       # node -> seeks
    late: float = 0.0                               # the worst lateness sampled, ms
    shared: bool = field(default=False, compare=False, repr=False)

    def copy(self):
        return Bucket({t: dict(d) for t, d in self.ms.items()}, dict(self.rows), self.unprobed, dict(self.stores),
                      dict(self.recomputed), dict(self.seeks), self.late)


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

    def copy(self):
        return Node({k: list(v) for k, v in self.runs.items()}, self.ran, self.held, self.served, list(self.parts))


@dataclass
class Walk:
    """One pass of a lane over its range, opened by a "begin" event and holding everything the lane
    emitted until the next: the chain's run after the last row is this walk's. A stream that marks no
    beginning opens one at a progress that goes back, with `start` unknown."""
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

    def copy(self):
        return replace(self, nodes={n: v.copy() for n, v in self.nodes.items()}, recomputed=dict(self.recomputed))


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
    `sample` may be called from any thread and never wait; a sample other than "late" is not kept."""

    def __init__(self, width=0.25, history=2400, walks=64, discards=1 << 17):
        self.width, self.history, self._discards = width, history, discards
        self._q = deque()
        self._lock = threading.Lock()   # held to fold and to take a view; an emitter that finds it taken leaves the folding
        self._buckets, self._newest = {}, None
        self._walks = deque(maxlen=walks)
        self._lanes = {}
        self._plan = self._keys = None
        self._nest = {}                 # thread -> [(start, end)] of the spans whose opening run has not emitted yet
        self._spent = {}                # thread -> ms accounted for: every span's, and the unprobed time given out
        self._gone = {}                 # (key, row) a store discarded -> the store

    def event(self, ev):
        self._q.append(ev)
        if len(self._q) > BACKLOG and self._lock.acquire(blocking=False):
            try:
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
                if name == "late" and (b := self._bucket(int(t // self.width))) is not None:
                    b.late = max(b.late, value)
            elif item.kind == "progress":
                self._progress(item)
            elif item.kind == "begin":
                self._begin(item, item.row)
            elif item.kind == "sync":
                self._plan, self._keys = item.facts, item.keys
                for lane in self._lanes.values():
                    lane.synced = True
            elif item.kind in ("evict", "uncache"):
                self._gone[(item.key, item.row)] = "memo" if item.kind == "evict" else item.key
                if len(self._gone) > self._discards:
                    del self._gone[next(iter(self._gone))]
            elif item.kind in SPANS and item.kind != "dump":    # the dump's writer is in the file and never in the stream
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
        lane.walk = Walk(ev.lane, start, ev.length, self._plan, self._keys, ev.t, ev.t)
        self._walks.append(lane.walk)
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
        at = ev.t
        for a, b in [*reversed(inner), (end, end)]:
            if a > at:
                for bucket, share in self._over(at, a):
                    ms = bucket.ms.setdefault(ev.thread, {})
                    ms[ev.node] = ms.get(ev.node, 0.0) + (a - at) * 1000 * share
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
        if lane.synced and ev.kind != "cancel":     # a cancelled run was the old plan's
            walk.replanned = True
        node = walk.nodes.setdefault(ev.node, Node())
        run = node.runs.setdefault((ev.kind, ev.demand, ev.asked), [0, 0.0, 0])
        run[0] += 1
        run[1] += ev.ms
        run[2] += ev.bytes
        node.parts[min(PARTS - 1, walk.done * PARTS // max(walk.length, 1))] += ev.ms
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
        lane.t, lane.at = ev.t, spent
        rows = ev.row - walk.done
        walk.done, walk.length, walk.t1 = ev.row, ev.length, ev.t
        walk.replanned = walk.replanned or lane.synced
        b = self._bucket(int(ev.t // self.width))
        if b is not None:
            if rows:
                b.rows[ev.lane] = b.rows.get(ev.lane, 0) + rows
            for store, s in {"memo": facts.get("memo"), **facts.get("caches", {})}.items():
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


def replay(path, **kwargs):
    """A Ledger fed the events and samples of the dump at `path`."""
    _, events, samples = read_dump(path)
    ledger = Ledger(**kwargs)
    for ev in events:
        ledger.event(ev)
    for s in samples:
        ledger.sample(s["sample"], s["value"], s["t"])
    return ledger
