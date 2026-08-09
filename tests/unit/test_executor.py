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

from enum import StrEnum
from fractions import Fraction

import numpy as np
import pytest

from sieve.core.pipeline_model import Edge, Node, Pipeline, SourceSpan
from sieve.core.tool_base import (
    ArraySpec,
    DisplaySurface,
    ElementRelation,
    Emission,
    Mode,
    ParamsBase,
    ParamStereotype,
    TableSpec,
    WarmupKind,
)
from sieve.core.tool_registry import ToolRegistry, register_tool
from sieve.core.types import ChannelSpec, Frame, FrameCount, FrameSpan
from sieve.pipeline.cache import FrameStore, MemoryFrameStore
from sieve.pipeline.dag import Dag
from sieve.pipeline.executor import (
    FrameResult,
    FrameSource,
    UndrawableNodeError,
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

#: `window.target.index` for each of those calls. Beside `WINDOWS` rather than
#: derived from it, because what the span *says* its target is and where that
#: frame sits in the window are the two halves of the claim.
TARGETS: list[int] = []


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
    # Adding a constant reaches no further back than the frame in front of it,
    # so the three frames below are lead-in this tool does not need and a bound
    # it is exact within — which is what makes it keyed.
    warmup_kind=WarmupKind.BOUNDED,
    param_stereotypes={"amount": ParamStereotype.SCALAR_RANGE},
    registry=SHELF,
)
class TagParams(ParamsBase):
    amount: int = 1

    @classmethod
    def max_warmup_frames(cls) -> FrameCount:
        return FrameCount(3)


def bare_run(params: BareParams, window: FrameSpan, state: None) -> Frame:
    del params, state
    return window.target


@register_tool(
    tool_id="bare",
    version="1.0.0",
    summary="Hands its frame straight back, having asked for no lead-in.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    emissions=(Emission("out"),),
    run=bare_run,
    element=ElementRelation.PRESERVED,
    registry=SHELF,
)
class BareParams(ParamsBase):
    """`tag` without the declared warmup, which is what the store rests on.

    A node may be served an entry only for frames its own warmup has elapsed
    behind, so a tool that declares one recomputes that many frames of every
    run — including a warm one. That is the correct answer and it makes the
    "reads nothing" claim unsayable on `tag`, whose three frames are a fiction
    the plan cases need. This is the same tool without the fiction.
    """


def _mean_run(params: ParamsBase, window: FrameSpan, state: None) -> Frame:
    """The mean of a window, emitted for the frame the executor centred it on.

    Read off the span rather than counted back from its end: the frames after
    the target are the reason this tool was made to wait, and how many there are
    is the executor's number rather than one the tool has to re-derive from
    `params`.
    """
    del params, state
    target = window.target
    WINDOWS.append(tuple(int(frame.index) for frame in window))
    TARGETS.append(int(target.index))
    data = np.mean([frame.data.astype(np.float32) for frame in window], axis=0).astype(np.uint8)
    return Frame(data=data, index=target.index, channels=target.channels)


