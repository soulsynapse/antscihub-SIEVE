"""The single shared execution path: a plan, a reader, and a store go in.

CLI, GUI, and HPC call this identically (`adr/one-execution-path.md`). The GUI
adds a *view* over it — a thread, a coalescer, a progress signal — and never a
second traversal, because two execution paths is two answers to what a project
computes and the disagreement would be invisible: both would report success
against caches keyed on their own arithmetic.

**What is left here is only the loop.** Ordering came from `Dag`, keys and the
window and resolved parameters came from `ExecutionPlan`, and where a computed
frame goes came from `FrameStore`. This module decodes, calls, delays, and
discards. Everything it would otherwise have had to invent is somewhere that can
be tested without a codec.

**Decode is lazy, per frame.** The source frame is fetched on the first root
that misses the cache and not at all when every root hits, which is what makes
re-running a tuned span cost nothing rather than cost a seek per frame. The
reader is a `FrameSource` rather than a `VideoReader` for the same reason the
store is a protocol: a run over materialized frames (VISION step 4) is the same
executor with a different source, not a mode.

**A stateful node keeps its state in its binding, and a served range is what it
has to survive.** `cache_policy` keys a node whose warmup is *bounded* whether
or not it keeps state (`adr/cache-admission-is-bounded-warmup.md`), so a store
that serves frames 150 to 200 and misses 201 is now reachable — and it leaves
the tool at 149 with the loop at 201. Three things here answer that, and they
are one rule seen from three sides:

- The store is read and written only where this run has itself filled the node's
  warmup, so an entry is never a lead-in frame's under-warmed output and a hit
  is never better-warmed than what the run would have computed. The run's own
  lead-in therefore always computes, which is what settles the state before the
  first hit can happen.
- A node whose history a skipped call would have filled — anything windowed, and
  any keyed stateful node — is asked of the store *after* its input is in hand,
  and keeps that frame either way. A hit skips the call and never the window.
- `_resettle` replays the kept frames into a state the hits left behind, before
  the first call that follows them.

The cost is that such a node's input is fetched on every frame, which for a root
means a decode on a warm re-render. That is paid by graphs whose *root* is
stateful or windowed and by no others: below a root, the input is the parent's
emission and the parent's own hit supplies it.

**The spec points at what runs, so there is nothing to select.** v2 asked a
kernel registry for a callable per node and per backend; v3 reads `ToolSpec.run`
(`adr/no-kernel-apparatus.md`), and what is left of that lookup is `_bind`
minting one state per run. The backend the registry chose was hashed into every
key, which made a wrong selection a silently poisoned cache; there is no
selection left to get wrong.

**Emission is delayed by declared lookahead, and that is the one extension.**
A v2 window only ever trailed, so a node's output for frame `i` was computable
the moment `i` was read. A v3 tool may declare `lookahead_frames`, and then its
output for `i` cannot exist until `i + k` has been read — so at loop step `j` it
answers for `j - k`, and everything below it answers for that frame too. Each
node therefore has a *lag*: its own lookahead plus its upstream's, accumulated
along the path, which is the same quantity `ExecutionPlan.lookahead` folds the
maximum of and the reason `decode_range` is widened at the trailing end. The
loop reads in step and the graph answers behind it, so one `FrameResult` is
assembled from outputs computed at different steps and is complete only when the
slowest node in the graph has reached that frame.

Two consequences worth naming. The result for a frame is yielded *after* the
frames its lookahead reaches have been read, which costs latency rather than
decode — a preview of a centred detector arrives `k` frames later than one of a
trailing chain over the same footage. And the cache is written at the frame a
node *answered for*, never at the frame the loop is reading: the store is keyed
by source frame index, and an entry filed under the reading index would be
served back later as a different frame's result.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from sieve.core.pipeline_model import Node
from sieve.core.tool_base import (
    ArraySpec,
    Mode,
    ToolRun,
    ToolSpec,
    node_lookahead_frames,
    node_warmup_frames,
)
from sieve.core.types import ChannelSpec, Frame, FrameCount, FrameIndex, FrameSpan
from sieve.pipeline.cache import FrameStore, NullFrameStore
from sieve.pipeline.plan import ExecutionPlan


class FormatMismatchError(RuntimeError):
    """The reader's decode format is not the one this run's keys were derived
    under.

    A defect rather than a user error, which is why it is a `RuntimeError` and
    not something a command catches to print nicely: nothing a user types
    chooses the format, so reaching this means two call sites derived it from
    different graphs. See `_check_format`.
    """


class UnrunnableNodeError(RuntimeError):
    """A node this graph contains cannot be executed by this executor.

    Not a `GraphError`: the graph is valid and the plan for it is buildable and
    useful — a dry run and a storage prediction both work on a graph containing
    one of these. What is missing is a way to *call* the node, and that is a
    property of the executor rather than of the document, so it is raised here
    and at run time rather than by `Dag.build` or `ExecutionPlan`.

    Which shapes those are is `_unrunnable_reason`, and deliberately not a list
    repeated here: every cause is something `ToolRun` has no signature for, so
    the enumeration belongs beside the signature and a second copy in this
    docstring would be the one that went stale. The message this carries is that
    function's clause with the node's identity in front of it.
    """


class FrameSource(Protocol):
    """Random access to source frames by index.

    `VideoReader` satisfies it. So does a reader over a materialized crop, and
    so does a list of frames in a test — which is why this is here rather than
    the concrete class: `sieve.pipeline` importing `sieve.decode.reader` would
    put a codec underneath the one module that most needs to run without one.
    """

    def read(self, index: int) -> Frame:
        """The frame at `index`, in source coordinates."""
        ...


@dataclass(frozen=True, init=False, slots=True)
class FrameResult:
    """Every node's output for one source frame.

    All nodes rather than only the leaves: the GUI shows intermediates, a
    checkpoint materializes one, and the cost of carrying them is one frame per
    node held for as long as the caller holds this — which it already paid to
    compute them. A caller wanting one node indexes for it.
    """

    #: The source frame index these outputs derive from. Authoritative, and
    #: preserved through every node — see `_run_node`.
    index: FrameIndex
    #: `node_id` to that node's output.
    outputs: Mapping[str, Frame]
    #: Which nodes were served from the store rather than computed. What a HUD
    #: reports and what a test asserts caching actually happened on.
    from_cache: frozenset[str]
    #: The frame as decoded, which is what a viewport showing the whole frame
    #: needs (render-fed playback) and what no node downstream of a crop node
    #: still has. `None` when no decode happened for this frame, which is the
    #: warm re-render of a graph whose roots are all servable without their
    #: input — see the module docstring on the roots that are not. Carrying it
    #: costs one frame's reference for as long as the caller holds this, the
    #: same argument as `outputs` above.
    #:
    #: v2 carried a second field saying whether this was already a crop, because
    #: a run over a written artifact was handed one and the promise above could
    #: not be kept. Schema v1 makes such a run a *child source* with an identity
    #: of its own (`adr/detector-is-a-node.md`), so what is decoded is whole
    #: footage either way and there is no flag left to carry.
    source: Frame | None = None

    def __init__(
        self,
        index: int | FrameIndex,
        outputs: Mapping[str, Frame],
        from_cache: frozenset[str],
        source: Frame | None = None,
    ) -> None:
        object.__setattr__(self, "index", FrameIndex.of(index))
        object.__setattr__(self, "outputs", outputs)
        object.__setattr__(self, "from_cache", from_cache)
        object.__setattr__(self, "source", source)

    def __getitem__(self, node_id: str) -> Frame:
        """That node's output.

        Raises:
            KeyError: if the plan did not compute it.
        """
        return self.outputs[node_id]


@dataclass(frozen=True, slots=True)
class BoundNode:
    """One node's `run`, its state for this run, and how to feed it.

    v2's `KernelBinding` after the shelf under it went: what a binding is for is
    holding the things that are per-run rather than per-spec, and with one
    signature and no backends the only such thing left is `state`.
    """

    run: ToolRun[Any, Any]
    #: This run's state, from `ToolSpec.state_factory`, or `None` for a tool
    #: that keeps none. Made in `_bind` and unreachable from anywhere else, so
    #: two concurrent `execute` calls over one node are two states.
    state: Any
    mode: Mode
    #: Frames the history holds: warmup + lookahead + 1 for a windowed node,
    #: one otherwise. A streaming node's warmup settles a state rather than
    #: filling a window, so it buys no history.
    window: int
    #: This configuration's warmup, in this node's input frames. Two consumers
    #: below and they are the same claim from either side: it is how far back an
    #: output depends, so it is both how many frames to replay into a stale
    #: state and how far into a run an entry stops being a lead-in artefact.
    warmup: int
    #: Whether `run` carries state across calls, and therefore whether skipping
    #: a call leaves it behind the loop.
    stateful: bool
    #: Frames past its target this node must have read before it may emit.
    lookahead: int
    #: Source frames this node's *upstream* output trails the loop by. Zero at
    #: a root, where the upstream is the reader.
    upstream_lag: int

    @property
    def lag(self) -> int:
        """Source frames this node's own output trails the loop by."""
        return self.upstream_lag + self.lookahead


