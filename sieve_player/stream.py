"""The stream: the Event every reader is handed, the kinds one may be, and the Emitter that builds
each and hands it to `on_event`. It imports nothing of sieve_player, so a reader of a dump loads no
graph; what a graph says into it is Graph's to call, and what no node ran, a thread's turn or the
player's selection, is said here by whoever holds the Emitter.
"""
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass

TURNS = ("slot", "paint")       # the GUI thread's spans of Emitter.turn, a thread's own time under no node
OWN = ("dump", "monitor")       # a consumer's own work: the dump's writer, and the ledger's bookkeeping on a thread that emits
SPANS = ("run", "step", "fold", "error", "cancel", "cache", "decode", "seek", "read", *OWN, *TURNS)    # the kinds with a duration; the rest are instants


@dataclass(frozen=True, slots=True)
class Event:
    """What the probe emits, one per run, read or boundary; see Emitter.probe(). Every field is
    required, so a consumer building or reading one by position, or one missing a field, fails
    where it stands instead of misreading its neighbour."""
    node: str | None    # the node that ran, or read; None on a boundary; on a "slot", "paint" or "monitor" what turn() was told, no node; on a "watch" the selection
    row: int | None
    key: str | None     # the node's raw key, what the memo holds under
    kind: str           # "run" | "step" | "fold" | "error" | "cancel" | "cache" | "decode" | "seek" | "read" | "sync" | "watch" | "evict" | "uncache" | "begin" | "progress" | "dump" | "monitor" | "slot" | "paint"
    bytes: int          # the result's; what an eviction freed
    ms: float           # wall, exclusive of the runs this one opened
    t: float            # start, on the probe's clock (perf_counter); orders events across threads
    thread: str         # the emitting thread's name
    cpu_ms: float       # the thread's CPU time over the same span, exclusive likewise; wall far above it is a wait. On
                        # Windows thread_time ticks at the scheduler quantum (~16 ms), so one event's is 0 or a tick and
                        # only a sum over many events is a figure
    serves: str | None  # "scrub" | "walk" | "bake": what the worker was doing; None off the worker (bench, tests)
    length: int | None  # progress and begin: rows in the lane's range, `row` being the rows done, or on a begin the range's first
    keys: dict | None   # sync only: every node's key under the new plan, band included; diff two to see what a drag changed
    reader: str | None  # the node whose read opened this run or read; None for one no node's read opened
    demand: str | None  # "walk" | "fold" | "display" | "bake": what asked at the top for everything under it; see Emitter.demand()
    asked: str | None   # the node the demand named: the walked or chain node, the folded one, the shown or overlaid, a bake's input
    lane: str | None    # "window" | "clip" | "scrub" | "bake": the worker's range the row belonged to; None off the worker
    facts: dict | None  # sync: the plan begun and the selection, see plan.facts() and Emitter.sync(); progress: the lane's memo hits and the stores, see Graph.progress()
    shape: tuple | None # of what a span read or made: a decode's or a read's frame, a run's result, a fold's plane; None for what has none