def _windowed(tool_id: str, warmup: int, lookahead: int) -> type[ParamsBase]:
    """A windowed tool declaring both sides of its window, and a mean over it.

    The refinement is declared beside the bound rather than only as the bound,
    and since the span carries its own target it buys nothing the tool reads:
    what it still pins is that the number the executor puts on the span is
    `node_lookahead_frames`', which prefers the refinement. `wrong_end` below is
    the other half — the bound alone, which is all a tool is obliged to state.
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
        # `None` where there is no lead-in to characterize: a kind with nothing
        # to settle is refused, which `ahead1` is the case for.
        warmup_kind=WarmupKind.BOUNDED if warmup else None,
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


class Flaw(StrEnum):
    """The three ways a filler can disagree with what its tool declared.

    One tool with a parameter for the flaw rather than three tools, because the
    subject is one rule and the cases are what breaking it looks like from each
    side.
    """

    NONE = "none"
    #: Draws nothing at all, which is the surface silently ceasing to exist.
    EMPTY = "empty"
    #: Draws a picture no band names, which nothing would ever read.
    SURPLUS = "surplus"
    #: Draws for the end of its window rather than the frame it answers for.
    OFFSET = "offset"


#: The frames a display filler was called for, in call order. Beside `CALLS`
#: and for its reason: whether the channel was filled on a frame is not
#: answerable by counting.
DRAWN: list[int] = []


def _band_run(params: BandParams, window: FrameSpan, state: None) -> Frame:
    del params, state
    frame = window.target
    CALLS.append((int(frame.index), 0))
    return frame


def _band_display(
    params: BandParams | AheadBandParams, window: FrameSpan, /
) -> dict[DisplaySurface, Frame]:
    """One trace column per frame, or one of the three ways to get it wrong."""
    target = window.target
    DRAWN.append(int(target.index))
    if params.flaw is Flaw.EMPTY:
        return {}
    index = window[len(window) - 1].index if params.flaw is Flaw.OFFSET else target.index
    drawn = {
        DisplaySurface.TRACE: Frame(
            data=np.full((1, 1), int(index), np.float32),
            index=index,
            channels=ChannelSpec.GRAY,
        )
    }
    if params.flaw is Flaw.SURPLUS:
        drawn[DisplaySurface.SCALOGRAM] = drawn[DisplaySurface.TRACE]
    return drawn


@register_tool(
    tool_id="banded",
    version="1.0.0",
    summary="Carries a band, and draws the trace the band is cut on.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    emissions=(Emission("out"),),
    run=_band_run,
    display=_band_display,
    element=ElementRelation.PRESERVED,
    param_stereotypes={
        "band": ParamStereotype.BAND,
        "flaw": ParamStereotype.ENUM,
    },
    param_surfaces={"band": DisplaySurface.TRACE},
    registry=SHELF,
)
class BandParams(ParamsBase):
    band: tuple[float, float] = (0.0, 1.0)
    flaw: Flaw = Flaw.NONE


def _ahead_band_run(params: AheadBandParams, window: FrameSpan, state: None) -> Frame:
    del params, state
    return window.target


@register_tool(
    tool_id="banded_ahead",
    version="1.0.0",
    summary="`banded` with a frame of read-ahead, so its target is not its end.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    emissions=(Emission("out"),),
    run=_ahead_band_run,
    display=_band_display,
    element=ElementRelation.PRESERVED,
    mode=Mode.WINDOWED,
    param_stereotypes={
        "band": ParamStereotype.BAND,
        "flaw": ParamStereotype.ENUM,
    },
    param_surfaces={"band": DisplaySurface.TRACE},
    registry=SHELF,
)
class AheadBandParams(ParamsBase):
    """The only shape in which "the end of the window" is the wrong frame.

    A streaming node is handed one frame, so its target *is* its last frame and
    a filler reaching for the end of the span cannot be caught being wrong. The
    mistake needs a window with a far side to exist at all — which is the same
    reason `wrong_end` above is windowed.
    """

    band: tuple[float, float] = (0.0, 1.0)
    flaw: Flaw = Flaw.NONE

    @classmethod
    def max_lookahead_frames(cls) -> FrameCount:
        return FrameCount(1)


def _last_frame_run(params: WrongEndParams, window: FrameSpan, state: None) -> Frame:
    """A centred tool that emits for the end of its window instead of its middle.

    Reaching for the last frame by hand, which is the one way left to make this
    mistake now that `window.target` is not that frame — and the shape any tool
    written against the trailing convention has.
    """
    del params, state
    return window[len(window) - 1]


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
    TARGETS.clear()
    DRAWN.clear()


def run(
    plan: ExecutionPlan,
    source: FrameSource,
    *,
    store: FrameStore | None = None,
    show: tuple[str, ...] = (),
) -> list[FrameResult]:
    """Drain the generator."""
    return list(execute(plan, source, store=store, show=show))


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
    """Second run over a span with no lead-in reads nothing and computes nothing.

    Decode is lazy per frame, so a graph whose every root is a hit never asks the
    reader — which is what makes re-scrubbing a tuned span free rather than
    merely cheaper. `RefusingSource` is what states that: a counter could be
    satisfied by a reader that was called and ignored.
    """
    plan = plan_for(Pipeline(nodes=(node("b", "bare"),)))
    store = MemoryFrameStore()

    first = run(plan, ListSource(), store=store)
    assert len(store) == len(plan.decode_range) == 3
    CALLS.clear()

    second = run(plan, RefusingSource(), store=store)

    assert not CALLS
    assert [result.from_cache for result in second] == [frozenset({"b"})] * 3
    assert all(
        np.array_equal(before["b"].data, after["b"].data)
        for before, after in zip(first, second, strict=True)
    )


def test_the_store_holds_no_frame_computed_before_its_nodes_warmup_elapsed() -> None:
    """A lead-in frame is not the frame that node computes cold, so it is not kept.

    `tag` declares three frames of warmup, so the first three frames of its
    decode range are answered by a tool that has not had them — which is exactly
    what the lead-in is. Filing those under a key would put them in front of a
    later run whose own lead-in reached further back, and the entry says nothing
    about how much lead-in produced it. The mirror is the same line: those frames
    are not *read* from the store either, so a run clamped near frame 0 computes
    what it would have computed cold rather than being handed something better
    warmed (`adr/cache-admission-is-bounded-warmup.md`).
    """
    plan = plan_for(Pipeline(nodes=(node("t"),)))
    store = MemoryFrameStore()

    run(plan, ListSource(), store=store)

    assert plan.lead_in == FrameCount(3)
    assert len(plan.decode_range) == 6
    assert len(store) == 3
    assert all(store.get(plan.keys["t"], index) is not None for index in range(20, 23))
    CALLS.clear()

    second = run(plan, ListSource(), store=store)

    # The lead-in runs again — that is the re-settle, and for a stateful tool it
    # is the whole reason a served range is safe to enter. The span does not.
    assert [call[0] for call in CALLS] == [17, 18, 19]
    assert [result.from_cache for result in second] == [frozenset({"t"})] * 3


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
    plan = plan_for(Pipeline(nodes=(node("b", "bare"),)))
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
    # Keyed, since 06.5: a window is bounded on both sides by construction, and
    # what denies a key is an epsilon warmup rather than a window or a state
    # (`adr/cache-admission-is-bounded-warmup.md`).
    assert plan.key("w") is not None
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


def test_a_centred_windows_span_target_is_the_frame_it_answers_for() -> None:
    """The span says which of its frames is the target, so no tool counts back.

    `centre2` reads two frames past the frame it emits for, and the number that
    says so is the executor's — `node_lookahead_frames`, which prefers the
    per-configuration refinement over the bound. A tool deriving it instead needs
    that same refinement declared on its own params, and one that stated only the
    bound would count back zero and land on the end of its window.
    """
    plan = plan_for(Pipeline(nodes=(node("w", "centre2"),)))

    results = run(plan, ListSource())

    for_first = WINDOWS[len(WINDOWS) - len(results)]
    assert for_first == (18, 19, 20, 21, 22)
    # The target is the third of the five, not the last — which is the whole of
    # what a lookahead side means, said by the span rather than by the tool.
    assert TARGETS[-len(results) :] == [int(result.index) for result in results]
    assert [window[-1] for window in WINDOWS[-len(results) :]] != TARGETS[-len(results) :]


def test_a_trailing_windows_span_target_is_still_its_last_frame() -> None:
    """What the accessor meant before there was a far side, unmoved.

    Every reader of `target` outside a centred tool — `crop`, `span`, every
    streaming tool handed a window of one — is correct only while this holds, so
    the change that taught the span about a lookahead side is answerable for it.
    """
    plan = plan_for(Pipeline(nodes=(node("t"), node("w", "trail3")), edges=edges("t>w")))

    results = run(plan, ListSource())

    assert WINDOWS[-3:] == [(18, 19, 20), (19, 20, 21), (20, 21, 22)]
    assert TARGETS[-3:] == [window[-1] for window in WINDOWS[-3:]]
    assert TARGETS[-3:] == [int(result.index) for result in results]


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
    and `FrameSpan.target` now says which one it is — so what is left to refuse
    is a tool taking the last frame anyway, which answers every frame `k` early.
    That is the shape of every tool written before the far side existed, and the
    executor is what stops it being a wrong answer. Nothing downstream would
    notice on its own: the
    frames are adjacent, the shapes match, and the store would file each one
    under the number the loop asked for rather than the one the tool used.
    """
    plan = plan_for(Pipeline(nodes=(node("w", "wrong_end"),)))

    with pytest.raises(UnrunnableNodeError, match=r"returned frame 21 for target frame 20"):
        run(plan, ListSource())