@dataclass(slots=True)
class _Partial:
    """One source frame's result, while the graph is still catching up to it.

    Mutable and private, unlike everything else in this module: it is the
    assembly buffer for a `FrameResult`, and a node's contribution lands in it
    at whatever step that node reaches the frame. At most `plan.lookahead` of
    these are open at once.
    """

    outputs: dict[str, Frame] = field(default_factory=dict)
    from_cache: set[str] = field(default_factory=set)
    source: Frame | None = None


def execute(
    plan: ExecutionPlan,
    reader: FrameSource,
    *,
    store: FrameStore | None = None,
) -> Iterator[FrameResult]:
    """Run `plan` against `reader`, yielding one result per frame of the span.

    A generator, so a caller cancels by stopping consumption and the memory held
    is one frame per node rather than one per node per frame. The GUI's cheapest
    correct cancellation is to abandon the iterator; nothing here needs a flag.

    Lead-in frames are computed and never yielded — they exist to warm the
    tools, and handing them to a caller would make the discard the caller's
    problem in every one of three call sites. They are not stored either, and
    that is the newer half: a frame computed while a node's own warmup is still
    filling is not the frame that node would compute cold. The frames past the span
    that a lookahead declaration adds are never yielded either, for the mirror
    reason: they were read so that the last frames of the span could be
    answered, and nothing was asked about them.

    Args:
        plan: What to run. Its `decode_range` is what the reader is asked for.
        reader: Where source frames come from.
        store: Where computed frames are looked up and kept. Defaults to
            keeping nothing, so a caller that has not thought about caching gets
            correct results rather than an unbounded dict it did not ask for.

    Yields:
        One `FrameResult` per frame in `plan.span`, in order.

    Raises:
        UnrunnableNodeError: if any node cannot be called — checked once, up
            front, so a graph that cannot finish does not first decode half of
            it — or if a node's output does not carry the frame index it was
            asked to answer for.
        FormatMismatchError: if the reader's format is not the plan's.
        VideoDecodeError: if a frame in the range cannot be read.
    """
    keep = NullFrameStore() if store is None else store
    bindings = _bind(plan)
    histories: dict[str, deque[Frame]] = {
        node_id: deque(maxlen=bound.window)
        for node_id, bound in bindings.items()
        if bound.mode is Mode.WINDOWED
    }
    # Only where a served range could leave a state behind: a node with no key
    # is never skipped, so its state is fed by the loop and there is nothing to
    # replay. That exclusion is what keeps `temporal_baseline`'s 7199-frame
    # warmup from becoming 7199 frames held in a deque.
    feeds: dict[str, deque[Frame]] = {
        node_id: deque(maxlen=bound.warmup)
        for node_id, bound in bindings.items()
        if bound.stateful and bound.warmup > 0 and node_id in plan.keys
    }
    # Nodes that need their input frame even on a hit, because what the hit
    # skips is the call and not the history behind it.
    reads_regardless = {
        node_id
        for node_id, bound in bindings.items()
        if bound.mode is Mode.WINDOWED or node_id in feeds
    }
    fed_through: dict[str, int] = {}
    pending: dict[int, _Partial] = {}
    total = len(plan.dag.order)
    first = int(plan.decode_start)

    for index in plan.decode_range:
        step = int(index)
        # Opened when the frame is read rather than when something answers for
        # it, so that "which frames the run covers" is the reader's range and
        # not a consequence of how many nodes there are — a graph with no nodes
        # yields one empty result per frame of the span rather than nothing.
        pending.setdefault(step, _Partial())
        decoded: Frame | None = None
        # This step's emissions, by node. A node's downstream reads its parent
        # here and nowhere else: the parent answered for `step - lag[parent]`
        # this very step, which is exactly the frame the child's own window
        # needs next, so no alignment machinery and no per-node input queue.
        emitted: dict[str, Frame] = {}
        for node in plan.dag.order:
            bound = bindings[node.node_id]
            if step - bound.upstream_lag < first:
                # Nothing has arrived at this node yet: everything above it is
                # still reading past the frames it will answer for first.
                continue
            answers_for = step - bound.lag
            key = plan.keys.get(node.node_id)
            # The store is touched only where this run has itself filled the
            # node's warmup, and both directions of that matter. Writing an
            # earlier entry would file a lead-in frame's short-window output
            # under a key that says nothing about how much lead-in it got, and
            # a later run would be served it in place of the settled answer.
            # Reading one would be the mirror: a run clamped at frame 0 would be
            # handed a better-warmed frame than it would have computed, which is
            # still a range that does not equal its cold run.
            reusable = key is not None and answers_for - first >= bound.warmup
            # Where the one lookup happens. A node whose history the hit does
            # not fill can be asked before its input is fetched, which is what
            # keeps a warm re-render from decoding; every other node is asked
            # after, so that the frames it was going to skip still land in the
            # window or the feed behind it.
            eager = reusable and node.node_id in reads_regardless
            if reusable and not eager:
                cached = keep.get(key, answers_for)
                if cached is not None:
                    _serve(node.node_id, cached, answers_for, emitted, pending)
                    continue
            fed = plan.dag.upstreams[node.node_id]
            if fed:
                (parent,) = fed
                incoming = emitted[parent]
            else:
                if decoded is None:
                    # The one place the reader is touched, and only once per
                    # frame however many roots there are: a graph with two roots
                    # reads one frame rather than seeking twice.
                    decoded = reader.read(step)
                    _check_format(decoded, plan)
                    pending[step].source = decoded
                incoming = decoded
            window = _window(incoming, bound, histories.get(node.node_id))
            if window is None:
                # Holding the window open: this node has its target in hand but
                # not yet the frames past it that it declared it would read.
                continue
            if eager:
                cached = keep.get(key, answers_for)
                if cached is not None:
                    _serve(node.node_id, cached, answers_for, emitted, pending)
                    _remember(feeds, node.node_id, incoming)
                    continue
            _resettle(node.node_id, bound, plan, feeds.get(node.node_id), fed_through)
            produced = _run_node(node, window, bound, plan, answers_for)
            fed_through[node.node_id] = answers_for
            emitted[node.node_id] = produced
            pending.setdefault(answers_for, _Partial()).outputs[node.node_id] = produced
            _remember(feeds, node.node_id, incoming)
            if reusable:
                keep.put(key, answers_for, produced)
        yield from _completed(pending, total, plan)


