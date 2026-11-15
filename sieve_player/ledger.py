"""The ledger: the probe's stream kept over time, with no opinion of what is wrong in it. Wall time is cut into buckets
of one width over a bounded history, and each walk of a lane is one record. It is fed events and
samples and nothing else, holding no graph and importing no Qt, so a dump replays into one. `event`
and `sample` only queue; the bookkeeping is done by whoever takes a `view()`, or by the thread that
queues once the queue is long and no reader is at it, so an emit never waits on a reader and the
queue is bounded with no reader at all.
"""
import json
import math
import sys
import threading
import time
import traceback
from collections import deque
from contextlib import nullcontext
from dataclasses import dataclass, field, fields, replace
from typing import NamedTuple

from .stream import (BEGIN, CACHE, CANCEL, DECODE, EVICT, FOLD, NODE_FACTS, NODES, OWN, PLAN_FACTS, PROGRESS, READ, REST, RUN, SEEK, STEP, SYNC,
                     TURNS, UNCACHE, WAKE, WATCH)
from .trace import read_dump

PARTS = 8           # the pieces a walk's range is cut into for a node's cost along it
BACKLOG = 4096      # events and samples queued before the thread that queues the next folds them itself
FINEST = 2.0 ** -10 # ms; the bottom of a distribution's first bin
OCTAVE = 8          # bins to a doubling of ms
LONG = 50.0         # ms; a tool's span this long or longer is kept as its bucket's longest of its node
BINS = 26 * OCTAVE  # up to 2 ** 16 ms; a span past either end is counted in the bin at it
AHEAD = 1           # the buckets behind the newest left unsettled for a span of a thread that says nothing of when it rests
SETTLES_BY = 8.0    # s behind the newest at which a bucket is settled whatever is still out, so no history drops one unjudged

_RAN = {RUN, STEP, FOLD, DECODE, SEEK}
_FILE = {DECODE, SEEK, READ}            # what a served node's file answered, its reader's cache not holding the row
_READS = _FILE | {CACHE}                # the kinds whose wall above CPU is a decoder's own threads at work and no wait


@dataclass
class Bucket:
    """One slice of wall time. A view's buckets are the ledger's own until it next writes one, which
    it copies first, so a reader holds them and never writes them."""
    ms: dict = field(default_factory=dict)          # thread -> {node: ms}, exclusive of the runs a run opened
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
    calls: dict = field(default_factory=dict)       # a key of `turns` -> the spans of it that began in the bucket
    own: dict = field(default_factory=dict)         # thread -> {name: ms}: a reader's own work there, the dump's writer and the ledger's bookkeeping, apart from `ms`
    begins: dict = field(default_factory=dict)      # lane -> {what began a walk of it, one of stream.BEGUN_BY: the walks so begun in the bucket}; a begin that says none is not in it
    longest: dict = field(default_factory=dict)     # node -> [ms, CPU ms, its start] of its longest span of LONG ms or more that ended in the bucket, of the kinds that are no read
    shared: bool = field(default=False, compare=False, repr=False)

    def copy(self):
        return Bucket({t: dict(d) for t, d in self.ms.items()}, dict(self.rows), self.unprobed, dict(self.stores),
                      dict(self.recomputed), dict(self.seeks), self.late, dict(self.turns), self.wait, self.read_wait, self.machine, dict(self.calls),
                      {t: dict(d) for t, d in self.own.items()}, {lane: dict(d) for lane, d in self.begins.items()},
                      {n: list(v) for n, v in self.longest.items()})


_EMPTY = Bucket(shared=True)


class Under(NamedTuple):
    """What a node's spans ran under: their kind and the demand they answered."""
    kind: str
    demand: str | None
    asked: str | None       # the node the demand named


class Total(NamedTuple):
    """What a node's spans under one Under came to."""
    count: int
    ms: float
    bytes: int


class WalkId(NamedTuple):
    """Which walk a record is: a lane begins one at a time. Made by Walk.id alone."""
    lane: str | None
    t0: float