def test_a_node_that_lags_the_loop_files_its_entry_under_the_frame_it_answered_for() -> None:
    """The store index is the frame answered for, never the frame being read.

    Until 06.5 this could not be caught getting wrong: `cache_policy` denied a
    windowed tool a key, a key was denied to everything below an unkeyed node,
    and a node lags only if something windowed is above it — so the set of nodes
    that lag and the set that are keyed were disjoint, and the two spellings
    computed the same number
    ([findings/loop/2026.08.07-the-emission-delay-and-the-cache-key-cannot-meet.md](
    ../../docs/findings/loop/2026.08.07-the-emission-delay-and-the-cache-key-cannot-meet.md)).

    `adr/cache-admission-is-bounded-warmup.md` is the day that disjointness
    ended: `w` and `u` both lag by one and both carry keys. A loop filing under
    the reading index would put every entry one frame late — adjacent, plausible,
    and served back later as a different frame's result.
    """
    chained = Pipeline(
        nodes=(node("t"), node("w", "ahead1"), node("u", amount=2)),
        edges=edges("t>w", "w>u"),
    )
    plan = plan_for(chained)
    bindings = _bind(plan)
    store = MemoryFrameStore()

    results = run(plan, ListSource(), store=store)

    assert plan.lookahead == FrameCount(1)
    assert {node_id for node_id, bound in bindings.items() if bound.lag} == {"w", "u"}
    assert set(plan.keys) == {"t", "w", "u"}
    for result in results:
        for node_id in ("t", "w", "u"):
            stored = store.get(plan.keys[node_id], result.index)
            assert stored is not None
            assert np.array_equal(stored.data, result[node_id].data)
    # The two lagging nodes are the ones that would collide, so they have to
    # disagree between adjacent frames or the check above proves nothing.
    assert not np.array_equal(results[0]["u"].data, results[1]["u"].data)