def _serve(
    node_id: str,
    cached: Frame,
    answers_for: int,
    emitted: dict[str, Frame],
    pending: dict[int, _Partial],
) -> None:
    """File a stored frame as this node's answer, as if it had been computed.

    Both places the store can answer land here rather than each writing the
    three lines, because the third — recording the node in `from_cache` — is the
    one a copy forgets, and forgetting it is a reuse figure that under-reports
    itself and a HUD that says the store did nothing.
    """
    emitted[node_id] = cached
    held = pending.setdefault(answers_for, _Partial())
    held.outputs[node_id] = cached
    held.from_cache.add(node_id)


def _remember(feeds: dict[str, deque[Frame]], node_id: str, incoming: Frame) -> None:
    """Keep this node's input against a state that may have to be replayed.

    Only the last `warmup` of them, and only for a node that can be skipped at
    all — see `feeds` in `execute`. The frame is kept whether the call happened
    or was answered from the store, which is the whole point: the run that was
    served frames 150 to 200 still has to be able to compute 201.
    """
    feed = feeds.get(node_id)
    if feed is not None:
        feed.append(incoming)


def _resettle(
    node_id: str,
    bound: BoundNode,
    plan: ExecutionPlan,
    feed: deque[Frame] | None,
    fed_through: dict[str, int],
) -> None:
    """Run a stale state over its warmup, discarding what comes out.

    The entry cost `adr/cache-admission-is-bounded-warmup.md` trades for v1's
    contiguity requirement. A served range skips the call, so the state stops
    where the hits began; the declaration that let the node be keyed at all says
    the last `warmup` frames determine the answer, so feeding it exactly those
    puts it where a cold run would have been. That claim is what the bit-identity
    gate in `tests/unit/test_cache_admission.py` exists to check, and it is the
    only thing standing behind an entry — a tool declaring `WarmupKind.BOUNDED`
    over an accumulator would be replayed here and still answer wrong.

    Nothing to do in the ordinary case, and it costs a dict lookup to find that
    out: the run's own lead-in is served nothing (`reusable` is false until the
    warmup has elapsed), so a node that has hit no entries has already been fed
    every frame in order and this replays none of them. The discard is the same
    one the lead-in performs; this is where a range that arrives mid-run gets it.
    """
    if feed is None:
        return
    seen = fed_through.get(node_id)
    if seen is not None and feed and int(feed[-1].index) <= seen:
        # The contiguous case, which is every frame of every run that was served
        # nothing: the newest frame kept is one the state has already had, so
        # there is no gap and the loop below would skip every element of a deque
        # that may be thousands long.
        return
    params = plan.params[node_id]
    for frame in feed:
        index = int(frame.index)
        if seen is not None and index <= seen:
            continue
        bound.run(params, FrameSpan((frame,)), bound.state)
        seen = index
    if seen is not None:
        fed_through[node_id] = seen


