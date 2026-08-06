"""What a plan has to get right before anything is decoded.

Four claims, each failing for its own reason. Lead-in is the maximum over a
node's paths rather than a sum over its nodes, and the two differ the moment a
graph forks. Lead-in is counted in *source* frames, so a rate-changing node
between the source and a warmup multiplies it rather than passing it through.
Which frames are in the answer comes from the graph, and the wider range the
reader is asked for is an optimization over it rather than a second answer. And
every node's parameters are validated, including the ones `Dag.node_keys` never
hashes and therefore never checked.
"""

from __future__ import annotations

from fractions import Fraction

import pytest
from pydantic import Field, ValidationError

from sieve.backend.dispatch import Backend
from sieve.core.filter_base import ArraySpec, CostEstimate, ElementRelation, ParamsBase
from sieve.core.filter_registry import FilterRegistry, register_filter
from sieve.core.pipeline_model import ClipRange, Edge, Node, Pipeline
from sieve.core.replicates import Replicate
from sieve.core.types import ROI, FrameCount
from sieve.pipeline.dag import Dag
from sieve.pipeline.plan import ExecutionPlan, root_paths

COST = CostEstimate(seconds_per_megapixel=0.001)
SOURCE = "footage|1|2"
SHELF = FilterRegistry()


def _settling(filter_id: str, warmup: FrameCount) -> type[ParamsBase]:
    """A streaming filter that needs `warmup` frames before it is trustworthy."""

    @register_filter(
        filter_id=filter_id,
        version="1.0.0",
        summary="Frames in, frames out, after a while.",
        accepts=ArraySpec(),
        emits=ArraySpec(),
        element=ElementRelation.PRESERVED,
        cost=COST,
        warmup_frames=warmup,
        registry=SHELF,
    )
    class Params(ParamsBase):
        pass

    return Params


_settling("settle1", FrameCount(1))
_settling("settle3", FrameCount(3))
_settling("settle5", FrameCount(5))


@register_filter(
    filter_id="join1",
    version="1.0.0",
    summary="Two frames in, one out, after a frame of settling.",
    accepts={"left": ArraySpec(), "right": ArraySpec()},
    emits=ArraySpec(),
    element=ElementRelation.PRESERVED,
    cost=COST,
    warmup_frames=FrameCount(1),
    registry=SHELF,
)
class Join1Params(ParamsBase):
    pass


@register_filter(
    filter_id="decimate",
    version="1.0.0",
    summary="Keep one frame in `factor`.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    element=ElementRelation.PRESERVED,
    cost=COST,
    rate_changing=True,
    registry=SHELF,
)
class DecimateParams(ParamsBase):
    factor: int = Field(default=10, ge=2)

    def output_rate(self) -> Fraction:
        return Fraction(1, self.factor)


@register_filter(
    filter_id="keep",
    version="1.0.0",
    summary="Keep a range of the frames it is handed.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    element=ElementRelation.PRESERVED,
    cost=COST,
    selecting=True,
    registry=SHELF,
)
class KeepParams(ParamsBase):
    """A span, declared here rather than reached for from `sieve.filters`.

    `pipeline` may not import a filter, and a test that named `span` would be
    asserting against the one filter that exists rather than against the
    contract — which is the whole of what the plan reads.
    """

    first: int = 0
    last: int = 1_000_000

    def selected_frames(self) -> range:
        return range(self.first, self.last)


@register_filter(
    filter_id="jitter",
    version="1.0.0",
    summary="Never the same twice, so never keyed.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    element=ElementRelation.PRESERVED,
    cost=COST,
    deterministic=False,
    registry=SHELF,
)
class JitterParams(ParamsBase):
    amount: int = 1


def node(node_id: str, filter_id: str, **params: object) -> Node:
    return Node(node_id=node_id, filter_id=filter_id, version="1.0.0", params=dict(params))


def edges(*pairs: str) -> tuple[Edge, ...]:
    """`"a>b"` for each edge, or `"a>b:left"` to name the port it feeds."""
    built: list[Edge] = []
    for pair in pairs:
        upstream, target = pair.split(">")
        downstream, _, port = target.partition(":")
        built.append(
            Edge(upstream=upstream, downstream=downstream, port=port)
            if port
            else Edge(upstream=upstream, downstream=downstream)
        )
    return tuple(built)


#: The span these tests run over unless they are about the span. A module-level
#: constant rather than a default argument because a `ClipRange` built in a
#: signature is built once at import and shared, which ruff's B008 is right to
#: flag even where the object is frozen.
DEFAULT_SPAN = ClipRange(start=100, end=110)


def plan_for(
    pipeline: Pipeline,
    *,
    span: ClipRange = DEFAULT_SPAN,
    replicate: Replicate | None = None,
    source: str = SOURCE,
    pre_cropped: bool = False,
    source_start: int = 0,
) -> ExecutionPlan:
    return ExecutionPlan.build(
        Dag.build(pipeline, SHELF),
        source=source,
        span=span,
        backend=Backend.CPU,
        replicate=replicate,
        pre_cropped=pre_cropped,
        source_start=source_start,
    )