def test_a_declared_surface_is_filled_for_every_frame_the_run_yields() -> None:
    """The channel beside the output, filled for the node the caller watched.

    A picture assembled from a run has to be a picture of the whole span, so the
    property is per frame and not per run: a surface filled on some frames is a
    plot with holes in it, and a plot with holes reads as footage that was quiet
    there. The unwatched node is the other half — the fill costs a second
    derivation of the window, so a run nobody is watching draws nothing at all.
    """
    plan = plan_for(Pipeline(nodes=(node("d", "banded"), node("b", "bare"))))

    results = run(plan, ListSource(), show=("d",))

    assert [result.index for result in results] == [20, 21, 22]
    assert DRAWN == [20, 21, 22]
    for result in results:
        assert set(result.displays) == {"d"}
        drawn = result.displays["d"]
        assert set(drawn) == {DisplaySurface.TRACE}
        assert drawn[DisplaySurface.TRACE].index == result.index
    # Nothing was asked of `b`, and the surface is not something a node emits:
    # what it computed is in `outputs` and there is no picture beside it.
    assert all("b" not in result.displays for result in results)
    assert all(set(result.outputs) == {"d", "b"} for result in results)


def test_a_run_nobody_watches_draws_no_declared_surface() -> None:
    """The default is empty, which is every headless run of the same graph.

    `sieve run` and the oracle execute the same plan through the same loop, and
    a channel filled by default would charge both of them a derivation whose
    only consumer is a panel that is not open.
    """
    plan = plan_for(Pipeline(nodes=(node("d", "banded"),)))

    results = run(plan, ListSource())

    assert not DRAWN
    assert all(result.displays == {} for result in results)