def _window(incoming: Frame, bound: BoundNode, history: deque[Frame] | None) -> FrameSpan | None:
    """The frames this node is called with, or `None` while it is still filling.

    A span even for a streaming node, because there is one signature and a
    window of one is what "one frame in" is in it (`adr/no-kernel-apparatus.md`).

    A windowed node's history is appended to on every step its input arrives,
    including the steps before it may emit anything — those frames are the
    lookahead side of its first window, and skipping the append would hand it a
    window missing its own future.

    The span is told how many of its trailing frames are past the target, which
    is what makes `FrameSpan.target` the frame the tool was called about. The
    number is this node's own, from `node_lookahead_frames` at bind time, so it
    is the same one `_run_node` then checks the returned index against.
    """
    if history is None:
        return FrameSpan((incoming,))
    history.append(incoming)
    if len(history) <= bound.lookahead:
        return None
    return FrameSpan(tuple(history), lookahead=FrameCount(bound.lookahead))


def _completed(
    pending: dict[int, _Partial], total: int, plan: ExecutionPlan
) -> Iterator[FrameResult]:
    """Every frame the whole graph has now answered for, in order.

    Ascending and stopping at the first gap, because a frame is completed by its
    slowest node and every node's answers advance one frame per step — so the
    open frames are completed in the order they were opened, and a later one
    being ready while an earlier one is not is a state this loop cannot reach.

    The frames left behind at the end are the trailing lookahead: the faster
    nodes answered for frames past the span that the slowest never reached, and
    nothing asked about them.
    """
    for index in sorted(pending):
        held = pending[index]
        if len(held.outputs) < total:
            return
        del pending[index]
        if index >= plan.span.start:
            yield FrameResult(
                index=index,
                outputs=held.outputs,
                from_cache=frozenset(held.from_cache),
                source=held.source,
            )


