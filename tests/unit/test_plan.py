









from __future__ import annotations

from fractions import Fraction

import pytest
from pydantic import Field, ValidationError

from sieve.backend.dispatch import Backend
from sieve.core.filter_base import ArraySpec, CostEstimate, ElementRelation, ParamsBase
from sieve.core.filter_registry import FilterRegistry, register_filter
from sieve.core.pipeline_model import ClipRange, Edge, Node, Pipeline
from sieve.core.replicates import Replicate
from sieve.core.types import ROI
from sieve.pipeline.dag import Dag
from sieve.pipeline.plan import ExecutionPlan, root_paths

COST = CostEstimate(seconds_per_megapixel=0.001)
SOURCE = "footage|1|2"
SHELF = FilterRegistry()


def _settling(filter_id: str, warmup: int) -> type[ParamsBase]:


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


_settling("settle1", 1)
_settling("settle3", 3)
_settling("settle5", 5)


@register_filter(
    filter_id="join1",
    version="1.0.0",
    summary="Two frames in, one out, after a frame of settling.",
    accepts={"left": ArraySpec(), "right": ArraySpec()},
    emits=ArraySpec(),
    element=ElementRelation.PRESERVED,
    cost=COST,
    warmup_frames=1,
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












    pipeline = Pipeline(
        nodes=(
            node("a", "settle1"),
            node("b", "settle5"),
            node("c", "settle3"),
            node("d", "join1"),
        ),
        edges=edges("a>b", "a>c", "b>d:left", "c>d:right"),
    )
    assert plan_for(pipeline).lead_in == 7

    assert len(root_paths(Dag.build(pipeline, SHELF), "d")) == 2


def test_lead_in_crosses_a_rate_change_in_source_frames() -> None:





    pipeline = Pipeline(
        nodes=(node("d", "decimate", factor=10), node("s", "settle5")),
        edges=edges("d>s"),
    )
    assert plan_for(pipeline).lead_in == 50


def test_params_are_validated_even_where_no_key_is_derived() -> None:






    pipeline = Pipeline(nodes=(node("j", "jitter", amonut=4),))
    assert "j" not in Dag.build(pipeline, SHELF).node_keys(source=SOURCE, backend=Backend.CPU)
    with pytest.raises(ValidationError):
        plan_for(pipeline)


def test_a_clip_near_the_start_runs_under_warmed_rather_than_failing() -> None:






    pipeline = Pipeline(nodes=(node("s", "settle5"),))
    plan = plan_for(pipeline, span=ClipRange(start=2, end=6))
    assert plan.lead_in == 5
    assert plan.decode_start == 0
    assert plan.decode_range == range(0, 6)
    assert plan.lead_in_shortfall == 3
    assert not plan.warmed


def test_the_replicates_overrides_reach_the_resolved_params() -> None:

    pipeline = Pipeline(nodes=(node("j", "jitter", amount=1),))
    replicate = Replicate(name="arena 2", roi=ROI(x=0, y=0, width=8, height=8)).with_override(
        "j", {"amount": 9}
    )
    plan = plan_for(pipeline, replicate=replicate)
    assert plan.params["j"].model_dump() == {"amount": 9}


class TestPlanningAgainstACropThatAlreadyExists:









    def test_the_replicates_region_leaves_both_the_crop_and_the_key(self) -> None:







        pipeline = Pipeline(nodes=(node("s", "settle1"),))
        arena = Replicate(name="arena 1", roi=ROI(x=4, y=4, width=8, height=8))

        over_parent = plan_for(pipeline, replicate=arena)
        over_artifact = plan_for(pipeline, replicate=arena, pre_cropped=True)
        whole_frame = plan_for(pipeline)

        assert over_parent.roi == arena.roi
        assert over_artifact.roi is None



        assert over_artifact.keys == whole_frame.keys
        assert over_artifact.keys != over_parent.keys

    def test_the_overrides_survive_the_crop_leaving(self) -> None:







        pipeline = Pipeline(nodes=(node("j", "jitter", amount=1),))
        arena = Replicate(name="arena 2", roi=ROI(x=0, y=0, width=8, height=8)).with_override(
            "j", {"amount": 9}
        )

        plan = plan_for(pipeline, replicate=arena, pre_cropped=True)

        assert plan.params["j"].model_dump() == {"amount": 9}
        assert plan.replicate is arena

    def test_lead_in_before_the_artifact_begins_is_a_shortfall_not_a_request(self) -> None:







        pipeline = Pipeline(nodes=(node("s", "settle5"),))

        plan = plan_for(pipeline, span=ClipRange(start=40, end=46), source_start=40)

        assert plan.lead_in == 5
        assert plan.decode_start == 40
        assert plan.decode_range == range(40, 46)
        assert plan.lead_in_shortfall == 5
        assert not plan.warmed
