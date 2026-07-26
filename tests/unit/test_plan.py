"""What a plan has to get right before anything is decoded.

Three claims, each failing for its own reason. Lead-in is the maximum over a
node's paths rather than a sum over its nodes, and the two differ the moment a
graph forks. Lead-in is counted in *source* frames, so a rate-changing node
between the source and a warmup multiplies it rather than passing it through.
And every node's parameters are validated, including the ones `Dag.node_keys`
never hashes and therefore never checked.
"""

from __future__ import annotations

from fractions import Fraction

import pytest
from pydantic import Field, ValidationError

from sieve.backend.dispatch import Backend
from sieve.core.filter_base import ArraySpec, CostEstimate, ParamsBase
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
    """A streaming filter that needs `warmup` frames before it is trustworthy."""

    @register_filter(
        filter_id=filter_id,
        version="1.0.0",
        summary="Frames in, frames out, after a while.",
        accepts=ArraySpec(),
        emits=ArraySpec(),
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
    filter_id="decimate",
    version="1.0.0",
    summary="Keep one frame in `factor`.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
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
    cost=COST,
    deterministic=False,
    registry=SHELF,
)
class JitterParams(ParamsBase):
    amount: int = 1


def node(node_id: str, filter_id: str, **params: object) -> Node:
    return Node(node_id=node_id, filter_id=filter_id, version="1.0.0", params=dict(params))


def edges(*pairs: str) -> tuple[Edge, ...]:
    return tuple(Edge(upstream=pair.split(">")[0], downstream=pair.split(">")[1]) for pair in pairs)


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
) -> ExecutionPlan:
    return ExecutionPlan.build(
        Dag.build(pipeline, SHELF),
        source=SOURCE,
        span=span,
        backend=Backend.CPU,
        replicate=replicate,
    )


def test_lead_in_is_the_longest_path_not_the_whole_graph() -> None:
    """A fork's two branches do not both charge for their warmup.

    ``a ─┬─> b ─┬─> d`` with warmups 1, 5, 3, 1. The path through `b` wants
    ``    └─> c ─┘``   1+5+1 = 7 source frames and the path through `c` wants
    1+3+1 = 5, so the graph wants 7 — decoding once feeds both branches. Summing
    every node's declaration instead gives 10, which is the mistake this pins:
    it is not a crash, it is three frames of extra decode per request, forever.
    """
    pipeline = Pipeline(
        nodes=(
            node("a", "settle1"),
            node("b", "settle5"),
            node("c", "settle3"),
            node("d", "settle1"),
        ),
        edges=edges("a>b", "a>c", "b>d", "c>d"),
    )
    assert plan_for(pipeline).lead_in == 7
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
    assert plan_for(pipeline).lead_in == 50


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
    assert plan.lead_in == 5
    assert plan.decode_start == 0
    assert plan.decode_range == range(0, 6)
    assert plan.lead_in_shortfall == 3
    assert not plan.warmed


def test_the_replicates_overrides_reach_the_resolved_params() -> None:
    """Per-replicate deviation is what the plan runs with, not `Node.params`."""
    pipeline = Pipeline(nodes=(node("j", "jitter", amount=1),))
    replicate = Replicate(name="arena 2", roi=ROI(x=0, y=0, width=8, height=8)).with_override(
        "j", {"amount": 9}
    )
    plan = plan_for(pipeline, replicate=replicate)
    assert plan.params["j"].model_dump() == {"amount": 9}
