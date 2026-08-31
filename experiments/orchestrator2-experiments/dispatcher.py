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

**Two roles.** Fetch threads decode and only decode; recorder threads run
activations and never decode. If arithmetic ran on a fetch thread, a step
costing tens of milliseconds would stall the decode the whole pressure queue
is about — the freeze the session explorer exists to avoid, re-introduced at
the other end.

**How many fetch threads is a measurement, and this file's first answer was
wrong.** It argued for exactly one, on the grounds that `Fetcher` is one open
container with one cursor and is not thread-safe. The premise is true and the
conclusion does not follow: what a cursor needs is one thread *per Fetcher*,
not one Fetcher. Two findings dated 2026.08.30 price the difference.
`a-second-cursor-makes-preemption-free` shows the seek pair a preemption
costs was one cursor being taken from the sweep rather than the price of
serving a person — given its own cursor, the alternations still happen,
`fill:seek` falls to 1 per window, and a live playhead costs what a parked
one costs. `the-remaining-wall-is-decode-and-a-reader-that-does-not-overlap`
then shows the wall is `fill + gui` and not `max(fill, gui)`, because one
dispatcher thread blocks inside `exact()` whichever container it holds. That
is about a third of a filled window and the largest single item on the sheet.

So `readers` is a parameter. Each fetch thread owns its own `Fetcher` and so
its own cursor, and above one the bands **partition**: reader 0 takes only
what nobody is waiting on, readers 1 and above take only INTERACTIVE picks.
A single reader takes everything, which is V1.

The partition is the whole mechanism and an overlapping split undoes it. A
reader 0 that may serve an interactive pick when it happens to be free is a
reader 0 that seeks away from the sweep's frontier and pays to rejoin it —
the seek pair `a-second-cursor-makes-preemption-free` attributes the cost to,
reintroduced by the arrangement meant to remove it. The cost of partitioning
is that reader 0 sits idle when only interactive work is pending, and idling
is precisely what preserves its cursor. It defaults to 1, so a run here stays
comparable to V1's until an experiment says otherwise, and a result names it:
a wall from one reader and a wall from two are different facts about the same
code.

**Two software readers is the shape that already failed once.**
`2026.08.21-software-decoders-collapse-under-contention` measured four
software workers with aggregate throughput below one worker alone. The
arrangement that survived there is asymmetric — software for the sequential
sweep, hardware for the interactive cursor — and this class does not
implement that. What it does is make the count a knob so the question can be
asked, and preserve the property that the extra reader is idle unless
something interactive is pending.

**One decode, several forms.** A fetcher hands back the source plane
whatever form was asked for, so which form a pick names decides what is
*stored* and not what is read. `tiers` is that map — a key and an opaque
callable that makes it from the plane — and it is how ADR-0017 arrives here:
display sampling for what is looked at, source sampling for what is recorded,
both of one instant, one decode. The second form is built only where
something already declared it (`graph.wanter`), because building one nobody
asked for is retention on a guess and that is the move the retention finding
refused. Nothing here learns what a form is; the callable comes from whoever
knew.

**Nothing has an interval**, and that is a property rather than the
argument. The fetch thread blocks on a condition the graph notifies when a
declaration arrives; the recorder threads block on a condition this class
notifies when a key lands in the pool. `blocked` counts waits where V1's
`idle_polls` counted naps, and the two are not the same measurement — one is
how often there was nothing to do, the other is how often we checked.

**Why two phases, given that a coroutine would also never sleep.** The
alternative this design has to beat is not polling, which is only what V1
did. It is a suspending scheduler: a consumer awaiting each input as it needs
it, with no interval, no deadline, no context object and far less ceremony
than a two-call callback. Against that, "nothing sleeps" argues for nothing.

What earns the split is that the INITIAL call's output is a **scheduling
input**. `Graph.pressure_queue` cannot rank a need it has not seen whole:
subsumption asks whether one declaration's rows lie inside a wider one's,
urgency ranks across every node in flight, and ADR-0006 makes the declaration
itself the hold, so the refcount needs the complete set at the moment it is
taken. A coroutine reveals demand one await at a time, so the dispatcher
would know a consumer wanted row *n* and not that it also wanted *n-30*,
*n-20* and *n-10*; it would serve *n*, learn the rest, and seek back — the
shape `2026.08.30-the-pressure-dispatcher-preempts-into-seeks` measured, a
consumer buying by seek what was arriving sequentially.

