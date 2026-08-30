"""The dispatcher, re-entrant: it calls consumers back instead of being polled.

Same name and same job as `orchestrator-experiments/explorer.py`'s
`Dispatcher` — the one thing that owns threads and decodes — and the finding
about it (`2026.08.30-the-pressure-dispatcher-preempts-into-seeks`) is about
this class's ancestor. What changes is not what it is. What changes is which
direction the question travels.

In V1 a consumer declared a need and then asked, over and over, whether the
answer had arrived: `ToolRunner` slept 5 ms in a loop against a ten-second
deadline, the dispatcher slept 4 ms when nothing was pickable, and the Qt
thread spun at 2 ms for an exact frame. Three loops asking one question that
the thing doing the decoding already knew the answer to.

VapourSynth never asks it. A filter there implements
`GetFrame(n, activationReason, frameCtx)`. On `arInitial` it calls
`requestFrameFilter` for each input it needs and returns *without computing*;
the core produces those frames on its own threads, and re-enters the same
call with `arAllFramesReady` once they are resident, at which point
`getFrameFilter` cannot miss. A filter never waits, because a filter is never
running at a moment when it would have to.

That is the whole apparatus here, with VapourSynth's word used wherever this
tree has none — `Reason.INITIAL` and `Reason.ALL_FRAMES_READY`, `request`,
`get`, and the filter modes — and this tree's word used wherever it has one.
It is deliberately *not* called a core: `gui/frame/panes.py` already spends
that word on the centre region a subpane strip attaches to, and a scheduler
named for a pane's middle is a homonym nobody asked for. `request_frame` and
`getFrameFilter` lose the word `frame` for the reason the next section gives:
in this tree the thing requested is often not one.

**Two roles, and the split is not a tuning choice.** One thread fetches and
only fetches; `fetch.Fetcher` is one open container with one cursor and is
not thread-safe by construction, and the seek/step rule is a statement about
a cursor's history. N threads run activations and never decode. If a decode
ran on a recorder thread the cursor would be shared, and if arithmetic ran on
the fetch thread then a step costing tens of milliseconds would stall the
decode that the whole pressure queue is about — which is the freeze the
session explorer exists to avoid, re-introduced at the other end.

**Nothing has an interval.** The fetch thread blocks on a condition the graph
notifies when a declaration arrives; the recorder threads block on a
condition this class notifies when a key lands in the pool. `blocked` counts
waits where V1's `idle_polls` counted naps, and the two are not the same
measurement — one is how often there was nothing to do, the other is how
often we checked. That difference is the countable half of README question 1.

**Lock order is not a rule here, because there is no order to keep.** The
graph fires its listeners after dropping its own lock and the pool fires
after dropping its own, so no thread ever holds one of those while reaching
for this one. `_arm` declares into the graph *before* taking `_lock` for the
same reason. If any of the three ever fires a listener under its lock, this
comment is the thing that stopped being true.

**What the pipeline mints and what this calls.** The activation callable is
built where the facts about a node live — for a step, that is everything
`sieve/pipeline/binding.py` already synthesises: the demand, the sink, the
hold, the arithmetic. This class supplies the thread and the moment, and
knows about none of it. `nodes.py` is where the experiment's callables are
built; a `Bound` growing a `recorder(node)` is the shape that belongs in the
tree, and this folder is not the place it lands.

## Where the port breaks

Two things about SIEVE make the translation partial, and both are load-
bearing rather than cosmetic. An experiment here that forgets either is
measuring VapourSynth.

**The filter is not the tool.** A VapourSynth filter author writes `GetFrame`
and calls `requestFrameFilter` from inside it; the plugin is compiled against
the core and is handed its pointers. A SIEVE tool may not do any of that
(ADR-0009): it declares `wants`, `offsets` and `produces`, supplies `field`
and `reduce`, and never sees a `Request`. So an activation is *synthesised
around* a tool from its declaration — the substrate reads the offsets and
issues the requests — and is never implemented by one.

That is why scheduling facts have to be declared fields rather than method
behaviour. VapourSynth's filter mode is a property the filter announces
because the filter is code the core calls; `Step.sequential` is a field for
the same reason, arrived at from the opposite direction — a tool that cannot
hold a context has no other way to say anything about how it may be run. It
also means a tool cannot be trusted to release, so `Request.release` is
called by the synthesised wrapper and not by the arithmetic.

**A dependency is not always a frame.** VapourSynth has one kind of thing a
filter can ask another for, indexed by `n`. This tree has four —
`contract/edges.py`'s `KINDS` — and the request path here is written for a
key and an opaque payload rather than for a frame, which is why `request`
and `get` lost the word.

What it deliberately does *not* do is enumerate classes of dependency and
schedule each differently. There is one payload kind anything in this tree
actually produces and one key shape, so a taxonomy written now would have
rows with no instance in them, and a later reader would take it for a
decision somebody made rather than a guess nobody tested. `KINDS` is already
the closed set and SIEVE alone extends it, when a real tool presses. An
orchestrator that predicts what future tools will need is ADR-0007's
falsified move — a step could not know its own cost class because that was a
ratio against a fetch it could not see — and ADR-0009's accretion, each
accommodation small and justified and their sum a substrate shaped by the
history of requests.

The one thing about non-frame inputs this tree *has* decided, and which is
therefore safe to rely on: a parameter is not a dependency. A threshold or
the crop the user drew has no row, is not requested, and travels in the
**key** (ADR-0010) — changing one names a different series, which
`sieve/series.py`'s `Sinks` makes a lookup rather than a re-run. Nothing here
should grow a way to request one, and a node that appears to want one is a
node whose key is wrong.

That is also where V1's withdrawn question 6 left a real gap: after a
parameter change every held frame is still correct and every scalar computed
under the old parameters is wrong. The key closes it for values. Whether it
closes it for a held *field* is not established, here or anywhere.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, Callable

import numpy as np

from graph import Envelope, Graph, Need, Urgency
from pool import Pool


class Reason(IntEnum):
    """Why a node is being called. VapourSynth's `activationReason`.

    A node is called exactly twice per activation and does something
    different each time, which is what lets it never block: the first call
    says what it wants and returns, and the second runs with everything it
    asked for already in hand.
    """

    INITIAL = 0            #: say what you need; do not compute; return
    ALL_FRAMES_READY = 1   #: your inputs are resident; compute now


class Mode(Enum):
    """How a node's activations may be scheduled against each other.

    VapourSynth has four filter modes. Two are represented here and two are
    not, and which is which is a claim about this tree rather than an
    omission:

    - `fmParallel` -> PARALLEL. Activations for different rows may run at
      once. Every step in this tree today.
    - `fmFrameState` -> ORDERED. The node carries state across rows, so its
      activations run one at a time and in ascending row order. Nothing in
      this tree is this yet; README question 3 builds the minimal case in
      order to find out whether the flag is load-bearing or has one legal
      value.
    - `fmParallelRequests` is absent because it distinguishes a parallel
      request phase from a serialised compute phase, and the request phase
      here is a list append.
    - `fmUnordered` — serial but any order — is absent because nothing has
      asked for it, and a mode with no instance is the field README question
      3 is about.

    **ORDERED is over everything armed, not over what happens to be ready.**
    An earlier draft ordered only among simultaneously-ready activations,
    which promises nothing: rows land one at a time under a pressure-ranked
    fetch, so each was the only candidate and ran alone. Driven in reverse it
    produced strictly descending rows while claiming to be ordered. The rule
    that means something is that an ORDERED node runs the lowest row it has
    been *armed* for and has not yet run, whatever else has landed.

    **What that costs, stated rather than discovered.** A row armed and never
    served stalls every later row of that node, because the lowest armed row
    never runs. VapourSynth does not have this problem: its core drives the
    request order, so it can promise a stateful filter an unbroken ascending
    run. A dispatcher that ranks by pressure cannot promise both that and a
    GUI served first. The gap is exactly the reset/step/checkpoint protocol
    `tool-experiments/tools.py` names and nothing implements, and it is the
    reason README question 3 is worth asking rather than assuming.
    """

    PARALLEL = "parallel"
    ORDERED = "ordered"


@dataclass
class Request:
    """One node's in-flight ask for one row — VapourSynth's frame context.

    The node's whole interface to the dispatcher, and the reason a node needs
    no reference to the pool, the graph, or a thread. It is handed to
    `activate` on both calls and means different things on each: during
    INITIAL it accepts `request_frame`, and during ALL_FRAMES_READY it
    answers `frame`.
    """

    node_id: str
    #: who holds, in the graph. **Not** `node_id`: `Graph.declare` keys by
    #: the declarer and *replaces*, so two activations of one node declaring
    #: under the same id would release each other's rows and only the last
    #: would be held. V1 never met this because a tool had exactly one row in
    #: flight — the thread was the limit. Here `Pass` runs several, and the
    #: unit that holds is the activation, which is also what ADR-0006 says:
    #: held until released, and it is an activation that releases.
    holder: str
    row: int
    #: the edge identity this activation's requests default to. A form's key
    #: when the edge is pixels, the producing edge's name when it is not —
    #: see "where the port breaks" above. Called `form_key` because that is
    #: what `graph.Need` and `pool` call it, and a third spelling of one
    #: field would be worse than a name that is right most of the time.
    form_key: str
    urgency: Urgency
    activate: Callable[["Reason", "Request"], None]
    dispatcher: "Dispatcher"
    #: (row, form_key) asked for during INITIAL, in the order asked. The
    #: order is the node's and is preserved into the `Need`: a sweep spells
    #: attention-first by rotating its offsets, and `Need.unserved` hands
    #: that order to the fetch thread.
    asked: list[tuple[int, str]] = field(default_factory=list)
    #: called once this activation is finished with, run or cancelled, on
    #: whichever thread finished it. Set before the activation is armed and
    #: never after, because after is a race against it having already run.
    #: `nodes.Pass` advances through it; nothing else needs it.
    then: Callable[[], None] | None = None
    outstanding: int = 0
    cancelled: bool = False
    #: whether the node said it was done with its inputs. A step does; a
    #: viewer deliberately does not, because its declaration is the hold on
    #: the frame it is showing.
    released: bool = False
    t_open: float = 0.0
    t_ready: float = 0.0
    t_done: float = 0.0

    # ── the node's side of the contract ──────────────────────────────────

    def request(self, row: int, form_key: str | None = None) -> None:
        """`requestFrameFilter`, less the assumption that it is a frame.

        Legal only during INITIAL. Says that this activation cannot proceed
        without that row of that edge. It does not fetch, does not block, and
        returns nothing — the whole point is that there is nothing to return
        yet.

        Not named `request_frame`: a step fed another step's field or scalar
        requests one of those the same way, and the only non-positional
        dependency this tree has travels in the key rather than through here.
        """
        self.asked.append((row, form_key or self.form_key))

    def get(self, row: int, form_key: str | None = None) -> Any:
        """`getFrameFilter`. Legal only during ALL_FRAMES_READY.

        Resident by construction: this activation was only re-entered because
        every row it asked for had landed. A miss here is not a cache miss to
        be handled, it is the dispatcher's invariant broken, so it raises
        rather than returning None and letting a node compute over a hole.
        """
        key_form = form_key or self.form_key
        got = self.dispatcher.pool.get(row, key_form, by=self.node_id)
        if got is None:
            raise LookupError(
                f"{self.node_id} was re-entered for row {self.row} but "
                f"({row}, {key_form}) is not resident — the dispatcher "
                f"promised it and the pool does not have it")
        return got

    def release(self) -> None:
        """Done with every row this activation asked for.

        ADR-0006's explicit release, and a node whose output is not
        frame-shaped has no other way to say it: nothing in its own position
        tells the graph it has finished with an input.
        """
        for row, form_key in self.asked:
            self.dispatcher.graph.release_row(self.holder, row, form_key)
        self.released = True

    @property
    def wait_ms(self) -> float:
        """How long this activation waited on its inputs.

        The number that replaces V1's `starved`. There is no deadline to
        exceed here, so a long wait is a fact about the fetch queue rather
        than an abandoned row, and it is reported instead of counted.
        """
        return (self.t_ready - self.t_open) * 1000.0 if self.t_ready else 0.0


def _role(node_id: str) -> str:
    """`tool-dis-140233...` -> `tool`. Ids carry an object id; the counters
    and the duration bars want the role."""
    return node_id.split("-")[0]


class Dispatcher:
    """Owns the threads and the moment; knows nothing about what a node is.

    Constructed with a graph and a pool, and a factory for the decode leaf so
    the fetch thread can own its cursor exclusively.
    """

    def __init__(self, graph: Graph, pool: Pool, form_key: str,
                 fetcher_factory: Callable[[], Any],
                 recorders: int = 2, t0: float = 0.0) -> None:
        self.graph = graph
        self.pool = pool
        self.form_key = form_key
        self._fetcher_factory = fetcher_factory
        self._recorder_count = max(1, recorders)
        self._t0 = t0

        self._lock = threading.Lock()
        #: two predicates, two conditions, one lock. A single condition with
        #: `notify_all` would wake every recorder on every declaration and
        #: every fetch on every landing, which is polling with extra steps.
        self._pickable = threading.Condition(self._lock)
        self._runnable = threading.Condition(self._lock)
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

        #: (row, form_key) -> activations still waiting on it. The dependency
        #: count VapourSynth's core keeps, and what makes a landing O(1) in
        #: the number of waiters rather than a scan of everything pending.
        self._waiting: dict[tuple[int, str], list[Request]] = {}
        self._ready: deque[Request] = deque()
        self._running: set[str] = set()      #: nodes a recorder is inside
        #: for an ORDERED node, every row armed and not yet finished. The
        #: lowest of them is the only one that may run, which is what makes
        #: the ordering a promise about the node rather than about whichever
        #: rows happened to land together.
        self._armed_rows: dict[str, set[int]] = {}
        self._modes: dict[str, Mode] = {}
        self._current: dict[str, Request] = {}
        self._seq = 0

        # ── fetch counters, the same ones V1's Dispatcher kept ───────────
        self.served = 0
        self.seeks = 0
        self.steps = 0
        self.failures = 0
        #: decodes that landed after the node asking had already moved on.
        #: Kept exactly as V1 kept it, `still_wants` and all: it is the price
        #: of per-frame preemption and the walk numbers are read against it.
        self.stale = 0
        #: how many times the fetch thread had nothing to do and slept on a
        #: condition. V1's `idle_polls` counted 4 ms naps; this counts waits.
        #: Comparing the two is comparing an interval to an event.
        self.blocked = 0
        self.blocked_s = 0.0
        self.by_pressure: dict[str, int] = {}
        self.trace: list[tuple] = []
        self.trace_cap = 20_000
        self.last = "idle"

        # ── activation counters, which V1 had no way to keep ─────────────
        self.activations = 0        #: INITIAL calls
        self.reentries = 0          #: ALL_FRAMES_READY calls
        self.immediate = 0          #: ...that needed no fetch at all
        self.superseded = 0         #: cancelled before they were re-entered
        self.wait_ms: list[float] = []
        #: what an activation raised, kept rather than propagated. A recorder
        #: thread that dies stops advancing every pass behind it, and that
        #: reads as a scheduling result rather than as the crash it is.
        self.errors: list[str] = []

        graph.on_change(self._graph_changed)
        pool.on_put(self._landed)

    # ── lifecycle ────────────────────────────────────────────────────────

    def start(self) -> None:
        self._stop.clear()
        self._threads = [
            threading.Thread(target=self._fetch_loop, name="fetch",
                             daemon=True)]
        self._threads += [
            threading.Thread(target=self._record_loop, name=f"record{i}",
                             daemon=True)
            for i in range(self._recorder_count)]
        for thread in self._threads:
            thread.start()

    def stop(self) -> None:
        self._stop.set()
        with self._lock:
            self._pickable.notify_all()
            self._runnable.notify_all()
        for thread in self._threads:
            thread.join(timeout=15)
        self._threads = []

    def running(self) -> bool:
        return any(thread.is_alive() for thread in self._threads)

    def set_mode(self, node_id: str, mode: Mode) -> None:
        """How this node's activations may be scheduled. PARALLEL if unset."""
        with self._lock:
            self._modes[node_id] = mode

    # ── the request side ─────────────────────────────────────────────────

    def get_frame(self, node_id: str, row: int,
                  activate: Callable[[Reason, Request], None],
                  urgency: Urgency = Urgency.DEFERRED,
                  form_key: str | None = None,
                  supersedes: bool = True,
                  then: Callable[[], None] | None = None) -> Request:
        """Ask *node_id* for *row*. Returns as soon as the node has declared.

        Calls `activate(INITIAL, ctx)` on the caller's thread — that call is
        a few list appends and must not be anything else — and then arms the
        activation. Whoever called this does not wait and is not told
        anything; the second call is where the answer happens.

        `supersedes` marks this node's previous in-flight activation
        cancelled, which is what a scrubbing GUI wants: the frame it asked
        for two positions ago is no longer worth re-entering for. A sweep
        that issues many rows at once passes False.
        """
        with self._lock:
            self._seq += 1
            holder = f"{node_id}#{self._seq}"
        ctx = Request(node_id=node_id, holder=holder, row=row,
                      form_key=form_key or self.form_key,
                      urgency=urgency, activate=activate, dispatcher=self,
                      then=then, t_open=time.perf_counter())
        activate(Reason.INITIAL, ctx)
        self._arm(ctx, supersedes)
        return ctx

    def _arm(self, ctx: Request, supersedes: bool) -> None:
        """Declare what the activation asked for, then wait on what is missing."""
        if not ctx.asked:
            # A node that asked for nothing is ready the instant it is armed.
            with self._runnable:
                self._ready.append(ctx)
                self._runnable.notify()
            return

        by_form: dict[str, list[int]] = {}
        for row, form_key in ctx.asked:
            by_form.setdefault(form_key, []).append(row)
        # Declared before `_lock` is taken, so nothing here ever holds this
        # lock while reaching for the graph's.
        for form_key, rows in by_form.items():
            self.graph.declare(Need(ctx.holder, ctx.row,
                                    tuple(row - ctx.row for row in rows),
                                    form_key, ctx.urgency))

        superseded = None
        with self._lock:
            self.activations += 1
            if self._modes.get(ctx.node_id, Mode.PARALLEL) is not Mode.PARALLEL:
                self._armed_rows.setdefault(ctx.node_id, set()).add(ctx.row)
            if supersedes:
                previous = self._current.get(ctx.node_id)
                if previous is not None and not previous.cancelled:
                    previous.cancelled = True
                    self.superseded += 1
                    superseded = previous
            self._current[ctx.node_id] = ctx
            missing = [key for key in ctx.asked if not self.pool.has(*key)]
            ctx.outstanding = len(missing)
            for key in missing:
                self._waiting.setdefault(key, []).append(ctx)
            if not missing:
                self.immediate += 1
                ctx.t_ready = time.perf_counter()
                self._ready.append(ctx)
                self._runnable.notify()
        #: outside the lock, because it reaches into the graph. A superseded
        #: activation's rows are dropped here and not by the new declaration:
        #: they are two holders now, so nothing releases them implicitly.
        if superseded is not None:
            self.graph.release(superseded.holder)

    def cancel(self, ctx: Request) -> None:
        """This activation is no longer wanted. It will not be re-entered."""
        with self._lock:
            if not ctx.cancelled:
                ctx.cancelled = True
                self.superseded += 1

    # ── landings ─────────────────────────────────────────────────────────

    def _landed(self, key: tuple[int, str]) -> None:
        """A key is in the pool. Told by the pool, after its lock is dropped."""
        woke = 0
        with self._lock:
            waiters = self._waiting.pop(key, ())
            now = time.perf_counter()
            for ctx in waiters:
                ctx.outstanding -= 1
                if ctx.outstanding == 0 and not ctx.cancelled:
                    ctx.t_ready = now
                    self._ready.append(ctx)
                    woke += 1
            if woke:
                self._runnable.notify(woke)

    def _graph_changed(self) -> None:
        """A declaration arrived or was released. Only the fetch thread cares."""
        with self._lock:
            self._pickable.notify()

    # ── the fetch thread ─────────────────────────────────────────────────

    def _pick(self) -> tuple[Need, int] | None:
        """The highest-pressure declared row that is not on hand.

        Unchanged from V1, including that the ranking is
        `graph.pressure_queue`'s to derive and not a consumer's to state.
        """
        for need in self.graph.pressure_queue():
            if need.form_key != self.form_key:
                continue
            unserved = need.unserved(self.pool.has)
            if unserved:
                return need, unserved[0]
        return None

    def _await_pick(self) -> tuple[Need, int] | None:
        with self._pickable:
            while not self._stop.is_set():
                pick = self._pick()
                if pick is not None:
                    return pick
                self.blocked += 1
                self.last = "blocked"
                before = time.perf_counter()
                self._pickable.wait()
                self.blocked_s += time.perf_counter() - before
            return None

    def _fetch_loop(self) -> None:
        fetcher = self._fetcher_factory()
        try:
            while not self._stop.is_set():
                pick = self._await_pick()
                if pick is None:
                    return
                need, row = pick
                #: `dispatch:<role>`, never the node that declared it. A bar
                #: attributed to the asker claims the GUI spent its time
                #: computing when what it spent was a seek somebody else
                #: performed for it.
                env = Envelope(f"dispatch:{_role(need.node_id)}", row,
                               need.form_key, "dispatch").open()
                try:
                    arr, how = fetcher.exact(row)
                except Exception:
                    self.failures += 1
                    #: park something so `has` says yes; a row nothing can
                    #: decode would otherwise be picked forever
                    self.pool.put(row, need.form_key,
                                  np.zeros((1, 1), np.uint8), by=need.node_id)
                    continue
                env.route = how
                env.close()
                self.graph.record(env)
                self.pool.put(row, need.form_key, arr, by=need.node_id)
                self.served += 1
                if how == "seek":
                    self.seeks += 1
                else:
                    self.steps += 1
                band = f"{_role(need.node_id)}/{need.urgency.name}"
                self.by_pressure[band] = self.by_pressure.get(band, 0) + 1
                if len(self.trace) < self.trace_cap:
                    self.trace.append((round(env.t_end - self._t0, 4),
                                       _role(need.node_id), row, how,
                                       round(env.ms, 2)))
                if not self.graph.still_wants(need.node_id, row,
                                              need.form_key):
                    self.stale += 1
                self.last = f"{_role(need.node_id)}/{band} @{row} {how}"
        finally:
            fetcher.close()

    # ── the recorder threads ─────────────────────────────────────────────

    def _next_runnable(self) -> tuple[Request | None, list[Request]]:
        """The first ready activation its node's mode permits to run now,
        and any cancelled ones dropped on the way past.

        Called under `_runnable`. The dropped ones are handed back rather
        than finished here because finishing one calls into the node, and a
        node that issues its next row from that call would be reaching for
        this lock while it is held.

        Linear in `_ready`, which holds activations whose inputs have landed
        and not yet run — short whenever the recorders keep up, and its
        length when they do not is the thing worth reporting rather than
        optimising away.
        """
        dropped: list[Request] = []
        while True:
            picked: Request | None = None
            rescan = False
            for index, ctx in enumerate(self._ready):
                if ctx.cancelled:
                    del self._ready[index]
                    self._disarm(ctx)
                    dropped.append(ctx)
                    rescan = True
                    break
                mode = self._modes.get(ctx.node_id, Mode.PARALLEL)
                if mode is Mode.PARALLEL:
                    del self._ready[index]
                    picked = ctx
                    break
                if ctx.node_id in self._running:
                    continue
                armed = self._armed_rows.get(ctx.node_id)
                if armed and ctx.row != min(armed):
                    continue      # a lower row of this node is still owed
                del self._ready[index]
                self._running.add(ctx.node_id)
                picked = ctx
                break
            if rescan:
                continue
            return picked, dropped

    def _disarm(self, ctx: Request) -> None:
        """This activation will not run again. Called under `_runnable`."""
        armed = self._armed_rows.get(ctx.node_id)
        if armed is not None:
            armed.discard(ctx.row)
            if not armed:
                del self._armed_rows[ctx.node_id]

    def _await_runnable(self) -> Request | None:
        while not self._stop.is_set():
            with self._runnable:
                ctx, dropped = self._next_runnable()
                if ctx is None and not dropped:
                    self._runnable.wait()
                    continue
            for gone in dropped:
                self._finished(gone)
            if ctx is not None:
                return ctx
        return None

    def _finished(self, ctx: Request) -> None:
        """One activation is done with, run or cancelled. Never under a lock.

        Drops the declaration for a holder that has released its rows, so
        `_needs` does not accumulate one dead entry per row computed. A node
        that did *not* release keeps its declaration — that is the viewer,
        whose hold on the frame on screen is exactly this entry, and it goes
        when the next activation supersedes it.
        """
        if ctx.released or ctx.cancelled:
            self.graph.release(ctx.holder)
        if ctx.then is not None:
            ctx.then()

    def _record_loop(self) -> None:
        while not self._stop.is_set():
            ctx = self._await_runnable()
            if ctx is None:
                return
            try:
                ctx.activate(Reason.ALL_FRAMES_READY, ctx)
            except Exception as exc:
                #: counted and carried, never raised out of the loop. A
                #: recorder thread that dies takes every later activation
                #: with it, and the symptom is a pass that stops advancing
                #: — which reads as a scheduling result and is a crash.
                self.errors.append(f"{ctx.node_id}@{ctx.row}: {exc!r}")
                self.failures += 1
            ctx.t_done = time.perf_counter()
            with self._runnable:
                self.reentries += 1
                self.wait_ms.append(ctx.wait_ms)
                self._running.discard(ctx.node_id)
                self._disarm(ctx)
                self._runnable.notify_all()
            self._finished(ctx)

    # ── report ───────────────────────────────────────────────────────────

    def stats(self) -> dict:
        with self._lock:
            pending = sum(len(v) for v in self._waiting.values())
            ready = len(self._ready)
        waits = sorted(self.wait_ms)
        return {
            "threads": {"fetch": 1, "recorders": self._recorder_count},
            "served": self.served, "seeks": self.seeks, "steps": self.steps,
            "failures": self.failures, "stale": self.stale,
            #: what `idle_polls` was, in the units the mechanism actually
            #: has: how many times there was nothing to fetch, and how long
            #: that lasted. Neither is a poll.
            "blocked": self.blocked, "blocked_s": round(self.blocked_s, 3),
            "by_pressure": dict(self.by_pressure),
            "activations": self.activations, "reentries": self.reentries,
            "immediate": self.immediate, "superseded": self.superseded,
            "pending_waits": pending, "ready_depth": ready,
            "wait_ms_p50": round(waits[len(waits) // 2], 2) if waits else None,
            "wait_ms_p95": (round(waits[int(len(waits) * 0.95)], 2)
                            if waits else None),
        }