def _check_format(decoded: Frame, plan: ExecutionPlan) -> None:
    """Refuse a reader whose format is not the one the keys were derived under.

    The failure this catches is the one that leaves no trace. `source_key`
    hashes the decode format, so a reader opened in the other one produces
    correctly-shaped frames computed from the wrong pixels, stored under keys
    that say otherwise — and the symptom is a preview that looks plausible and a
    cache that stays poisoned for the rest of the session. Several sites derive
    this format independently and each is correct in isolation; this is the
    check that makes a disagreement between any two of them loud.

    Costs one enum comparison per decoded frame, which is nothing beside the
    decode that produced it, so it is not hoisted to the first frame only: a
    reader that changed format mid-run is exactly as wrong as one that started
    wrong, and a first-frame check would miss it.
    """
    if (decoded.channels is ChannelSpec.GRAY) == plan.luma:
        return
    wanted = "luma" if plan.luma else "colour"
    raise FormatMismatchError(
        f"this run is keyed for {wanted} but the reader handed {decoded.channels}. Every frame "
        "it computes would be stored under a key that names the other format."
    )


def _unrunnable_reason(spec: ToolSpec) -> str | None:
    """Why `ToolRun` cannot call `spec`, or `None` if it can.

    The single enumeration of what the tool contract can declare and this
    executor has no way to call. Pure over the spec — declarations only, no
    shelf, no machine, no footage — so `_bind` can ask it once for the whole
    graph before a frame is read, and so a test can walk the declarable shape
    space without an executor.

    v2 kept this beside four kernel protocols and each clause named the one that
    declined to invent a signature. There is one signature now, so the clauses
    are what that signature cannot express: a spec that points at nothing, a
    node that emits for only some of its input frames, and rows at either end of
    a call that is frames in and a frame out.

    Returns:
        A clause naming the declaration that cannot be run — the caller supplies
        whatever identifies the node — or `None` when the spec is callable.
    """
    if spec.run is None:
        return (
            "points at no run, so there is nothing to call — a spec may be declared without one "
            "and a graph over it still plans, but it cannot be executed"
        )
    if spec.rate_changing:
        return (
            "declares rate_changing, and the one signature has no way to emit nothing for an "
            "input frame"
        )
    if not isinstance(spec.accepts, ArraySpec):
        return (
            "accepts rows, and a run is handed frames — nothing downstream of a table has "
            "anything to feed it"
        )
    if not isinstance(spec.emits, ArraySpec):
        return "emits rows, and a run returns a frame — a table emitter has no way to hand back"
    return None