def test_lead_in_is_the_longest_path_not_the_whole_graph() -> None:
    """A fork's two branches do not both charge for their warmup.

    ``a ─┬─> b ─┬─> d`` with warmups 1, 5, 3, 1. The path through `b` wants
    ``    └─> c ─┘``   1+5+1 = 7 source frames and the path through `c` wants
    1+3+1 = 5, so the graph wants 7 — decoding once feeds both branches. Summing
    every node's declaration instead gives 10, which is the mistake this pins:
    it is not a crash, it is three frames of extra decode per request, forever.

    `d` is a two-port join because it has to be — a node with two upstreams
    declares two ports now — and its warmup is denominated at its own input
    exactly as a single-input filter's is, so the arithmetic is unchanged.
    """
    pipeline = Pipeline(
        nodes=(
            node("a", "settle1"),
            node("b", "settle5"),
            node("c", "settle3"),
            node("d", "join1"),
        ),
        edges=edges("a>b", "a>c", "b>d:left", "c>d:right"),
    )
    assert plan_for(pipeline).lead_in == FrameCount(7)
    # And the walk agrees with the definition it is an optimization of.
    assert len(root_paths(Dag.build(pipeline, SHELF), "d")) == 2


def test_lead_in_crosses_a_rate_change_in_source_frames() -> None:
    """Five frames of warmup behind a 10:1 decimator is fifty source frames.

    The failure this closes is silent: a plain sum asks for 5, the preview
    renders, and the filter it was meant to warm has settled a tenth of the way.
    """
    pipeline = Pipeline(
        nodes=(node("d", "decimate", factor=10), node("s", "settle5")),
        edges=edges("d>s"),
    )
    assert plan_for(pipeline).lead_in == FrameCount(50)


class TestSelection:
    """Which frames are in the answer, and why the decode range is free to differ.

    `docs/todo/the-span-is-a-filter.md`. The span used to be an argument to
    `build` and nothing else, so two runs of one graph over different stretches
    were the same graph. It is a node now, and these are the things that have to
    hold for the pushdown underneath it to stay an optimization.
    """

    def test_a_selecting_node_narrows_what_the_caller_asked_for(self) -> None:
        # The claim itself: the answer's frames come from the graph. Asserted
        # against a request that is *wider* on both sides, so a fold that took
        # either bound from the wrong operand fails here rather than agreeing
        # by coincidence.
        plan = plan_for(
            Pipeline(nodes=(node("k", "keep", first=102, last=108),)),
            span=ClipRange(start=100, end=110),
        )

        assert plan.span == ClipRange(start=102, end=108)

    def test_the_decode_range_still_widens_by_the_lead_in(self) -> None:
        """The pushdown is over the span; it does not swallow the warmup.

        This is the whole of "changes nothing about the result". The reader is
        asked for frames the answer does not contain — five of them, here — and
        a fold that had narrowed `decode_range` to the declared span instead
        would leave `settle5` unsettled for the first five frames of every run
        while reporting the same frame count and the same `warmed`.
        """
        plan = plan_for(
            Pipeline(
                nodes=(node("k", "keep", first=102, last=108), node("s", "settle5")),
                edges=edges("k>s"),
            ),
            span=ClipRange(start=100, end=110),
        )

        assert (plan.span.start, plan.decode_start) == (102, 97)
        assert plan.decode_range == range(97, 108)
        assert plan.warmed

    def test_where_the_node_sits_does_not_change_which_frames_are_kept(self) -> None:
        """One graph has one frame set, so a selection is the run's, not a branch's.

        `span.md` tells a reader to put the node at a leaf, and that advice is
        purely about which cache entries its parameters reach. If placement
        moved the answer as well, the advice would be a correctness rule wearing
        a performance argument's clothes.
        """
        first = plan_for(
            Pipeline(
                nodes=(node("k", "keep", first=102, last=108), node("s", "settle1")),
                edges=edges("k>s"),
            ),
        )
        last = plan_for(
            Pipeline(
                nodes=(node("s", "settle1"), node("k", "keep", first=102, last=108)),
                edges=edges("s>k"),
            ),
        )

        assert first.span == last.span == ClipRange(start=102, end=108)

    def test_two_selections_intersect_and_an_empty_one_is_refused(self) -> None:
        # Intersection because every node computes the same frames: a graph
        # cannot hold one branch that ran over frames another did not. And an
        # empty result is refused rather than run, because a graph that computes
        # nothing and reports success is rule 6's failure exactly — the message
        # names both ranges, which is what a reader needs to know which to move.
        overlapping = Pipeline(
            nodes=(node("a", "keep", first=100, last=108), node("b", "keep", first=104, last=120)),
            edges=edges("a>b"),
        )
        assert plan_for(overlapping).span == ClipRange(start=104, end=108)

        disjoint = Pipeline(
            nodes=(node("a", "keep", first=100, last=104), node("b", "keep", first=106, last=120)),
            edges=edges("a>b"),
        )
        with pytest.raises(ValueError, match=r"nothing is left to compute.*100:110"):
            plan_for(disjoint)

    def test_a_selecting_node_is_hashed_like_any_other_node(self) -> None:
        """Which frames are in the answer is what the result is, so it is keyed.

        And the cost `span.md` is made of: the node's own key moves with its
        bounds, so anything downstream of it moves too. Both halves asserted,
        because a fold that skipped a selecting filter's params would pass every
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
    nodes it cannot key. Before the plan, a misspelled parameter on a filter
    declaring `deterministic=False` reached its kernel unchallenged.
    """
    pipeline = Pipeline(nodes=(node("j", "jitter", amonut=4),))
    assert "j" not in Dag.build(pipeline, SHELF).node_keys(source=SOURCE, backend=Backend.CPU)
    with pytest.raises(ValidationError):
        plan_for(pipeline)


