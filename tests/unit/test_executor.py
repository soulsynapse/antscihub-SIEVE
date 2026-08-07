"""What the loop has to do that nothing above it already did.

The plan settled ordering, keys, and both sides of the window, and those are
tested where they live. What is left here is what only the loop can get wrong:
the lead-in has to reach the tools and *not* reach the caller; a cache hit has
to skip both the call and the decode; a node that cannot be called has to say so
before anything is read rather than after half a span has been decoded; and — the
one thing v2's loop never had to do — a node that declared it would read past
its target has to answer for the frame it was centred on, with everything below
it answering for that same frame and the result assembled from calls made at
different steps.

The backend half of v2's file is gone with `backend/` (`adr/no-kernel-apparatus.
md`): four of its thirteen cases were about which of two kernels a plan selected
and what that selection did to a key, and there is one `run` per tool now with
nothing left to select. So is the crop the loop used to apply to every root:
under schema v1 the crop is a node (`adr/detector-is-a-node.md`), so the region
never reaches this module.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

from sieve.core.pipeline_model import Edge, Node, Pipeline, SourceSpan
from sieve.core.tool_base import (
    ArraySpec,
    ElementRelation,
    Emission,
    Mode,
    ParamsBase,
    ParamStereotype,
    TableSpec,
)
from sieve.core.tool_registry import ToolRegistry, register_tool
from sieve.core.types import ChannelSpec, Frame, FrameCount, FrameSpan
from sieve.pipeline.cache import FrameStore, MemoryFrameStore
from sieve.pipeline.dag import Dag
from sieve.pipeline.executor import (
    FrameResult,
    FrameSource,
    UnrunnableNodeError,
    _bind,
    execute,
)
from sieve.pipeline.plan import ExecutionPlan

SOURCE = "footage|1|2"

#: A scratch shelf, not `REGISTRY` — `test_plan.py`'s reason: the process-wide
#: one is populated by tool modules at import, and registering into it would make
#: this file's behaviour depend on whether such an import had already happened.
SHELF = ToolRegistry()

WIDTH, HEIGHT = 32, 24

#: `(frame index, amount)` for every `tag` call. A list rather than a counter
#: because the lead-in case needs to know *which* frames reached the tool, and
#: "how many" would be satisfied by the wrong three.
CALLS: list[tuple[int, int]] = []

#: The frame indices of every window a windowed tool was handed, in call order.
WINDOWS: list[tuple[int, ...]] = []


def tag_run(params: TagParams, window: FrameSpan, state: None) -> Frame:
    del state
    frame = window.target
    CALLS.append((int(frame.index), params.amount))
    return Frame(
        data=frame.data + np.uint8(params.amount),
        index=frame.index,
        channels=frame.channels,
    )


@register_tool(
    tool_id="tag",
    version="1.0.0",
    summary="Adds `amount` to every pixel, and remembers being called.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    emissions=(Emission("out"),),
    run=tag_run,
    element=ElementRelation.PRESERVED,
    settling_epsilon=0.0,
    param_stereotypes={"amount": ParamStereotype.SCALAR_RANGE},
    registry=SHELF,
)
class TagParams(ParamsBase):
    amount: int = 1

    @classmethod
    def max_warmup_frames(cls) -> FrameCount:
        return FrameCount(3)


def _mean_run(params: ParamsBase, window: FrameSpan, state: None) -> Frame:
    """The mean of a window, emitted for the frame the executor centred it on.

    The one place a tool has to know its own lookahead: the target sits that
    many frames back from the end of what it was handed, because the frames
    after it are the reason it was made to wait. A tool that took `window.target`
    instead would answer for a frame it had not been asked about, which is what
    `_run_node`'s index check is there to catch.
    """
    del state
    lookahead = params.lookahead_frames().frames
    target = window[len(window) - 1 - lookahead]
    WINDOWS.append(tuple(int(frame.index) for frame in window))
    data = np.mean([frame.data.astype(np.float32) for frame in window], axis=0).astype(np.uint8)
    return Frame(data=data, index=target.index, channels=target.channels)


def _windowed(tool_id: str, warmup: int, lookahead: int) -> type[ParamsBase]:
    """A windowed tool declaring both sides of its window, and a mean over it.

    The refinement is declared beside the bound rather than only as the bound,
    which is what lets `_mean_run` read the number back: `ParamsBase.
    lookahead_frames` is the per-configuration answer and `node_lookahead_frames`
    prefers it, so a tool that states both is stating one number twice and a
    tool that states only the bound cannot find its own target.
    """

    @register_tool(
        tool_id=tool_id,
        version="1.0.0",
        summary="A mean over the frames around the one it emits for.",
        accepts=ArraySpec(),
        emits=ArraySpec(),
        emissions=(Emission("out"),),
        run=_mean_run,
        element=ElementRelation.PRESERVED,
        mode=Mode.WINDOWED,
        settling_epsilon=0.0,
        registry=SHELF,
    )
    class Params(ParamsBase):
        @classmethod
        def max_warmup_frames(cls) -> FrameCount:
            return FrameCount(warmup)

        @classmethod
        def max_lookahead_frames(cls) -> FrameCount:
            return FrameCount(lookahead)

        def lookahead_frames(self) -> FrameCount:
            return FrameCount(lookahead)

    return Params


#: A trailing three-frame mean: v2's window, which reads nothing ahead.
_windowed("trail3", 2, 0)
#: A centred five-frame window: two frames of lead-in and two of lookahead.
_windowed("centre2", 2, 2)
#: The smallest window with a trailing side, for chaining two of them.
_windowed("ahead1", 0, 1)


def _last_frame_run(params: WrongEndParams, window: FrameSpan, state: None) -> Frame:
    """A centred tool that emits for the end of its window instead of its middle.

    The mistake the convention invites: `FrameSpan.target` is the last frame,
    which is the right answer for a trailing window and the wrong one for every
    window with a lookahead side.
    """
    del params, state
    return window.target


@register_tool(
    tool_id="wrong_end",
    version="1.0.0",
    summary="Reads ahead and then answers for the frame it read.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    emissions=(Emission("out"),),
    run=_last_frame_run,
    element=ElementRelation.PRESERVED,
    mode=Mode.WINDOWED,
    registry=SHELF,
)
class WrongEndParams(ParamsBase):
    @classmethod
    def max_lookahead_frames(cls) -> FrameCount:
        return FrameCount(1)


@register_tool(
    tool_id="unwritten",
    version="1.0.0",
    summary="A spec with nothing behind it, which plans and cannot run.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    emissions=(Emission("out"),),
    element=ElementRelation.PRESERVED,
    registry=SHELF,
)
class UnwrittenParams(ParamsBase):
    pass


def _rows_run(params: RowsParams, window: FrameSpan, state: None) -> Frame:
    del params, state
    return window.target


@register_tool(
    tool_id="rows",
    version="1.0.0",
    summary="Emits a table, which the one signature has no way to hand back.",
    accepts=ArraySpec(),
    emits=TableSpec(columns=("x", "y")),
    emissions=(Emission("out"),),
    run=_rows_run,
    registry=SHELF,
)
class RowsParams(ParamsBase):
    pass


def _reads_rows_run(params: ReadsRowsParams, window: FrameSpan, state: None) -> Frame:
    del params, state
    return window.target


@register_tool(
    tool_id="reads_rows",
    version="1.0.0",
    summary="Accepts a table, which no run is ever handed.",
    accepts=TableSpec(columns=("x",)),
    emits=ArraySpec(),
    emissions=(Emission("out"),),
    run=_reads_rows_run,
    element=ElementRelation.PRESERVED,
    registry=SHELF,
)
class ReadsRowsParams(ParamsBase):
    pass


def _decimate_run(params: DecimateParams, window: FrameSpan, state: None) -> Frame:
    del params, state
    return window.target


@register_tool(
    tool_id="decimate",
    version="1.0.0",
    summary="Keeps one frame in ten, which is not one frame out per frame in.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    emissions=(Emission("out"),),
    run=_decimate_run,
    element=ElementRelation.PRESERVED,
    rate_changing=True,
    registry=SHELF,
)
class DecimateParams(ParamsBase):
    def output_rate(self) -> Fraction:
        return Fraction(1, 10)


class ListSource:
    """Frames in a list, counting the reads.

    A source rather than a `VideoReader` because several of these cases are about
    *whether* a read happened, which a real decoder can only be asked about by
    timing it.
    """

    def __init__(self) -> None:
        self.reads: list[int] = []

    def read(self, index: int) -> Frame:
        self.reads.append(index)
        # Frame `n` is a field of intensity `n`, so a later assertion can say
        # which frame an output came from rather than that one arrived. Gray,
        # because these plans are keyed for luma: every graph here is built from
        # tools that accept a single channel, so `plan.luma` is True and
        # `executor._check_format` refuses a colour reader against it.
        data = np.full((HEIGHT, WIDTH), index % 200, dtype=np.uint8)
        return Frame(data=data, index=index, channels=ChannelSpec.GRAY)


class RefusingSource:
    """A source that fails if it is read at all."""

    def read(self, index: int) -> Frame:
        raise AssertionError(f"decoded frame {index} when every node was cached")


def node(node_id: str, tool_id: str = "tag", **params: object) -> Node:
    return Node(node_id=node_id, tool_id=tool_id, version="1.0.0", params=dict(params))


def edges(*pairs: str) -> tuple[Edge, ...]:
    """`"a>b"` for each edge. Schema v1 gives an edge no port to name."""
    built: list[Edge] = []
    for pair in pairs:
        upstream, downstream = pair.split(">")
        built.append(Edge(upstream=upstream, downstream=downstream))
    return tuple(built)


#: The span these cases run over unless they are about the span. A module-level
#: constant rather than a default argument because a `SourceSpan` built in a
#: signature is built once at import and shared, which ruff's B008 is right to
#: flag even where the object is frozen.
DEFAULT_SPAN = SourceSpan(start=20, end=23)


def plan_for(pipeline: Pipeline, *, span: SourceSpan = DEFAULT_SPAN) -> ExecutionPlan:
    return ExecutionPlan.build(Dag.build(pipeline, SHELF), source=SOURCE, span=span)


@pytest.fixture(autouse=True)
def forget_calls() -> None:
    CALLS.clear()
    WINDOWS.clear()


def run(
    plan: ExecutionPlan, source: FrameSource, *, store: FrameStore | None = None
) -> list[FrameResult]:
    """Drain the generator."""
    return list(execute(plan, source, store=store))


def test_the_lead_in_reaches_the_run_and_not_the_caller() -> None:
    """Three warmup frames are computed; the caller sees only the span.

    The two halves fail differently and both are silent. Skipping the lead-in
    leaves a stateful tool unsettled on the first frame anyone looks at. Yielding
    it makes the caller's first frame the wrong frame, and since the frames are
    adjacent and plausible, nothing downstream would notice.
    """
    plan = plan_for(Pipeline(nodes=(node("t"),)))
    assert plan.lead_in == FrameCount(3)

    results = run(plan, ListSource())

    assert [call[0] for call in CALLS] == [17, 18, 19, 20, 21, 22]
    assert [result.index for result in results] == [20, 21, 22]


def test_a_warm_cache_skips_the_run_and_the_decode() -> None:
    """Second run over the same span reads nothing and computes nothing.

    Decode is lazy per frame, so a graph whose every root is a hit never asks the
    reader — which is what makes re-scrubbing a tuned span free rather than
    merely cheaper. `RefusingSource` is what states that: a counter could be
    satisfied by a reader that was called and ignored.
    """
    plan = plan_for(Pipeline(nodes=(node("t"),)))
    store = MemoryFrameStore()

    first = run(plan, ListSource(), store=store)
    assert len(store) == len(plan.decode_range)
    CALLS.clear()

    second = run(plan, RefusingSource(), store=store)

    assert not CALLS
    assert [result.from_cache for result in second] == [frozenset({"t"})] * 3
    assert all(
        np.array_equal(before["t"].data, after["t"].data)
        for before, after in zip(first, second, strict=True)
    )


def test_two_roots_share_one_decode_of_each_frame() -> None:
    """A second root costs a second call and not a second read.

    v2 stated this while asserting that every root saw the replicate's crop; the
    crop is a node now (`adr/detector-is-a-node.md`) and what is left is the
    claim about the reader, which is this module's either way — a per-root decode
    would be the same pixels at twice the price, and nothing downstream would
    report it.
    """
    plan = plan_for(Pipeline(nodes=(node("a"), node("b"))))
    source = ListSource()

    results = run(plan, source)

    assert source.reads == [int(index) for index in plan.decode_range]
    assert len(source.reads) == len(set(source.reads))
    assert all(set(result.outputs) == {"a", "b"} for result in results)


def test_the_decoded_frame_reaches_the_caller_only_when_a_decode_happened() -> None:
    """`source` is this frame's, and a warm replay carries none.

    Two failures, both silent. A source on the fully-cached replay would claim a
    decode that never ran, and whoever shares it — render-fed playback — would
    treat store-served results as fresh pixels. No source at all on the cold run
    is the second decode coming back.
    """
    plan = plan_for(Pipeline(nodes=(node("t"),)))
    store = MemoryFrameStore()

    first = run(plan, ListSource(), store=store)
    for result in first:
        assert result.source is not None
        assert result.source.index == result.index
        assert result.source.data.shape == (HEIGHT, WIDTH)

    second = run(plan, RefusingSource(), store=store)
    assert all(result.source is None for result in second)


def test_a_windowed_node_gets_a_span_ending_at_the_current_frame() -> None:
    """A trailing window is a bounded history, not one frame smuggled through.

    `trail3` asks for two warmup frames and reads nothing ahead. Behind `tag`'s
    three-frame warmup the fold therefore charges five source frames, and the
    first yielded window is over the settled tag outputs for 18, 19, and 20.
    """
    plan = plan_for(Pipeline(nodes=(node("t"), node("w", "trail3")), edges=edges("t>w")))

    results = run(plan, ListSource())

    assert plan.lead_in == FrameCount(5)
    assert plan.lookahead == FrameCount(0)
    assert plan.key("w") is None
    assert WINDOWS[-3:] == [(18, 19, 20), (19, 20, 21), (20, 21, 22)]
    assert [result.index for result in results] == [20, 21, 22]
    assert [int(result["w"].data[0, 0]) for result in results] == [20, 21, 22]


def test_every_node_in_a_result_answers_for_the_same_source_frame() -> None:
    """One result is one source frame, however differently its nodes are paced.

    v2 stated this of a merging node's two ports, which schema v1 has no way to
    build; what makes it a live claim again is the delay. A fork whose branches
    declare different lookaheads answers for a frame at different *steps* — `w`
    is a frame behind `c` throughout — so a loop that assembled a result out of
    whatever each node last produced would pair `c`'s frame `i` with `w`'s frame
    `i-1`, and the two are adjacent, plausible, and wrong.
    """
    forked = Pipeline(
        nodes=(node("a"), node("c", amount=5), node("w", "ahead1")),
        edges=edges("a>c", "a>w"),
    )
    plan = plan_for(forked)

    results = run(plan, ListSource())

    assert [result.index for result in results] == [20, 21, 22]
    for result in results:
        assert result["c"].index == result.index
        assert result["w"].index == result.index
        # `a` adds 1 and `c` adds 5 on top; `w` is a mean of `a`'s output over
        # frames either side of the target, which for a ramp is the target's own
        # value. Both branches therefore name the source frame they came from.
        assert int(result["c"].data[0, 0]) == int(result.index) + 6
        assert int(result["w"].data[0, 0]) == int(result.index) + 1


def test_a_node_the_one_signature_cannot_call_is_refused_before_anything_is_read() -> None:
    """Every shape the contract can declare and `ToolRun` cannot call.

    Up front, over the whole graph: resolving lazily would decode the lead-in,
    run four nodes and then discover that the fifth emits rows, which is a minute
    of work to deliver a message that was available immediately. Each clause
    names the declaration rather than the node's position, because what the
    reader has to change is the declaration.
    """
    shapes = {
        "unwritten": "points at no run",
        "decimate": "declares rate_changing",
        "reads_rows": "accepts rows",
        "rows": "emits rows",
    }
    for tool_id, clause in shapes.items():
        source = ListSource()
        with pytest.raises(UnrunnableNodeError, match=clause):
            run(plan_for(Pipeline(nodes=(node("x", tool_id),))), source)
        assert not source.reads


def test_a_spec_that_points_at_no_run_says_which_node() -> None:
    """And which tool it is, which is what a reader goes and edits.

    A graph may name one tool twice, so the node id alone does not say where to
    look and the tool alone does not say which of them broke. v2 said the same of
    a missing kernel and had a second half — GPU absent versus GPU unwritten —
    that has no referent here (`adr/no-kernel-apparatus.md`).
    """
    pipeline = Pipeline(
        nodes=(node("first", "unwritten"), node("second", "unwritten")),
        edges=edges("first>second"),
    )

    with pytest.raises(UnrunnableNodeError, match=r"first \(unwritten 1\.0\.0\)"):
        run(plan_for(pipeline), ListSource())


def test_a_lookahead_node_emits_for_a_frame_it_has_already_read_past() -> None:
    """The extension, stated at the yield: the answer trails the reading.

    `centre2` reads two frames past its target, so the plan widens the range at
    both ends and the tool's first call — at source frame 20 — answers for frame
    18. The caller still gets exactly the span: the frames answered before it are
    lead-in, and the frames read after it exist only so the last of the span can
    be answered at all.
    """
    plan = plan_for(Pipeline(nodes=(node("w", "centre2"),)))
    source = ListSource()

    results = run(plan, source)

    assert (plan.lead_in, plan.lookahead) == (FrameCount(2), FrameCount(2))
    assert source.reads == list(range(18, 25))
    assert [window[-1] for window in WINDOWS] == [20, 21, 22, 23, 24]
    assert [result.index for result in results] == [20, 21, 22]


def test_a_lookahead_window_holds_the_frames_on_both_sides_of_its_target() -> None:
    """What the second side buys, stated at the call instead of at the yield.

    A centred window of five is two frames of history, the target, and two frames
    the run had to wait for. v2's loop could only ever hand over the first three,
    which is why a tool tuned against a centred result could not be a node
    (`adr/detector-is-a-node.md`) — and a loop that widened the decode range and
    then handed over a trailing window anyway would pass every case above.
    """
    plan = plan_for(Pipeline(nodes=(node("w", "centre2"),)))

    results = run(plan, ListSource())

    # The window that answered for the first frame of the span. Its target is
    # third of five, so two of the frames in it are ones the caller was never
    # told about and the tool could not otherwise have seen.
    for_first = WINDOWS[len(WINDOWS) - len(results)]
    assert for_first == (18, 19, 20, 21, 22)
    assert for_first[len(for_first) - 1 - 2] == int(results[0].index)


def test_the_lookahead_the_loop_delays_by_is_the_one_the_plan_decoded_for() -> None:
    """Two centred nodes in a chain delay by the sum, and the plan read for it.

    The loop accumulates the lag forward from the roots and the plan folds the
    maximum backward from the leaves; they are the same per-edge sum and nothing
    checks that they agree. A loop that delayed by each node's own declaration
    rather than by its ancestry would answer the last frame of the span from a
    window running off the end of what was read, and would report the same frame
    count either way.
    """
    chained = Pipeline(
        nodes=(node("t"), node("u", "ahead1"), node("v", "ahead1")),
        edges=edges("t>u", "u>v"),
    )
    plan = plan_for(chained)
    source = ListSource()

    results = run(plan, source)

    assert plan.lookahead == FrameCount(2)
    assert max(source.reads) == plan.span.end - 1 + plan.lookahead.frames
    assert [result.index for result in results] == [20, 21, 22]
    assert all(result["v"].index == result.index for result in results)


def test_a_lookahead_tool_that_answers_for_the_end_of_its_window_is_refused() -> None:
    """The one place the two-sided window can be misread, made loud.

    A window's target is its last frame only while nothing is read ahead of it,
    and `FrameSpan.target` cannot say otherwise — so a centred tool that reaches
    for it answers every frame `k` early. Nothing downstream would notice: the
    frames are adjacent, the shapes match, and the store would file each one
    under the number the loop asked for rather than the one the tool used.
    """
    plan = plan_for(Pipeline(nodes=(node("w", "wrong_end"),)))

    with pytest.raises(UnrunnableNodeError, match=r"returned frame 21 for target frame 20"):
        run(plan, ListSource())


def test_no_node_that_lags_behind_the_lookahead_is_ever_a_keyed_node() -> None:
    """Why the store index and the reading index may agree without being one.

    The loop files an entry at the frame a node *answered for*, which under a
    lookahead is not the frame being read. It cannot currently be caught getting
    that wrong: `cache_policy` denies a windowed tool a key, a key is denied to
    everything below an unkeyed node, and a node lags only if something windowed
    is above it — so the set of nodes that lag and the set that are keyed are
    disjoint, and the two spellings compute the same number
    ([findings/loop/2026.08.07-the-emission-delay-and-the-cache-key-cannot-meet.md](
    ../../docs/findings/loop/2026.08.07-the-emission-delay-and-the-cache-key-cannot-meet.md)).

    So this is the disjointness itself, which is a claim rather than a
    coincidence: the day a windowed frontier becomes keyable, the store call
    below it is reading an index the loop is no longer at, and this is what says
    so before a frame is served under the wrong number.
    """
    chained = Pipeline(
        nodes=(node("t"), node("w", "ahead1"), node("u", amount=2)),
        edges=edges("t>w", "w>u"),
    )
    plan = plan_for(chained)
    bindings = _bind(plan)

    assert plan.lookahead == FrameCount(1)
    assert {node_id for node_id, bound in bindings.items() if bound.lag} == {"w", "u"}
    assert set(plan.keys) == {"t"}
    assert all(bindings[node_id].lag == 0 for node_id in plan.keys)