def _bind(plan: ExecutionPlan) -> dict[str, BoundNode]:
    """Resolve every node to the callable that implements it, or refuse.

    Up front, over the whole graph, before a frame is read. The alternative —
    resolving lazily at the node — would decode the lead-in, run four nodes, and
    then discover that the fifth cannot be called at all, which is a minute of
    work to deliver a message that was available immediately. Every rejection
    here is static: it reads declarations, and nothing about the footage can
    change the answer.

    **The state is made here, and that is what makes it per run.** This function
    is called once inside `execute`, so a stateful node's state is created here,
    lives in the binding, and is unreachable from anywhere else — two concurrent
    `execute` calls over the same node are two bindings and therefore two
    states, with no registry entry, no dict keyed by node id, and nothing to
    reset between runs. The generator is the state's lifetime, which is also the
    right one: a caller that cancels a preview by abandoning the iterator drops
    the half-warmed background model with it.

    **The lag is accumulated forward, where the plan folded it backward.** Both
    are the same per-edge sum, and they answer different questions: the plan
    needs the graph's maximum, to widen the decode range, while the loop needs
    each node's own, to know which frame that node is answering for. A rate
    change would make the two speak different index spaces, which is one more
    reason `rate_changing` is refused above rather than merely unimplemented.
    """
    bindings: dict[str, BoundNode] = {}
    for node in plan.dag.order:
        spec = plan.dag.spec(node.node_id)
        reason = _unrunnable_reason(spec)
        if reason is not None:
            # The node id, not only the tool: a graph may name the same tool
            # twice and the reader has to know which one to go and edit.
            raise UnrunnableNodeError(f"{node.node_id} ({spec.tool_id} {spec.version}) {reason}")
        assert spec.run is not None  # `_unrunnable_reason` refused a spec without one
        step = (spec, plan.params[node.node_id])
        lookahead = node_lookahead_frames(step).frames
        warmup = node_warmup_frames(step).frames
        bindings[node.node_id] = BoundNode(
            run=spec.run,
            state=None if spec.state_factory is None else spec.state_factory(),
            mode=spec.mode,
            window=(warmup + lookahead + 1 if spec.mode is Mode.WINDOWED else 1),
            warmup=warmup,
            stateful=spec.stateful,
            lookahead=lookahead,
            upstream_lag=max(
                (bindings[parent].lag for parent in plan.dag.upstreams[node.node_id]),
                default=0,
            ),
        )
    return bindings


def _run_node(
    node: Node,
    window: FrameSpan,
    bound: BoundNode,
    plan: ExecutionPlan,
    answers_for: int,
) -> Frame:
    """One call, with the frame index checked on the way out.

    The check is cheap and closes a hole nothing else can see: the store is
    keyed by source frame index, so a tool that renumbered its output would
    write an entry under the wrong index and serve it back later as a different
    frame's result. That is a wrong answer from cache, which `cache_key.py`'s
    asymmetry rule says is the failure to spend a comparison on. A tool that
    genuinely reindexes is `rate_changing` and was already refused in `_bind`.

    Checked against the frame the executor scheduled this call for rather than
    against the newest frame in the window, because with a declared lookahead
    those differ — the target sits `lookahead` frames from the end, and a tool
    that emitted for the end of its own window instead would answer every frame
    `k` early under a key that says otherwise.
    """
    produced = bound.run(plan.params[node.node_id], window, bound.state)
    if produced.index != answers_for:
        spec = plan.dag.spec(node.node_id)
        raise UnrunnableNodeError(
            f"{node.node_id} ({spec.tool_id} {spec.version}) returned frame "
            f"{produced.index} for target frame {answers_for}; a run emits for the frame "
            f"{bound.lookahead} back from the end of the window it was handed, and the cache is "
            "keyed on it"
        )
    return produced