def test_a_clip_near_the_start_runs_under_warmed_rather_than_failing() -> None:
    """Frame 0 cannot be warmed, and refusing would make it untunable.

    The shortfall is reported rather than raised, because no footage would fix
    it and a preview scrubbed to the opening of a video is an ordinary thing to
    want.
    """
    pipeline = Pipeline(nodes=(node("s", "settle5"),))
    plan = plan_for(pipeline, span=ClipRange(start=2, end=6))
    assert plan.lead_in == FrameCount(5)
    assert plan.decode_start == 0
    assert plan.decode_range == range(0, 6)
    assert plan.lead_in_shortfall == FrameCount(3)
    assert not plan.warmed


def test_the_replicates_overrides_reach_the_resolved_params() -> None:
    """Per-replicate deviation is what the plan runs with, not `Node.params`."""
    pipeline = Pipeline(nodes=(node("j", "jitter", amount=1),))
    replicate = Replicate(name="arena 2", roi=ROI(x=0, y=0, width=8, height=8)).with_override(
        "j", {"amount": 9}
    )
    plan = plan_for(pipeline, replicate=replicate)
    assert plan.params["j"].model_dump() == {"amount": 9}


class TestPlanningAgainstACropThatAlreadyExists:
    """`pre_cropped` and `source_start`: what a run over an artifact changes.

    Three separable claims, because the child-source model splits one fact into
    three and the parts fail independently. The ROI stops applying (the crop
    happened on disk). The overrides do *not* stop applying (they are about
    parameters, not pixels). And the footage begins partway into the source's
    numbering, which is a shortfall to report rather than a frame to demand.
    """

    def test_the_replicates_region_leaves_both_the_crop_and_the_key(self) -> None:
        """A crop of a crop is the one wrong answer available here.

        `plan.roi` is what the executor cuts with and what the root key names,
        and over an artifact both must be nothing. If only one of them dropped
        the region, the run would either cut twice or key the correct pixels
        under a claim of a region nobody applied.
        """
        pipeline = Pipeline(nodes=(node("s", "settle1"),))
        arena = Replicate(name="arena 1", roi=ROI(x=4, y=4, width=8, height=8))

        over_parent = plan_for(pipeline, replicate=arena)
        over_artifact = plan_for(pipeline, replicate=arena, pre_cropped=True)
        whole_frame = plan_for(pipeline)

        assert over_parent.roi == arena.roi
        assert over_artifact.roi is None
        # And the key follows the ROI rather than the `replicate` argument:
        # with no overrides in play, an uncropped run over this source is keyed
        # identically however the arena reached it.
        assert over_artifact.keys == whole_frame.keys
        assert over_artifact.keys != over_parent.keys

    def test_the_overrides_survive_the_crop_leaving(self) -> None:
        """`pre_cropped` is not `replicate=None`, and this is the difference.

        The cheap way to say "no ROI" would have been to plan the artifact with
        no replicate at all. That silently reverts every per-arena parameter pin
        to the node's baseline — a wrong answer with no symptom, since the run
        completes and reports the same frame count.
        """
        pipeline = Pipeline(nodes=(node("j", "jitter", amount=1),))
        arena = Replicate(name="arena 2", roi=ROI(x=0, y=0, width=8, height=8)).with_override(
            "j", {"amount": 9}
        )

        plan = plan_for(pipeline, replicate=arena, pre_cropped=True)

        assert plan.params["j"].model_dump() == {"amount": 9}
        assert plan.replicate is arena

    def test_lead_in_before_the_artifact_begins_is_a_shortfall_not_a_request(self) -> None:
        """The clamp at frame 0, applied once more at the artifact's own start.

        A crop covering exactly the clip can never supply a warmup reaching
        before it, from any file. Without the floor the plan would ask the
        reader for frames the artifact does not hold, and a run over footage
        that is entirely correct would fail.
        """
        pipeline = Pipeline(nodes=(node("s", "settle5"),))

        plan = plan_for(pipeline, span=ClipRange(start=40, end=46), source_start=40)

        assert plan.lead_in == FrameCount(5)
        assert plan.decode_start == 40
        assert plan.decode_range == range(40, 46)
        assert plan.lead_in_shortfall == FrameCount(5)
        assert not plan.warmed