class Emitter:
    """Builds each Event and hands it to `on_event`, the stream's one consumer, None while there is
    none, and keeps on each thread what it stamps one with: the spans open there, the demand, what
    the thread serves and its lane. A Graph is handed one and emits through it; any thread may call."""

    def __init__(self):
        self.on_event = None
        self.watched = None                 # the node the player shows beside the pinned; see watch()
        self._thread = threading.local()    # the spans open on this thread, so a span's time excludes those it opened; its demand, serves and lane

    @property
    def lane(self):
        """The lane this thread last said it serves, or None."""
        return getattr(self._thread, "lane", None)

    def emit(self, kind, nid, row, key, nbytes, ms=0.0, t=None, cpu_ms=0.0, length=None, keys=None, reader=None, facts=None, shape=None):
        """One Event to `on_event`, stamped here with what every event carries: its start, the
        thread, and what the thread says it is serving, the demand open on it and its lane. The probe
        passes the times it measured; a boundary or an eviction has none and is stamped now."""
        if self.on_event is not None:
            p = self._thread
            demand, asked = getattr(p, "demand", (None, None))
            self.on_event(Event(nid, row, key, kind, nbytes, ms, time.perf_counter() if t is None else t,
                                threading.current_thread().name, cpu_ms, getattr(p, "serves", None), length, keys,
                                reader, demand, asked, getattr(p, "lane", None), facts, shape))

    def sync(self, keys, facts):
        """A "sync" event, a boundary with no node, row or time: what runs next ran under a new plan,
        whose `keys` and `facts` it carries, with "selected", the watched node, among the facts."""
        self.emit("sync", None, None, None, 0, keys=keys, facts={**facts, "selected": self.watched})

    def watch(self, nid):
        """`nid`, or None, is the node the player now shows beside the document's pinned: a "watch"
        event naming it, and "selected" in every sync's facts from here on. Nothing is computed for
        it; a reader of the stream takes a fold of it for work something shown asked for."""
        if nid != self.watched:
            self.watched = nid
            self.emit("watch", nid, None, None, 0)

    def serving(self, what, lane=None):
        """What the events this thread emits from here on served, "scrub", "walk" or "bake", and the
        lane they are in; the worker says before each job's turn, since only it knows, and nothing
        else sets it."""
        self._thread.serves, self._thread.lane = what, lane

    @contextmanager
    def demand(self, what, nid):
        """Names what this thread's events answer while the body runs: `what`, "walk", "fold",
        "display" or "bake", asked of `nid`. The graph's entries open their own; the worker opens one
        around a chain node's probe, which is under no entry of the graph's."""
        p = self._thread
        held, p.demand = getattr(p, "demand", (None, None)), (what, nid)
        try:
            yield
        finally:
            p.demand = held

    @contextmanager
    def probe(self, nid, row, key, reader=None, cancel=()):
        """Times the run inside and hands `on_event` one Event, its ms wall time exclusive of the
        runs it opened in turn, so a cold row charges the decode to the video node and each tool its
        own work, `reader` being the node whose read opened it. The body sets `kind`, `bytes` and the shape on the yielded
        list, what only the call site knows: a tool's kind is "run", or "step" for one row of a
        series tool the walk steps, since a memo hit is not a run
        and emits nothing, counted instead into the next progress event; the video read's is "cache", "decode" or "seek", read off the decoder's
        counters; a body that raises emits "error", or "cancel" for an exception of `cancel`, a class or a tuple of them, with the time it took and
        no bytes, so a reader tells a failed run from one that returned. Nothing when `on_event` is unset. `Graph.sync()` emits a "sync" event into the same
        stream, a boundary with no node, row or time, and the memo and decoder cache emit "evict"
        and "uncache" with the bytes freed. The worker wraps a series tool's run in this; `Graph._compute`
        wraps a frame tool's and the video node's read."""
        if self.on_event is None:
            yield [None, 0, None]
            return
        stack = self._thread.__dict__.setdefault("stack", [])
        stack.append([0.0, 0.0])             # wall and CPU the runs opened inside this one took
        ev = ["run", 0, None]
        t, c = time.perf_counter(), time.thread_time()
        try:
            yield ev
        except BaseException as exc:
            # cancelled: the graph moved on under the run, not the tool's fault; else the body raised, a tool failed or the read ran off the stream's end
            ev[0] = "cancel" if isinstance(exc, cancel) else "error"
            raise
        finally:
            total, cpu = time.perf_counter() - t, time.thread_time() - c
            inner, inner_cpu = stack.pop()
            if stack:
                stack[-1][0] += total
                stack[-1][1] += cpu
            self.emit(ev[0], nid, row, key, ev[1], (total - inner) * 1000, t, (cpu - inner_cpu) * 1000, reader=reader, shape=ev[2])

    @contextmanager
    def turn(self, kind, name):
        """Times the body as a span of this thread's that no node ran and hands `on_event` one Event
        of `kind` with `name` as its node, its ms exclusive of the turns opened inside it: the
        window's are "slot", a worker signal's slot named by the signal, and "paint", named by the
        part that painted; the monitor's poll and paint are a "slot" and a "paint" named "monitor",
        and "monitor" is its ledger's bookkeeping on a thread that emits. Emitted whether or not the body raises; nothing when `on_event` is unset."""
        if self.on_event is None:
            yield
            return
        stack = self._thread.__dict__.setdefault("stack", [])
        stack.append([0.0, 0.0])
        t, c = time.perf_counter(), time.thread_time()
        try:
            yield
        finally:
            total, cpu = time.perf_counter() - t, time.thread_time() - c
            inner, inner_cpu = stack.pop()
            if stack:
                stack[-1][0] += total
                stack[-1][1] += cpu
            self.emit(kind, name, None, None, 0, (total - inner) * 1000, t, (cpu - inner_cpu) * 1000)