So the design commitment is that **a declaration is complete before anything
is served**, and these two phases are where that is enforced. It is not a
commitment to callbacks: a coroutine that gathers its whole demand set in one
await has re-invented INITIAL, and this could become `async` without giving
anything up. What could not be kept is a consumer that discovers its inputs
by running.

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


#: How long a node may go unserved before it outranks the ranking (prior art:
#: the Linux deadline I/O scheduler and the deadline family generally). The
#: pressure queue ranks for locality and urgency, which is exactly the axis
#: that starves whoever ranks last; a deadline scheduler keeps its sorted
#: queue and adds an expiry queue beside it, servicing what has expired
#: regardless of where the ranking put it.
#:
#: **Measured against last service, not against declaration.** The first
#: version aged a declaration from when it arrived, which is wrong for a
#: standing declaration covering a window: a sweep declares once and is then
#: permanently older than any deadline, so it wins every pick and the expiry
#: queue replaces the ranking instead of rescuing it. Measured that way it
#: took 976 of 1071 picks. A deadline in Linux belongs to a *request* and
#: leaves the queue when that request is served; the equivalent for a
#: standing declaration is the time since this node was last served.
DEADLINE_S = 2.0

#: How many rows an expired node is served before the ranking resumes (prior
#: art: `fifo_batch`). One pick per deadline is an anti-starvation floor so
#: low it is indistinguishable from starvation over a window; draining a
#: batch is what makes the floor mean progress. It is deliberately not a fair
#: share — a deadline scheduler guarantees service, never a rate.
EXPIRY_BATCH = 16


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

    **ORDERED starves if anything it is waiting on never arrives**, and the
    dispatcher owes it a deadline for that reason. Running the lowest armed
    row means a row that is never served stops every later row of that node,
    with their inputs pinned while they wait. Two ways in: a declaration
    subsumed behind INTERACTIVE traffic forever, since `_pick` takes the
    first need with an unserved row and urgency sorts first, so a person
    scrubbing without pause means a sweep's rows never land; and, before it
    was fixed, an activation cancelled while still waiting on a decode, which
    never reached `_ready` and so never disarmed. The first is what
    `DEADLINE_S` is for and the second is now disarmed at the point of
    cancellation.

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
    """`tool-dis-140233#57` -> `tool`. The counters and the duration bars want
    the role, and an id carries two things that are not it.

    **Both separators, and the `#` was a regression.** An id carries an object
    id after a dash, so two windows' fills are distinct holders; since holding
    became per-activation it also carries a sequence after a hash. Splitting
    on the dash alone left `gui#42`, which put one key per activation into
    `duration_bars` where there should be one per role — the same defect the
    bars were fixed for in V1, arriving from the other direction. Caught by
    `06-two-readers` reporting seeks under forty distinct `gui#n` names.
    """
    return node_id.split("-")[0].split("#")[0]