def test_a_declared_surface_the_tool_leaves_empty_is_refused() -> None:
    """Declared and not filled, caught where registration cannot see it.

    The spec says which pictures this tool draws; only the call can say whether
    it drew them. A filler that quietly stopped returning one would leave the
    band's handles over a plot that never repaints, which looks like footage
    that is not moving.
    """
    plan = plan_for(Pipeline(nodes=(node("d", "banded", flaw="empty"),)))

    with pytest.raises(UndrawableNodeError, match=r"left \['trace'\] empty"):
        run(plan, ListSource(), show=("d",))


def test_a_declared_surface_is_the_whole_of_what_a_tool_may_draw() -> None:
    """The other direction: a picture no band names is refused too.

    Symmetry with the emission list and for its reason — a surface nothing
    declared is a derivation run every frame that no parameter reads, and the
    only way to notice it is to be told.
    """
    plan = plan_for(Pipeline(nodes=(node("d", "banded", flaw="surplus"),)))

    with pytest.raises(UndrawableNodeError, match=r"filled \['scalogram'\]"):
        run(plan, ListSource(), show=("d",))


def test_a_declared_surface_drawn_for_another_frame_is_refused() -> None:
    """`_run_node`'s index check for the channel that is never stored.

    Nothing here can be served back later as the wrong frame's result, because
    nothing here is stored. What a wrong index costs instead is the picture's x
    axis: a surface is plotted against the frames the run yielded, so a column
    filed at the end of its own window shifts the whole plot by the lookahead
    while the trace it is compared against does not move.
    """
    plan = plan_for(Pipeline(nodes=(node("d", "banded_ahead", flaw="offset"),)))

    with pytest.raises(UndrawableNodeError, match=r"drew \['trace'\] for a frame other than"):
        run(plan, ListSource(), show=("d",))


def test_a_node_with_no_declared_surface_cannot_be_watched() -> None:
    """Refused up front, before a frame is read — `_bind`'s argument.

    A caller watching a node that draws nothing has asked for a picture this
    graph cannot produce, and the answer was available before the lead-in
    decoded. `RefusingSource` is what says "before": a counter would be
    satisfied by a reader that was called and ignored.
    """
    plan = plan_for(Pipeline(nodes=(node("b", "bare"),)))

    with pytest.raises(UndrawableNodeError, match=r"b \(bare 1.0.0\) declares no display surface"):
        run(plan, RefusingSource(), show=("b",))


def test_a_declared_surface_is_never_served_from_the_store() -> None:
    """Watching a node costs it its cache, and that is the cheaper wrong answer.

    A hit skips the call, and the display channel was never in the store to be
    skipped with it — so a watched node reading the store would draw only the
    frames that missed. The run still *writes* what it computed, so the cost is
    this run's re-use and not the next one's.
    """
    plan = plan_for(Pipeline(nodes=(node("d", "banded"),)))
    store = MemoryFrameStore()

    first = run(plan, ListSource(), store=store)
    assert len(store) == 3
    assert [result.from_cache for result in first] == [frozenset()] * 3
    CALLS.clear()
    DRAWN.clear()

    # Unwatched, the same plan over the same store is answered entirely from it.
    assert [result.from_cache for result in run(plan, ListSource(), store=store)] == [
        frozenset({"d"})
    ] * 3
    assert not CALLS
    CALLS.clear()

    watched = run(plan, ListSource(), store=store, show=("d",))

    assert [call[0] for call in CALLS] == [20, 21, 22]
    assert [result.from_cache for result in watched] == [frozenset()] * 3
    assert DRAWN == [20, 21, 22]