class StillOut(NamedTuple):
    """A node's span a thread had not left as it was last sampled, by stream.Emitter.still_out."""
    node: str
    since: float            # its start, on the probe's clock
    ms: float               # as an Event's, exclusive of the spans that ended inside it, as far as `at`
    cpu_ms: float | None    # the thread's CPU over the same; None where the sampler could not read it
    at: float               # when it was sampled


_NONE = Total(0, 0.0, 0)


@dataclass
class Node:
    """One node over one walk. A row counts once, by the most that happened to the node on it: its
    served file answered, else it ran, else a store held it. A progress of several rows counts the
    rows its spans since the last were of, each once, then its hits, which name no row, over the rows left."""
    runs: dict = field(default_factory=dict)        # Under -> Total
    ran: int = 0
    held: int = 0
    served: int = 0
    parts: list = field(default_factory=lambda: [0.0] * PARTS)     # ms in order along the range, each span's where its own row is, of every span but a "cache": a row its reader's cache held is no cost of the node's there
    counts: list = field(default_factory=lambda: [0] * PARTS)      # the spans those ms were of
    bins: dict = field(default_factory=dict)        # kind -> the spans of it counted by their ms, BINS bins; see quantile()
    shape: list | None = None                       # of its output, as the last span that carried one had it

    def copy(self):
        return Node(dict(self.runs), self.ran, self.held, self.served, list(self.parts),
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

    @property
    def id(self):
        return WalkId(self.lane, self.t0)

    def copy(self):
        return replace(self, nodes={n: v.copy() for n, v in self.nodes.items()}, recomputed=dict(self.recomputed),
                       recomputed_ms=dict(self.recomputed_ms), selected=list(self.selected))


@dataclass
class View:
    """What a reader is handed, its own to hold while the stream continues. Bucket `i` of `buckets`
    covers [(first + i) * width, (first + i + 1) * width) seconds on the probe's clock, with none
    missing between the first and the last; `walks` is oldest first, the last of each lane perhaps
    still walking. `settled` is the index on the probe's clock of the last bucket no span still out
    and shorter than ledger.SETTLES_BY can write, None before there is one, and `found` what the ledger's `watch` had made of the
    stream by then, None with none. `now` is the latest time anything in the stream was of, None
    of a view no stream made, and `no_row_since` says of each lane being walked short of its range,
    by a thread that says when it rests and is not at rest, since when it has finished no row with
    no turn of another lane's taken: a lane waiting behind the one its thread is walking is not in it,
    and `walked_by` names the thread of each that is. `still_out` is, by thread, the StillOut of each
    a "still_out" sample last found in a node's span, until the stream says the span has ended, and
    `since_row` is, of each lane of `no_row_since`, {node: the seconds its spans no other opened
    have taken, whole, since the lane last began or finished a row}."""
    width: float
    first: int
    buckets: list
    walks: list
    settled: int | None = field(default=None, compare=False)
    found: object = field(default=None, compare=False)
    now: float | None = field(default=None, compare=False)
    no_row_since: dict = field(default_factory=dict, compare=False)
    walked_by: dict = field(default_factory=dict, compare=False)
    still_out: dict = field(default_factory=dict, compare=False)
    since_row: dict = field(default_factory=dict, compare=False)


class _Lane:
    def __init__(self):
        self.walk = None
        self.kinds = {}         # node -> {kind: the rows its spans were of} since the lane's last progress
        self.spans = {}         # node -> the seconds its spans no other opened took, whole, since the lane's last progress or begin
        self.t = None           # the lane's last progress or begin
        self.at = 0.0           # its thread's ms accounted for then
        self.thread = None      # the thread that said so
        self.synced = False     # a sync landed since the walk began


class Ledger:
    """`width` is a bucket's seconds, `history` the buckets kept, `walks` the records kept, a
    lane's walk under way never dropped for another's, and `discards` how many discarded (key, row) are remembered for telling a recomputation. `event` and
    `sample` may be called from any thread and never wait or raise, an event the bookkeeping fails on there being said on stderr and not kept, where `view()` raises; a sample other than "late", "machine" and "still_out" is not kept.
    `timed()` gives the context a thread that queues folds inside, for whoever attached the ledger to
    time its bookkeeping there, the ledger holding no Emitter to emit a span through.

    A bucket is settled once no span that began in or before it can still be out: behind the last
    time each thread that says when it rests was under no span, a "rest", a "wake", a "progress", a
    "begin" or the end of a span no other opened, and resting it holds nothing back; behind the
    last lateness sampled, which the GUI thread's loop gives between its turns; and AHEAD behind
    the newest for a thread that says neither. A bucket SETTLES_BY seconds behind the newest is
    settled whatever is still out, and before the history drops any, so a span longer than that is
    written into buckets already settled. `watch`, when given, is told as the stream is folded
    and in its order: `settled(view, i)` each time the last settled bucket moves on, to `i`, and
    `clock(view)` each time the stream's latest time enters another bucket's width, settled or not,
    each with a view that is the ledger's own and not to be kept. It gives `back(width)`, the buckets behind
    one it reads, which the history is never shorter than with SETTLES_BY's beside them, `final(id)`, whether it is done with a
    walk, before which the walk is not dropped, and `copy()`, what a view carries as its `found`. A
    watch that raises in any but `back` is said once on stderr and told nothing more, neither `event` nor `view()` raising for it."""

    def __init__(self, width=0.25, history=2400, walks=64, discards=1 << 17, timed=nullcontext, watch=None):
        self.width, self._discards, self._timed, self._kept, self._watch = width, discards, timed, walks, watch
        self._age = max(math.ceil(SETTLES_BY / width), AHEAD + 1)
        self.history = history if watch is None else max(history, watch.back(width) + self._age)
        self._clear, self._resting, self._loop, self._settled = {}, set(), None, None   # thread -> when it last had no span out; those at rest; the last lateness's t
        self._now, self._told = None, None      # the latest time anything folded was of, and the bucket's index `watch` was last told the clock at
        self._last = {}                 # a thread that says when it rests -> {lane: when it last said anything in it}
        self._out = {}                  # thread -> StillOut, of the last "still_out" sample
        self._q = deque()
        self._lock = threading.Lock()   # held to fold and to take a view; an emitter that finds it taken leaves the folding
        self._buckets, self._newest = {}, None
        self._first = None              # the lowest index of `_buckets`, or None where it is to be read off them again
        self._walks = deque()
        self._lanes = {}
        self._plan = self._keys = self._selected = None
        self._nest = {}                 # thread -> [(start, end)] of the spans whose opening run has not emitted yet
        self._spent = {}                # thread -> ms accounted for: every span's, and the unprobed time given out
        self._gone = {}                 # (key, row) a store discarded -> the store

    def event(self, ev):
        self._queue(ev)

    def sample(self, name, value, t):
        self._queue((name, value, t))

    def _queue(self, item):
        self._q.append(item)
        if len(self._q) > BACKLOG and self._lock.acquire(blocking=False):
            try:
                with self._timed():
                    self._fold()
            except Exception:       # the emitter is a tool's run or a slot: the ledger's fault is not its failure
                print(f"SIEVE {time.strftime('%H:%M:%S')}: ledger: an event was not kept\n{traceback.format_exc()}", file=sys.stderr)
            finally:
                self._lock.release()

    def view(self):
        with self._lock:
            self._fold()
            return self._view(True)

    def end(self):
        """The stream has ended: what is folded is settled, to the newest bucket, and `watch` is told so."""
        with self._lock:
            self._fold()
            if self._watch is not None and self._newest is not None:
                self._settled = self._newest
                self._tell("settled", self._view(False), None)

    def _tell(self, said, *args):
        """What the watch's `said` gives of `args`. A watch that raises is said once on stderr and
        told nothing more: None is given, and no view carries a `found` from then on."""
        try:
            return getattr(self._watch, said)(*args)
        except Exception:
            print(f"SIEVE {time.strftime('%H:%M:%S')}: ledger: its watch, a {type(self._watch).__name__}, raised in {said} and is told "
                  f"nothing more\n{traceback.format_exc()}", file=sys.stderr)
            self._watch = None

    def _view(self, kept):
        """The View now; `kept`, one a reader may hold, and else the ledger's own records for `watch` to read and leave."""
        walking = {id(lane.walk) for lane in self._lanes.values()}
        walks = [w.copy() if kept and id(w) in walking else w for w in self._walks]
        found = self._tell("copy") if kept and self._watch is not None else None
        since, by = self._no_row_since()
        spent = {name: dict(self._lanes[name].spans) for name in since}
        if self._newest is None:
            return View(self.width, 0, [], walks, self._settled, found, self._now, since, by, dict(self._out), spent)
        first = self._lowest()
        buckets = [self._buckets.get(i, _EMPTY) for i in range(first, self._newest + 1)]
        if kept:
            for b in buckets:
                b.shared = True
        return View(self.width, first, buckets, walks, self._settled, found, self._now, since, by, dict(self._out), spent)

    def _no_row_since(self):
        """(View.no_row_since, View.walked_by): of the lanes a thread has short of their ranges the one that last began
        or finished a row is the one it is walking, the ladder giving a turn to no lane behind another."""
        walking = {}
        for name, lane in self._lanes.items():
            w = lane.walk
            if (w is not None and w.done < w.length and lane.t is not None and lane.thread in self._clear
                    and lane.thread not in self._resting and lane.t >= walking.get(lane.thread, (lane.t,))[0]):
                walking[lane.thread] = lane.t, name
        return ({name: max([t, *(at for other, at in self._last.get(thread, {}).items() if other != name)])
                 for thread, (t, name) in walking.items()}, {name: thread for thread, (t, name) in walking.items()})

    def _settle(self, newest=None):
        """Moves the last settled bucket on to where the stream now puts it and tells `watch`;
        `newest` given, to where a newest bucket of that index is about to put it."""
        if self._newest is None:
            return
        w = self.width
        s = (self._newest if newest is None else newest) - self._age
        if newest is None:
            s = max(s, min([self._newest - 1 - AHEAD, *(int(t // w) - 1 for thread, t in self._clear.items() if thread not in self._resting),
                            *(() if self._loop is None else (int(self._loop // w) - 1,))]))
        if s >= self._lowest() and (self._settled is None or s > self._settled):
            self._settled = s
            if self._watch is not None:
                self._tell("settled", self._view(False), s)

    def _fold(self):
        q = self._q
        while q:
            item = q.popleft()
            at = item[2] if isinstance(item, tuple) else item.t + item.ms / 1000
            if isinstance(item, tuple):
                name, value, t = item
                if name == "still_out":
                    self._out = {thread: StillOut(*span, t) for thread, span in value.items()}
                elif name in ("late", "machine") and (b := self._bucket(int(t // self.width))) is not None:
                    if name == "late":
                        b.late = max(b.late, value)
                        self._loop = t if self._loop is None else max(self._loop, t)
                    else:
                        b.machine = value
            elif item.kind in (REST, WAKE):
                self._clear[item.thread] = item.t
                (self._resting.add if item.kind == REST else self._resting.discard)(item.thread)
                self._bucket(int(item.t // self.width))
            elif item.kind == PROGRESS:
                self._progress(item)
                self._said(item.thread, item.t)
            elif item.kind == BEGIN:
                self._said(item.thread, item.t)
                self._begin(item, item.row)
                by = (item.facts or {}).get("by")
                if by is not None and (b := self._bucket(int(item.t // self.width))) is not None:
                    began = b.begins.setdefault(item.lane, {})
                    began[by] = began.get(by, 0) + 1
            elif item.kind == SYNC:
                self._plan, self._keys = _plan(item.facts, "a sync's facts"), item.keys
                self._selected = (item.facts or {}).get("selected")
                for lane in self._lanes.values():
                    lane.synced = True
            elif item.kind == WATCH:
                self._selected = item.node
                for w in (lane.walk for lane in self._lanes.values()):
                    if w is not None and w.done < w.length and item.node is not None and item.node not in w.selected:
                        w.selected.append(item.node)
            elif item.kind in (EVICT, UNCACHE):
                self._gone[(item.key, item.row)] = "memo" if item.kind == EVICT else item.key
                if len(self._gone) > self._discards:
                    del self._gone[next(iter(self._gone))]
            elif item.kind in TURNS:
                name = f"{item.kind} {item.node}"
                for i, (bucket, share) in enumerate(self._over(item.t, item.t + item.ms / 1000)):
                    bucket.turns[name] = bucket.turns.get(name, 0.0) + item.ms * share
                    if not i:
                        bucket.calls[name] = bucket.calls.get(name, 0) + 1
            elif item.kind in OWN:      # in the buckets under its thread and accounted for there, and in no walk
                name = item.kind if item.node in (None, item.kind) else f"{item.kind} {item.node}"
                for bucket, share in self._over(item.t, item.t + item.ms / 1000):
                    ms = bucket.own.setdefault(item.thread, {})
                    ms[name] = ms.get(name, 0.0) + item.ms * share
                self._spent[item.thread] = self._spent.get(item.thread, 0.0) + item.ms
            elif item.kind in NODES:
                at = self._span(item)
            if not isinstance(item, tuple) and item.thread in self._clear:
                last = self._last.setdefault(item.thread, {})
                last[item.lane] = max(last.get(item.lane, at), at)
            if (not isinstance(item, tuple) and item.thread in self._out
                    and (item.t <= self._out[item.thread].since or item.kind in (REST, WAKE, PROGRESS, BEGIN))):
                del self._out[item.thread]      # the span has ended, or one around it, or the thread is between spans; one that ended inside it says nothing of it
            self._now = at if self._now is None else max(self._now, at)
            self._settle()
            if self._watch is not None and (i := int(self._now // self.width)) != self._told:
                self._told = i
                self._tell("clock", self._view(False))

    def _bucket(self, i):
        """Bucket `i` to write into, or None for one older than the history."""
        if self._newest is None or i > self._newest:
            self._settle(i)     # while every ledger still holds what a class reads behind the buckets it settles
            self._newest = i
            for old in [k for k in self._buckets if k <= i - self.history]:
                del self._buckets[old]
                self._first = None
        elif i <= self._newest - self.history:
            return None
        b = self._buckets.get(i)
        if b is None or b.shared:
            if b is None and self._first is not None and i < self._first:
                self._first = i
            b = self._buckets[i] = Bucket() if b is None else b.copy()
        return b

    def _lowest(self):
        if self._first is None:
            self._first = min(self._buckets)
        return self._first

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
        if at is not None:
            del self._walks[at]
        self._walks.append(lane.walk)
        if len(self._walks) > self._kept:
            walking = {id(x.walk) for x in self._lanes.values()}
            for i, w in enumerate(self._walks):
                if id(w) not in walking and (self._watch is None or not w.done or self._tell("final", w.id) or self._watch is None):
                    del self._walks[i]
                    break
        self._bucket(int(ev.t // self.width))   # so a walk in a view began before the view's first bucket only when the history has dropped its beginning
        lane.kinds, lane.spans, lane.synced = {}, {}, False
        lane.t, lane.at, lane.thread = ev.t, self._spent.get(ev.thread, 0.0), ev.thread
        return lane

    def _said(self, thread, t):
        """`thread` was under no span at `t`, which counts of one that says when it rests."""
        if thread in self._clear:
            self._clear[thread] = max(self._clear[thread], t)
            self._resting.discard(thread)

    def _span(self, ev):
        """Keeps a node's span and returns when it ended."""
        # By the rule beside stream.Event, the nest holds only what a run still to emit will take.
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
        if ev.ms >= LONG and not reads and (b := self._bucket(int(end // self.width))) is not None and ev.ms > b.longest.get(ev.node, (0.0,))[0]:
            b.longest[ev.node] = [ev.ms, ev.cpu_ms, ev.t]
        if ev.reader is None:
            self._said(ev.thread, end)
        lane = self._lanes.get(ev.lane)
        if ev.reader is None and lane is not None:
            lane.spans[ev.node] = lane.spans.get(ev.node, 0.0) + end - ev.t
        walk = None if lane is None else lane.walk
        store = self._gone.pop((ev.key, ev.row), None) if ev.kind in _RAN else None
        if (store is not None or ev.kind == SEEK) and (b := self._bucket(int(ev.t // self.width))) is not None:
            if store is not None:
                b.recomputed[store] = b.recomputed.get(store, 0) + 1
            if ev.kind == SEEK:
                b.seeks[ev.node] = b.seeks.get(ev.node, 0) + 1
        if walk is None:
            return end
        if store is not None:
            walk.recomputed[store] = walk.recomputed.get(store, 0) + 1
            walk.recomputed_ms[store] = walk.recomputed_ms.get(store, 0.0) + ev.ms
        if lane.synced and ev.kind != CANCEL:     # a cancelled run was the old plan's
            walk.replanned = True
        if reads:
            walk.read_wait += off
        else:
            walk.wait += off
        node = walk.nodes.setdefault(ev.node, Node())
        under = Under(ev.kind, ev.demand, ev.asked)
        was = node.runs.get(under, _NONE)
        node.runs[under] = Total(was.count + 1, was.ms + ev.ms, was.bytes + ev.bytes)
        if ev.kind != CACHE:
            # by the span's row and not the rows told done, which stand still between two progresses
            at = walk.done if walk.start is None or ev.row is None else ev.row - walk.start
            part = min(PARTS - 1, max(0, at * PARTS // max(walk.length, 1)))
            node.parts[part] += ev.ms
            node.counts[part] += 1
        bins = node.bins.get(ev.kind)
        if bins is None:
            bins = node.bins[ev.kind] = [0] * BINS
        bins[min(BINS - 1, max(0, int(math.log2(ev.ms / FINEST) * OCTAVE))) if ev.ms > 0 else 0] += 1
        if ev.shape is not None:
            node.shape = list(ev.shape)
        lane.kinds.setdefault(ev.node, {}).setdefault(ev.kind, set()).add(ev.row)
        return end

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
        lane.t, lane.at, lane.thread = ev.t, spent, ev.thread
        rows = ev.row - walk.done
        walk.done, walk.length, walk.t1 = ev.row, ev.length, ev.t
        walk.replanned = walk.replanned or lane.synced
        b = self._bucket(int(ev.t // self.width))
        if b is not None:
            if rows:
                b.rows[ev.lane] = b.rows.get(ev.lane, 0) + rows
            told = {"memo": facts.get("memo"), **facts.get("caches", {}), f"{ev.lane or 'walk'} stack": facts.get("stack")}
            b.stores = stores_after(b.stores, {store: (s["bytes"], s["limit"]) for store, s in told.items() if s is not None})
        if rows:
            served = {n for n, f in ((walk.plan or {}).get("nodes") or {}).items() if f["served"]}
            hits, folds = facts.get("hits", {}), facts.get("fold_hits", {})
            for nid in lane.kinds.keys() | hits.keys() | folds.keys():
                kinds, node = lane.kinds.get(nid, {}), walk.nodes.setdefault(nid, Node())
                file = _FILE if nid in served else {READ}
                answered = set().union(*(at for k, at in kinds.items() if k in file))
                ran = set().union(*(at for k, at in kinds.items() if k in _RAN and k not in file)) - answered
                left = rows
                for name, n in (("served", len(answered)), ("ran", len(ran)),
                                ("held", len(kinds.get(CACHE, set()) - answered - ran) + hits.get(nid, 0) + folds.get(nid, 0))):
                    n = min(n, left)
                    setattr(node, name, getattr(node, name) + n)
                    left -= n
        lane.kinds, lane.spans = {}, {}


def stores_after(held, told):
    """`held`, a bucket's `stores`, with a later telling `told` over it. A telling of the memo or a
    cache is of every one there then is, so one of `held` it leaves out is gone; a lane's stack is
    told by that lane alone and stays until it is told again."""
    if any(not s.endswith(" stack") for s in told):
        held = {s: v for s, v in held.items() if s.endswith(" stack")}
    return {**held, **told}


def coarsen(view, k):
    """`view` with its buckets merged `k` at a time on the probe's clock, each the reading a bucket
    `k` widths wide would have held: what is summed summed, the lateness the worst and a node's longest span the longest, the stores by
    `stores_after` and the machine as the last bucket that had one found it. The walks are the view's own."""
    if k <= 1:
        return view
    first, out = view.first // k, []
    for i, b in enumerate(view.buckets, view.first):
        if i // k - first == len(out):
            out.append(Bucket())
        if b is _EMPTY:
            continue
        m = out[-1]
        for name in ("ms", "own", "begins"):
            for thread, d in getattr(b, name).items():
                ms = getattr(m, name).setdefault(thread, {})
                for n, v in d.items():
                    ms[n] = ms.get(n, 0) + v
        for name in ("rows", "recomputed", "seeks", "turns", "calls"):
            d = getattr(m, name)
            for key, v in getattr(b, name).items():
                d[key] = d.get(key, 0) + v
        m.stores = stores_after(m.stores, b.stores)
        m.machine = b.machine or m.machine
        for n, v in b.longest.items():
            if v[0] > m.longest.get(n, (0.0,))[0]:
                m.longest[n] = list(v)
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
           "buckets": [plain(b, {"rows": list(b.rows.items()), "begins": list(b.begins.items())}) for b in view.buckets],   # a lane may be None, which is no JSON key
           "walks": [plain(w, {"nodes": {n: plain(x, {"runs": [u._asdict() | r._asdict() for u, r in x.runs.items()]})
                                         for n, x in w.nodes.items()}}) for w in view.walks]}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f)


def _record(d, names, where):
    """`d` when it is a dict of exactly `names`, as `save` writes a record and the stream a sync's
    facts; else ValueError naming `where` it was read."""
    if not isinstance(d, dict) or set(d) != set(names):
        raise ValueError(f"{where} is of another shape than this ledger reads: "
                         f"{sorted(d) if isinstance(d, dict) else type(d).__name__} where {sorted(names)} is written")
    return d


def _plan(facts, where):
    """`facts` when it is None or a sync's as stream.PLAN_FACTS and NODE_FACTS name them, so what
    reads a walk's plan reads a field that is there; else ValueError naming `where`."""
    if facts is not None:
        for node in _record(facts, PLAN_FACTS, where)["nodes"].values():
            _record(node, NODE_FACTS, where)
    return facts


def saved(path):
    """(a Ledger holding the buckets and walks `save` wrote to `path`, every walk closed, and the
    `more` written beside them). A history is of the session that wrote it: one holding a record
    whose fields are not this ledger's raises ValueError."""
    with open(path, encoding="utf-8") as f:
        d = _record(json.load(f), ("width", "first", "more", "buckets", "walks"), path)
    of = {cls: [f.name for f in fields(cls) if f.name != "shared"] for cls in (Bucket, Walk, Node)}
    ledger = Ledger(width=d["width"], history=max(len(d["buckets"]), 1), walks=max(len(d["walks"]), 1))
    for i, b in enumerate(d["buckets"], d["first"]):
        ledger._buckets[i] = Bucket(**_record(b, of[Bucket], path) | {"rows": {lane: n for lane, n in b["rows"]}, "begins": {lane: by for lane, by in b["begins"]},
                                                                      "stores": {k: tuple(v) for k, v in b["stores"].items()}})
        ledger._newest = i
    for w in d["walks"]:
        nodes = {}
        for n, x in _record(w, of[Walk], path)["nodes"].items():
            runs = [_record(r, Under._fields + Total._fields, path) for r in _record(x, of[Node], path)["runs"]]
            nodes[n] = Node(**x | {"runs": {Under(*(r[f] for f in Under._fields)): Total(*(r[f] for f in Total._fields)) for r in runs}})
        ledger._walks.append(Walk(**w | {"nodes": nodes, "plan": _plan(w["plan"], path)}))
    return ledger, d["more"]