class Dispatcher:
    """Owns the threads and the moment; knows nothing about what a node is.

    Constructed with a graph and a pool, and a factory for the decode leaf so
    the fetch thread can own its cursor exclusively.
    """

    def __init__(self, graph: Graph, pool: Pool, form_key: str,
                 fetcher_factory: Callable[[], Any],
                 recorders: int = 2, readers: int = 1,
                 deadline_s: float = DEADLINE_S, t0: float = 0.0,
                 tiers: dict[str, Callable[[Any], Any]] | None = None,
                 coserve: bool = True) -> None:
        #: `readers` defaults to 1 here and to 2 in the explorer, which is
        #: deliberate rather than an oversight: a headless experiment is
        #: comparing against numbers taken at one reader, and a driven session
        #: is trying to feel right. Both say which they used.
        self.graph = graph
        self.pool = pool
        self.form_key = form_key
        #: which keys a decode can be turned into, and how (ADR-0017). A
        #: fetcher hands back one thing — the source plane — and every form
        #: of that row is a function of it, so what varies between them is a
        #: callable and not a route. The dispatcher never learns what a form
        #: is: it holds an opaque maker per key, the same refusal `pool.put`
        #: makes about payloads.
        #:
        #: Default is the one identity entry, which is every measurement in
        #: this folder taken before 2026-08-31 and is not the same
        #: arrangement as a one-entry map some caller passed.
        self._tiers: dict[str, Callable[[Any], Any]] = (
            dict(tiers) if tiers else {form_key: lambda arr: arr})
        #: off is the control that prices the co-serve rather than assuming
        #: it: with two tiers and no co-serve, each form is decoded on its own
        #: pick, which is what a pool keyed by form does when nobody writes
        #: the negotiation.
        self.coserve = coserve
        self._fetcher_factory = fetcher_factory
        self._recorder_count = max(1, recorders)
        self._reader_count = max(1, readers)
        #: 0 disables the expiry queue, which is how an experiment measures
        #: what the ranking does when nothing rescues it.
        self.deadline_s = deadline_s
        self.expiry_batch = EXPIRY_BATCH
        #: when each node last had a row served. The clock the deadline is
        #: measured against; a node absent from here has never been served
        #: and ages from when it declared.
        self._last_served: dict[str, float] = {}
        #: the node currently draining its expiry batch, and how much of the
        #: batch is left.
        self._expiry_node: str | None = None
        self._expiry_left = 0
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
        #: keys a fetch thread has taken and not yet put. Without it two
        #: readers pick the same unserved row — `pool.has` is still false
        #: while the first is inside `exact()` — and the second decode is
        #: waste no counter would call waste, because both were correct picks
        #: at the moment each was made.
        self._claimed: set[tuple[int, str]] = set()

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
        #: picks the expiry queue made that the ranking would not have. Zero
        #: means the ranking never starved anybody over this run.
        self.expired_picks = 0
        #: rows where one decode was put under more than one key, and what
        #: the extra keys cost to build. The cross-form half of "decode once,
        #: serve many": under a single form that claim is the pool's sharing
        #: count, and under two it is this — a second consumer at a coarser
        #: form is served without a second decode or it is not served at all.
        self.cofetched = 0
        #: why a co-serve declined, which is the difference between a rate
        #: that is low because the tiers agree and one that is low because
        #: they never meet. `present` is the other tier already resident —
        #: somebody served it first, and nothing was lost. `undeclared` is
        #: nobody wanting it at the moment it was free, which is the decode
        #: that will be paid for again.
        self.coserve_present = 0
        self.coserve_undeclared = 0
        self.tier_ms = 0.0
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
            threading.Thread(target=self._fetch_loop, args=(index,),
                             name=f"fetch{index}", daemon=True)
            for index in range(self._reader_count)]
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
                    #: here and not only where a cancelled activation is
                    #: dropped from `_ready`: one cancelled while still
                    #: waiting on a decode never reaches `_ready`, so that
                    #: path never runs and an ORDERED node would block on a
                    #: row that is never going to run.
                    self._disarm(previous)
                    self._unwait(previous)
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
            #: `moved=True`: this release *is* the consumer changing its mind,
            #: which is the one thing a holder that declares once can say
            #: about why its rows went.
            self.graph.release(superseded.holder, moved=True)

    def cancel(self, ctx: Request) -> None:
        """This activation is no longer wanted. It will not be re-entered."""
        with self._lock:
            if not ctx.cancelled:
                ctx.cancelled = True
                self.superseded += 1
                self._disarm(ctx)
                self._unwait(ctx)

    def _unwait(self, ctx: Request) -> None:
        """Drop a cancelled activation from the keys it was waiting on.

        Called under `_lock`. Without it a cancelled activation stays
        registered against every row it asked for until that row happens to
        land — and a row a scrubbing person passed over may never land at
        all. A driven session left 301 of these behind in twenty seconds,
        which is a leak that grows with how much somebody scrubs; `_landed`
        would still skip them, so it costs memory rather than correctness,
        and `pending_waits` is what shows it.
        """
        for key in ctx.asked:
            waiters = self._waiting.get(key)
            if not waiters:
                continue
            remaining = [other for other in waiters if other is not ctx]
            if remaining:
                self._waiting[key] = remaining
            else:
                del self._waiting[key]

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

    def _unclaim(self, row: int, form_key: str) -> None:
        with self._lock:
            self._claimed.discard((row, form_key))

    def _graph_changed(self) -> None:
        """A declaration arrived or was released. Only the fetch threads care.

        `notify_all` and not `notify`, above one reader. The bands partition,
        so a declaration is pickable by exactly one band and waking one
        arbitrary waiter wakes the wrong one half the time — which leaves the
        reader that could have served it asleep until some later declaration
        happens to wake it. It self-heals under a person, who declares
        constantly, and that is what makes it a defect worth naming rather
        than one a run reports: nothing counts a wake that went to the wrong
        band. The spurious wake costs a predicate test.
        """
        with self._lock:
            self._pickable.notify_all()

    # ── the fetch thread ─────────────────────────────────────────────────

    def _pick(self, interactive_only: bool | None) -> tuple[Need, int] | None:
        """The highest-pressure declared row not on hand and not claimed.

        The ranking is `graph.pressure_queue`'s to derive and never a
        consumer's to state, unchanged from V1. New here are `_claimed`,
        which is what makes a second reader safe, and the band filter, which
        is what keeps it off the sweep's cursor.

        Called under `_lock` so taking a pick and claiming it are one step.
        """
        batched = self._batch_pick(interactive_only)
        if batched is not None:
            self.expired_picks += 1
            return batched
        expired = self._expired_pick(interactive_only)
        if expired is not None:
            self.expired_picks += 1
            self._expiry_node = expired[0].node_id
            self._expiry_left = self.expiry_batch - 1
            return expired
        for need in self.graph.pressure_queue():
            if need.form_key not in self._tiers:
                continue
            #: None means this reader is the only one and takes every band.
            if (interactive_only is not None
                    and interactive_only != (need.urgency
                                             is Urgency.INTERACTIVE)):
                continue
            for row in need.unserved(self.pool.has):
                if (row, need.form_key) not in self._claimed:
                    return need, row
        return None

    def _serviceable(self, need: Need, interactive_only: bool | None):
        """The first row of *need* this reader may take, or None."""
        if need.form_key not in self._tiers:
            return None
        if (interactive_only is not None
                and interactive_only != (need.urgency
                                         is Urgency.INTERACTIVE)):
            return None
        for row in need.unserved(self.pool.has):
            if (row, need.form_key) not in self._claimed:
                return row
        return None

    def _batch_pick(self, interactive_only: bool | None):
        """Keep draining the expired node's batch, if it has one left."""
        if self._expiry_left <= 0 or self._expiry_node is None:
            return None
        for need in self.graph.pressure_queue():
            if need.node_id != self._expiry_node:
                continue
            row = self._serviceable(need, interactive_only)
            if row is not None:
                self._expiry_left -= 1
                return need, row
            break
        self._expiry_node, self._expiry_left = None, 0
        return None

    def _expired_pick(self, interactive_only: bool | None):
        """A node that has gone `deadline_s` without being served.

        The expiry queue a deadline scheduler keeps beside its sorted one,
        consulted before the ranking because a node that has expired is by
        definition one the ranking was not going to reach. `expired_picks`
        counting zero is what says the ranking never starved anybody over a
        run, and it is the number to read before concluding that it cannot.
        """
        if self.deadline_s <= 0:
            return None
        now = time.perf_counter()
        cutoff = now - self.deadline_s
        for declared_at, need in self.graph.by_age():
            last = self._last_served.get(need.node_id, declared_at)
            if last > cutoff:
                continue
            row = self._serviceable(need, interactive_only)
            if row is not None:
                return need, row
        return None

    def _await_pick(self,
                    interactive_only: bool | None) -> tuple[Need, int] | None:
        with self._pickable:
            while not self._stop.is_set():
                pick = self._pick(interactive_only)
                if pick is not None:
                    need, row = pick
                    self._claimed.add((row, need.form_key))
                    #: served, so this node's deadline clock restarts. What
                    #: makes the expiry queue a floor under service rather
                    #: than a replacement for the ranking.
                    self._last_served[need.node_id] = time.perf_counter()
                    return pick
                self.blocked += 1
                self.last = "blocked"
                before = time.perf_counter()
                self._pickable.wait()
                self.blocked_s += time.perf_counter() - before
            return None

    def _fetch_loop(self, index: int = 0) -> None:
        #: one reader takes everything, which is V1. Above one the bands
        #: partition: reader 0 never touches an interactive pick, so its
        #: cursor stays where the sweep left it.
        interactive_only = index > 0
        if self._reader_count == 1:
            interactive_only = None
        #: the band is handed to the factory because ADR-0020 makes the route
        #: a per-band decision — a sequential reader and a seeking one are the
        #: two cases hardware decode falls on opposite sides of.
        try:
            fetcher = self._fetcher_factory(interactive_only)
        except Exception as exc:
            #: recorded rather than raised, for the reason `_record_loop`
            #: keeps its own failures: a fetch thread that dies on the way up
            #: takes every decode with it, and the symptom is a window that
            #: never fills — which reads as a scheduling result and is a
            #: crash. A hardware route that is unavailable arrives here.
            self.errors.append(f"reader {index} could not open: {exc!r}")
            self.failures += 1
            return
        try:
            while not self._stop.is_set():
                pick = self._await_pick(interactive_only)
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
                    self._unclaim(row, need.form_key)
                    continue
                env.route = how
                env.close()
                self.graph.record(env)
                #: the envelope just timed this decode, so the replacement
                #: policy is told what the key cost rather than guessing. A
                #: seek and a step differ by more than an order of magnitude
                #: and that difference is the whole reason the pool ranks by
                #: cost instead of by recency.
                self.pool.put(row, need.form_key,
                              self._make(need.form_key, arr, env),
                              by=need.node_id, cost_ms=env.ms)
                self._unclaim(row, need.form_key)
                self._coserve(row, need.form_key, arr, env)
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

    def _make(self, form_key: str, arr: Any, env: Envelope) -> Any:
        """This tier's payload, built from the one decode. Timed as the
        tier's cost and not as the decode's: a build charged to the envelope
        would report the sweep's decode as having got slower under a second
        form, when what it did was produce two things."""
        maker = self._tiers[form_key]
        if maker is None:
            return arr
        began = time.perf_counter()
        made = maker(arr)
        self.tier_ms += (time.perf_counter() - began) * 1000.0
        return made

    def _coserve(self, row: int, served: str, arr: Any,
                 env: Envelope) -> None:
        """Put every *other* declared form of this row from the same decode.

        ADR-0017 puts two forms of one instant in the pool — display sampling
        for what is looked at, source sampling for what is recorded — and a
        pool keyed by form would otherwise decode the row twice, once per
        consumer. The decode does not depend on which form asked for it, so
        the second form is a build over bytes already in hand.

        **Declared and unserved only.** Building a form nobody asked for is
        holding on a guess, and how far that gets is measured: the retention
        finding refused a policy that kept rows on speculation, and the
        information gap it named — the next want is not declared yet — is the
        same one here. `graph.wanter` is the whole of the test.

        Cost is the decode's, for every form. What a key would cost to
        replace is what it would take to produce again, which is this decode
        however cheap the build over it was.
        """
        if not self.coserve or len(self._tiers) == 1:
            return
        for form_key in self._tiers:
            if form_key == served:
                continue
            if self.pool.has(row, form_key):
                self.coserve_present += 1
                continue
            wanter = self.graph.wanter(row, form_key)
            if wanter is None:
                self.coserve_undeclared += 1
                continue
            with self._lock:
                if (row, form_key) in self._claimed:
                    continue
                self._claimed.add((row, form_key))
            try:
                self.pool.put(row, form_key, self._make(form_key, arr, env),
                              by=wanter, cost_ms=env.ms)
            finally:
                self._unclaim(row, form_key)
            self.cofetched += 1

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
            self.graph.release(ctx.holder, moved=ctx.cancelled)
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
            "threads": {"fetch": self._reader_count,
                        "recorders": self._recorder_count},
            "served": self.served, "seeks": self.seeks, "steps": self.steps,
            "failures": self.failures, "stale": self.stale,
            "tiers": sorted(self._tiers), "coserve": self.coserve,
            #: rows a second form was built from a decode that had already
            #: happened. Under one tier it is 0 by construction and says
            #: nothing; under two it is the cross-form half of "decode once,
            #: serve many".
            "cofetched": self.cofetched,
            "coserve_present": self.coserve_present,
            "coserve_undeclared": self.coserve_undeclared,
            "tier_ms": round(self.tier_ms, 1),
            #: what `idle_polls` was, in the units the mechanism actually
            #: has: how many times there was nothing to fetch, and how long
            #: that lasted. Neither is a poll.
            "blocked": self.blocked, "blocked_s": round(self.blocked_s, 3),
            "deadline_s": self.deadline_s,
            "expiry_batch": self.expiry_batch,
            "expired_picks": self.expired_picks,
            "by_pressure": dict(self.by_pressure),
            "activations": self.activations, "reentries": self.reentries,
            "immediate": self.immediate, "superseded": self.superseded,
            "pending_waits": pending, "ready_depth": ready,
            "wait_ms_p50": round(waits[len(waits) // 2], 2) if waits else None,
            "wait_ms_p95": (round(waits[int(len(waits) * 0.95)], 2)
                            if waits else None),
        }
