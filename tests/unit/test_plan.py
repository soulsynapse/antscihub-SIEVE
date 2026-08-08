"""What a plan has to get right before anything is decoded.

Five claims, each failing for its own reason. A window has two sides, and both
are the maximum over a node's paths rather than a sum over its nodes — the two
differ the moment a graph forks. Both sides are counted in *source* frames, so a
rate-changing node between the source and a window multiplies them rather than
passing them through. Which frames are in the answer comes from the graph, and
the wider range the reader is asked for is an optimization over it rather than a
second answer. Every node's parameters are validated, including the ones
`Dag.node_keys` never hashes and therefore never checked. And the format the
reader is opened in is the graph's answer, asked once.

Two cases here are neither a claim about a plan's contents nor carried from v2:
each pins one line the other fourteen leave free — the fold's closing maximum,
which a single-root graph satisfies under `min` as readily as under `max`, and
the refusal of a rate no input could satisfy.

The second side is v3's. v2's window only ever trailed, so its plan asked for
frames before the span and never after; a tool declaring `lookahead_frames`
needs the frames after its target to exist in the decode range or the executor
has nothing to delay emission *for* (`adr/detector-is-a-node.md`).
"""

from __future__ import annotations

from fractions import Fraction
from typing import assert_type

import pytest
from pydantic import Field

from sieve.core.pipeline_model import Edge, Node, Pipeline, Replicate, SourceSpan
from sieve.core.tool_base import (
    ArraySpec,
    ElementRelation,
    Emission,
    Mode,
    ParamsBase,
    ParamStereotype,
    PathStep,
    WarmupKind,
    source_warmup_frames,
)
from sieve.core.tool_registry import ToolRegistry, register_tool
from sieve.core.types import NO_FRAMES, ChannelSpec, FrameCount, FrameIndex, FrameRange
from sieve.pipeline.dag import Dag, InvalidParamsError
from sieve.pipeline.plan import ExecutionPlan, _input_lookahead_frames

SOURCE = "footage|1|2"

#: A scratch shelf, not `REGISTRY` — `test_dag.py`'s reason: the process-wide one
#: is populated by tool modules at import, and registering into it would make
#: this file's behaviour depend on whether such an import had already happened.
SHELF = ToolRegistry()


def _settling(tool_id: str, warmup: int) -> type[ParamsBase]:
    """A streaming tool that needs `warmup` frames before it is trustworthy."""

    @register_tool(
        tool_id=tool_id,
        version="1.0.0",
        summary="Frames in, frames out, after a while.",
        accepts=ArraySpec(),
        emits=ArraySpec(),
        emissions=(Emission("out"),),
        element=ElementRelation.PRESERVED,
        settling_epsilon=0.0,
        warmup_kind=WarmupKind.BOUNDED,
        registry=SHELF,
    )
    class Params(ParamsBase):
        @classmethod
        def max_warmup_frames(cls) -> FrameCount:
            return FrameCount(warmup)

    return Params


def _centred(tool_id: str, warmup: int, lookahead: int) -> type[ParamsBase]:
    """A windowed tool declaring both sides of its window.

    `Mode.WINDOWED` is not decoration: `ToolSpec` refuses a nonzero lookahead on
    a streaming tool, because a node that emits on consumption has no later
    frame it could have read.
    """

    @register_tool(
        tool_id=tool_id,
        version="1.0.0",
        summary="Reads around the frame it emits.",
        accepts=ArraySpec(),
        emits=ArraySpec(),
        emissions=(Emission("out"),),
        element=ElementRelation.PRESERVED,
        mode=Mode.WINDOWED,
        settling_epsilon=0.0,
        # `None` where the window has no near side: a kind with nothing to
        # settle is refused, which the `ahead*` tools are the case for.
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

    return Params


_settling("settle1", 1)
_settling("settle3", 3)
_settling("settle5", 5)
_centred("ahead2", 0, 2)
_centred("ahead5", 0, 5)
_centred("centre2", 2, 2)


@register_tool(
    tool_id="decimate",
    version="1.0.0",
    summary="Keep one frame in `factor`.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    emissions=(Emission("out"),),
    element=ElementRelation.PRESERVED,
    rate_changing=True,
    param_stereotypes={"factor": ParamStereotype.SCALAR_RANGE},
    registry=SHELF,
)
class DecimateParams(ParamsBase):
    factor: int = Field(default=10, ge=2)

    def output_rate(self) -> Fraction:
        return Fraction(1, self.factor)


@register_tool(
    tool_id="double",
    version="1.0.0",
    summary="Two frames out per frame in.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    emissions=(Emission("out"),),
    element=ElementRelation.PRESERVED,
    rate_changing=True,
    registry=SHELF,
)
class DoubleParams(ParamsBase):
    """The rate change `decimate` is the other side of.

    A rate above 1 is the only shape in which a node needs *fewer* source frames
    than something below it does, which is what separates the graph's answer from
    the largest number in the fold's table.
    """

    def output_rate(self) -> Fraction:
        return Fraction(2)


@register_tool(
    tool_id="stalled",
    version="1.0.0",
    summary="Declares a rate no quantity of input could satisfy.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    emissions=(Emission("out"),),
    element=ElementRelation.PRESERVED,
    rate_changing=True,
    registry=SHELF,
)
class StalledParams(ParamsBase):
    def output_rate(self) -> Fraction:
        return Fraction(0)


@register_tool(
    tool_id="keep",
    version="1.0.0",
    summary="Keep a range of the frames it is handed.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    emissions=(Emission("out"),),
    element=ElementRelation.PRESERVED,
    selecting=True,
    param_stereotypes={
        "first": ParamStereotype.SPAN,
        "last": ParamStereotype.SPAN,
    },
    registry=SHELF,
)
class KeepParams(ParamsBase):
    """A span, declared here rather than reached for from `sieve.tools`.

    `pipeline` may not import a tool, and a test that named `span` would be
    asserting against the one tool that exists rather than against the contract
    — which is the whole of what the plan reads.
    """

    first: int = 0
    last: int = 1_000_000

    def selected_frames(self) -> range:
        return range(self.first, self.last)


@register_tool(
    tool_id="jitter",
    version="1.0.0",
    summary="Never the same twice, so never keyed.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    emissions=(Emission("out"),),
    element=ElementRelation.PRESERVED,
    deterministic=False,
    param_stereotypes={"amount": ParamStereotype.SCALAR_RANGE},
    registry=SHELF,
)
class JitterParams(ParamsBase):
    amount: int = 1


@register_tool(
    tool_id="hue_band",
    version="1.0.0",
    summary="Reads colour: names the packed layouts and omits GRAY.",
    accepts=ArraySpec(channels=(ChannelSpec.RGB, ChannelSpec.BGR)),
    emits=ArraySpec(),
    emissions=(Emission("out"),),
    element=ElementRelation.PRESERVED,
    registry=SHELF,
)
class HueBandParams(ParamsBase):
    pass


def node(node_id: str, tool_id: str, **params: object) -> Node:
    return Node(node_id=node_id, tool_id=tool_id, version="1.0.0", params=dict(params))


def edges(*pairs: str) -> tuple[Edge, ...]:
    """`"a>b"` for each edge. Schema v1 gives an edge no port to name."""
    built: list[Edge] = []
    for pair in pairs:
        upstream, downstream = pair.split(">")
        built.append(Edge(upstream=upstream, downstream=downstream))
    return tuple(built)


def step(pipeline: Pipeline, node_id: str) -> PathStep:
    """One node's `(spec, params)`, for checking the walk against a definition."""
    dag = Dag.build(pipeline, SHELF)
    spec = dag.specs[node_id]
    return (spec, spec.params_model.model_validate(dag.pipeline.node(node_id).params))


#: The span these tests run over unless they are about the span. A module-level
#: constant rather than a default argument because a `SourceSpan` built in a
#: signature is built once at import and shared, which ruff's B008 is right to
#: flag even where the object is frozen.
DEFAULT_SPAN = SourceSpan(start=100, end=110)


def plan_for(
    pipeline: Pipeline,
    *,
    span: SourceSpan = DEFAULT_SPAN,
    replicate: Replicate | None = None,
    source: str = SOURCE,
) -> ExecutionPlan:
    return ExecutionPlan.build(
        Dag.build(pipeline, SHELF), source=source, span=span, replicate=replicate
    )


class TestTheWindowHasTwoSides:
    """Lead-in and lookahead: the same arithmetic on either side of a frame.

    v2 could state only the first. The claims that have to hold for the second
    are the first's claims restated, and they are asserted separately rather
    than by symmetry because a fold that computed one side and reused it for the
    other would satisfy every claim about the shape and none about the numbers.
    """

    def test_lead_in_is_the_longest_path_not_the_whole_graph(self) -> None:
        """A fork's two branches do not both charge for their warmup.

        ``a ─┬─> b`` with warmups 1, 5, 3. The chain through `b` wants 1+5 = 6
        ``   └─> c`` source frames and the chain through `c` wants 1+3 = 4, so
        the graph wants 6 — decoding once feeds both branches. Summing every
        node's declaration instead gives 9, which is the mistake this pins: it
        is not a crash, it is three frames of extra decode per request, forever.

        A fork rather than v2's diamond, because schema v1 refuses a second edge
        into one node — a join is the shape the fold's max-over-paths argument
        was written against, and a fork is what is left of it that a document can
        express. The mistake it catches is unchanged: `max` and `sum` still
        disagree.
        """
        pipeline = Pipeline(
            nodes=(
                node("a", "settle1"),
                node("b", "settle5"),
                node("c", "settle3"),
            ),
            edges=edges("a>b", "a>c"),
        )

        assert plan_for(pipeline).lead_in == FrameCount(6)
        # And the walk agrees with the single-path definition it is a fold of,
        # taken over each root-to-leaf chain by hand.
        assert max(
            source_warmup_frames([step(pipeline, "a"), step(pipeline, "b")]),
            source_warmup_frames([step(pipeline, "a"), step(pipeline, "c")]),
        ) == FrameCount(6)

    def test_lookahead_is_the_longest_path_not_the_whole_graph(self) -> None:
        """The same fork, on the other side of the frame being emitted.

        ``a ─┬─> b`` with lookaheads 0, 5, 2. The chain through `b` wants 5
        ``   └─> c`` frames past the target and the chain through `c` wants 2,
        so the graph reads 5 ahead. Summed it would be 7, and the cost of that
        is not extra decode but extra *latency*: the executor cannot emit frame
        `i` until it has read `i + lookahead`, so an over-stated lookahead
        delays every preview by the difference.
        """
        pipeline = Pipeline(
            nodes=(
                node("a", "settle1"),
                node("b", "ahead5"),
                node("c", "ahead2"),
            ),
            edges=edges("a>b", "a>c"),
        )

        assert plan_for(pipeline).lookahead == FrameCount(5)

    def test_two_roots_disagree_and_the_graph_decodes_for_the_larger(self) -> None:
        """The fold's *closing* maximum, which a single-root graph leaves free.

        Every other pipeline in this file has one root, so
        `max(need[root] for root in dag.roots)` returns its only operand and
        returns the same under `min` — measured in `findings/loop/2026.08.07-a-
        fold-has-two-maxima-and-one-fork-fixture-exercises-the-inner-one.md`.
        Two unconnected roots is what hands it two operands: one decode feeds
        both, so the graph wants the larger, and `min` under-warms the deeper
        branch by the difference with nothing to show for it.
        """
        disconnected = Pipeline(nodes=(node("a", "settle1"), node("b", "settle5")))

        assert plan_for(disconnected).lead_in == FrameCount(5)

        # The graph above does not separate the roots from `dag.order`: `need`
        # only grows towards a root, so ranging over every node would agree with
        # it. A root that emits *more* frames than it consumes is what breaks
        # that — `s` wants five of `d`'s frames, which is three of the source's —
        # so here the graph's answer is smaller than a number in the table it is
        # folded from, and only the roots give it.
        above_a_doubling = Pipeline(
            nodes=(node("d", "double"), node("s", "settle5"), node("c", "settle1")),
            edges=edges("d>s"),
        )

        assert plan_for(above_a_doubling).lead_in == FrameCount(3)

    def test_lead_in_crosses_a_rate_change_in_source_frames(self) -> None:
        """Five frames of warmup behind a 10:1 decimator is fifty source frames.

        The failure this closes is silent: a plain sum asks for 5, the preview
        renders, and the tool it was meant to warm has settled a tenth of the
        way.
        """
        pipeline = Pipeline(
            nodes=(node("d", "decimate", factor=10), node("s", "settle5")),
            edges=edges("d>s"),
        )

        assert plan_for(pipeline).lead_in == FrameCount(50)

    def test_lookahead_crosses_a_rate_change_in_source_frames(self) -> None:
        """The conversion is the window's, not the lead-in's.

        Five frames of *lookahead* behind the same decimator is fifty source
        frames for the same reason, and the reason a separate case pins it is
        that the two folds are separate code: a lookahead fold that forgot
        `at_input_of` would agree with this graph's lead-in — zero — and be
        wrong by the decimation factor everywhere a window sits behind a rate
        change.
        """
        pipeline = Pipeline(
            nodes=(node("d", "decimate", factor=10), node("a", "ahead5")),
            edges=edges("d>a"),
        )

        assert plan_for(pipeline).lookahead == FrameCount(50)

    def test_a_centred_window_widens_the_decode_range_at_both_ends(self) -> None:
        """What the second side is for: the range is wider than the answer twice.

        A centred window of length 5 is 2 of lead-in and 2 of lookahead, and
        both are frames the reader must supply for frames it will not be asked
        about. v2's plan could widen only the leading end, so the last two
        frames of every span would be computed from a window running off the end
        of the request — no error, a plausible frame, and the tuning done
        against it wrong rather than absent.
        """
        plan = plan_for(Pipeline(nodes=(node("w", "centre2"),)))

        assert (plan.lead_in, plan.lookahead) == (FrameCount(2), FrameCount(2))
        assert plan.span == SourceSpan(start=100, end=110)
        assert plan.decode_range == range(98, 112)
        assert_type(plan.decode_start, FrameIndex)
        assert_type(plan.decode_range, FrameRange)


class TestSelection:
    """Which frames are in the answer, and why the decode range is free to differ.

    The span is a node rather than an argument to `build`, so two runs of one
    graph over different stretches are two graphs. These are the things that have
    to hold for the pushdown underneath it to stay an optimization.
    """

    def test_a_selecting_node_narrows_what_the_caller_asked_for(self) -> None:
        # The claim itself: the answer's frames come from the graph. Asserted
        # against a request that is *wider* on both sides, so a fold that took
        # either bound from the wrong operand fails here rather than agreeing by
        # coincidence.
        plan = plan_for(
            Pipeline(nodes=(node("k", "keep", first=102, last=108),)),
            span=SourceSpan(start=100, end=110),
        )

        assert plan.span == SourceSpan(start=102, end=108)

    def test_the_decode_range_still_widens_at_both_ends(self) -> None:
        """The pushdown is over the span; it does not swallow the window.

        This is the whole of "changes nothing about the result", and it is v2's
        case with the second side added: the reader is asked for frames the
        answer does not contain at *both* ends — two before and two after, here
        — and a fold that had narrowed the decode range to the declared span
        instead would leave the window unfilled at each boundary while reporting
        the same frame count and the same `warmed`.
        """
        plan = plan_for(
            Pipeline(
                nodes=(node("k", "keep", first=102, last=108), node("w", "centre2")),
                edges=edges("k>w"),
            ),
            span=SourceSpan(start=100, end=110),
        )

        assert (plan.span.start, plan.span.end) == (102, 108)
        assert plan.decode_range == range(100, 110)
        assert FrameIndex(plan.span.start) - plan.decode_start == FrameCount(2)
        assert plan.decode_range.stop - FrameIndex(plan.span.end) == FrameCount(2)
        assert plan.warmed

    def test_where_the_node_sits_does_not_change_which_frames_are_kept(self) -> None:
        """One graph has one frame set, so a selection is the run's, not a branch's.

        Placing the node at a leaf is advice about which cache entries its
        parameters reach. If placement moved the answer as well, the advice would
        be a correctness rule wearing a performance argument's clothes.
        """
        first = plan_for(
            Pipeline(
                nodes=(node("k", "keep", first=102, last=108), node("s", "settle1")),
                edges=edges("k>s"),
            )
        )
        last = plan_for(
            Pipeline(
                nodes=(node("s", "settle1"), node("k", "keep", first=102, last=108)),
                edges=edges("s>k"),
            )
        )

        assert first.span == last.span == SourceSpan(start=102, end=108)

    def test_two_selections_intersect_and_an_empty_one_is_refused(self) -> None:
        # Intersection because every node computes the same frames: a graph
        # cannot hold one branch that ran over frames another did not. And an
        # empty result is refused rather than run, because a graph that computes
        # nothing and reports success is a result that looks better founded than
        # it is — the message names both ranges, which is what a reader needs to
        # know which one to move.
        overlapping = Pipeline(
            nodes=(node("a", "keep", first=100, last=108), node("b", "keep", first=104, last=120)),
            edges=edges("a>b"),
        )
        assert plan_for(overlapping).span == SourceSpan(start=104, end=108)

        disjoint = Pipeline(
            nodes=(node("a", "keep", first=100, last=104), node("b", "keep", first=106, last=120)),
            edges=edges("a>b"),
        )
        with pytest.raises(ValueError, match=r"nothing is left to compute.*100:110"):
            plan_for(disjoint)

    def test_a_selecting_node_is_hashed_like_any_other_node(self) -> None:
        """Which frames are in the answer is what the result is, so it is keyed.

        And the cost of putting the node at a root: its own key moves with its
        bounds, so anything downstream of it moves too. Both halves asserted,
        because a fold that skipped a selecting tool's params would pass every
        test above and leave two different answers sharing entries.
        """
        pipeline = Pipeline(
            nodes=(node("k", "keep", first=102, last=108), node("s", "settle1")),
            edges=edges("k>s"),
        )
        wider = Pipeline(
            nodes=(node("k", "keep", first=101, last=108), node("s", "settle1")),
            edges=edges("k>s"),
        )

        narrow, broad = plan_for(pipeline).keys, plan_for(wider).keys

        assert narrow["k"] != broad["k"]
        assert narrow["s"] != broad["s"]


def test_params_are_validated_even_where_no_key_is_derived() -> None:
    """A non-deterministic node is never hashed, so nothing else checks it.

    `Dag.node_keys` validates as a side effect of building a key and skips the
    nodes it cannot key. Without the plan, a misspelled parameter on a tool
    declaring `deterministic=False` reaches its kernel unchallenged.
    """
    pipeline = Pipeline(nodes=(node("j", "jitter", amonut=4),))

    assert "j" not in Dag.build(pipeline, SHELF).node_keys(source=SOURCE)
    with pytest.raises(InvalidParamsError):
        plan_for(pipeline)


def test_invalid_params_names_the_node_and_not_only_the_field() -> None:
    """The plan validates a call before the key walk does, so its refusal is the one read.

    `Dag.node_keys` wraps pydantic's error so the message carries the node id,
    and `build` validates the same nodes in the same order one statement
    earlier — so a plan that let the raw error out would make the wrapping
    unreachable from every caller that builds a plan, which is all of them.
    A misspelled key on a *cacheable* node is the case that separates the two:
    the walk would have refused this node itself.
    """
    pipeline = Pipeline(
        nodes=(node("smooth", "settle1"), node("smooth-again", "settle5", radiuz=3)),
        edges=edges("smooth>smooth-again"),
    )

    with pytest.raises(InvalidParamsError, match="smooth-again") as raised:
        plan_for(pipeline)

    assert raised.value.node_id == "smooth-again"
    # The field survives the wrapping, for `test_dag.py`'s reason: a caller that
    # wants the cursor on the offending parameter reads the original.
    assert raised.value.error.errors()[0]["loc"] == ("radiuz",)
    # And the walk one statement later refuses the same node, so what the plan
    # raises is the walk's rejection reached earlier rather than a second one.
    with pytest.raises(InvalidParamsError, match="smooth-again"):
        Dag.build(pipeline, SHELF).node_keys(source=SOURCE)


def test_a_span_near_the_start_runs_under_warmed_rather_than_failing() -> None:
    """Frame 0 cannot be warmed, and refusing would make it untunable.

    The shortfall is reported rather than raised, because no footage would fix
    it and a preview scrubbed to the opening of a video is an ordinary thing to
    want.
    """
    plan = plan_for(Pipeline(nodes=(node("s", "settle5"),)), span=SourceSpan(start=2, end=6))

    assert plan.lead_in == FrameCount(5)
    assert plan.decode_start == 0
    assert plan.decode_range == FrameRange(0, 6)
    assert plan.lead_in_shortfall == FrameCount(3)
    assert not plan.warmed


def test_the_replicates_overrides_reach_the_resolved_params() -> None:
    """Per-replicate deviation is what the plan runs with, not `Node.params`.

    Schema v1 has no `Replicate.roi` to carry a geometry beside the override —
    a replicate's box is the crop node's region parameter, deviated through this
    same path (`adr/detector-is-a-node.md`), so this case now covers both.
    """
    pipeline = Pipeline(nodes=(node("j", "jitter", amount=1), node("k", "keep", first=100)))
    replicate = Replicate(name="arena 2").with_override("j", {"amount": 9})
    elsewhere = replicate.with_override("k", {"first": 104})

    plan = plan_for(pipeline, replicate=replicate)

    assert plan.params["j"].model_dump() == {"amount": 9}
    assert plan.replicate is replicate
    # And the same replicate reaches the keys, not only the params. The two are
    # separate arguments to two separate calls inside `build`, so a plan that
    # resolved one and defaulted the other would run this arena's settings and
    # write the result under the baseline's key — a wrong answer with no symptom.
    assert plan.keys["k"] != plan_for(pipeline, replicate=elsewhere).keys["k"]


def test_a_non_positive_output_rate_is_refused_on_the_lookahead_side() -> None:
    """A rate of zero is an output frame no quantity of input could supply.

    Asserted at the fold rather than only through `build`, which cannot tell the
    two sides apart: `input_warmup_frames` carries the identical guard and the
    lead-in is folded first, so the warmup twin answers for both graphs below and
    the refusal declared on this side would survive its own deletion
    (`todo/a-declared-refusal-that-only-the-lookahead-side-proves.md` holds the
    twin). What the deletion costs is the tool's name: `at_input_of` refuses the
    same rate one call later and names only the number, which in a graph of
    fifteen nodes is the difference between a fix and a search.
    """
    pipeline = Pipeline(nodes=(node("z", "stalled"),))

    with pytest.raises(ValueError, match=r"stalled: output_rate must be positive"):
        _input_lookahead_frames(step(pipeline, "z"), NO_FRAMES)
    # And the graph is refused rather than planned, which is the `ValueError`
    # `build` declares — reached one fold earlier, from the warmup side.
    with pytest.raises(ValueError, match=r"stalled: output_rate must be positive"):
        plan_for(pipeline)


def test_the_reader_format_is_the_graphs_answer_and_not_a_choice() -> None:
    """`luma` is `not dag.needs_chroma`, which is what the source key hashed.

    Asked here rather than decided at the call site, because a reader handing
    BGR to a graph keyed for luma fills the store with correctly-shaped frames
    computed from the wrong pixels, and the symptom is a preview that looks
    plausible.
    """
    assert plan_for(Pipeline(nodes=(node("s", "settle1"),))).luma
    assert not plan_for(Pipeline(nodes=(node("h", "hue_band"),))).luma
