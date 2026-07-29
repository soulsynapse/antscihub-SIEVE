

















from __future__ import annotations

from fractions import Fraction
from typing import Any, ClassVar

from hypothesis import given
from hypothesis import strategies as st

from sieve.backend.dispatch import Backend
from sieve.core.filter_base import (
    ArraySpec,
    CostEstimate,
    ElementRelation,
    ParamsBase,
    source_warmup_frames,
)
from sieve.core.filter_registry import FilterRegistry, register_filter
from sieve.core.pipeline_model import ClipRange, Edge, Node, Pipeline
from sieve.pipeline.dag import Dag
from sieve.pipeline.plan import ExecutionPlan, root_paths

COST = CostEstimate(seconds_per_megapixel=0.001)
SHELF = FilterRegistry()




WARMUPS = (0, 1, 2, 7)











RATES = (Fraction(1, 1), Fraction(1, 2), Fraction(1, 10), Fraction(2, 3), Fraction(3, 2))





MAX_ARITY = 6


def _spec_id(warmup: int, rate: Fraction, arity: int) -> str:
    return f"w{warmup}_r{rate.numerator}_{rate.denominator}_a{arity}"


def _register(warmup: int, rate: Fraction, arity: int) -> type[ParamsBase]:












    common: dict[str, Any] = {
        "version": "1.0.0",
        "summary": "Settles, and maybe resamples.",




        "accepts": {f"p{port}": ArraySpec() for port in range(arity)},
        "emits": ArraySpec(),
        "element": ElementRelation.PRESERVED,
        "cost": COST,
        "warmup_frames": warmup,
        "registry": SHELF,
    }
    if rate == 1:

        @register_filter(filter_id=_spec_id(warmup, rate, arity), **common)
        class Unchanged(ParamsBase):
            pass

        return Unchanged

    @register_filter(filter_id=_spec_id(warmup, rate, arity), rate_changing=True, **common)
    class Resampling(ParamsBase):



        RATE: ClassVar[Fraction] = rate

        def output_rate(self) -> Fraction:
            return self.RATE

    return Resampling


for _warmup in WARMUPS:
    for _rate in RATES:
        for _arity in range(1, MAX_ARITY + 1):
            _register(_warmup, _rate, _arity)

_FILTER_IDS_BY_ARITY = {
    arity: tuple(_spec_id(w, r, arity) for w in WARMUPS for r in RATES)
    for arity in range(1, MAX_ARITY + 1)
}


@st.composite
def dags(draw: st.DrawFn) -> Pipeline:








    count = draw(st.integers(min_value=1, max_value=7))
    nodes: list[Node] = []
    edges: list[Edge] = []
    for index in range(count):
        parents = draw(
            st.lists(
                st.integers(min_value=0, max_value=index - 1) if index else st.nothing(),
                max_size=index,
                unique=True,
            )
        )
        arity = max(1, len(parents))
        filter_id = draw(st.sampled_from(_FILTER_IDS_BY_ARITY[arity]))
        nodes.append(Node(node_id=f"n{index}", filter_id=filter_id, version="1.0.0"))
        for port, parent in enumerate(parents):
            edges.append(Edge(upstream=f"n{parent}", downstream=f"n{index}", port=f"p{port}"))
    return Pipeline(nodes=tuple(nodes), edges=tuple(edges))


@given(dags())
def test_lead_in_equals_the_maximum_over_enumerated_paths(pipeline: Pipeline) -> None:
    dag = Dag.build(pipeline, SHELF)
    plan = ExecutionPlan.build(
        dag,
        source="footage|1|2",
        span=ClipRange(start=1000, end=1001),
        backend=Backend.CPU,
    )

    def cost(path: tuple[Node, ...]) -> int:
        return source_warmup_frames(
            [(dag.spec(step.node_id), plan.params[step.node_id]) for step in path]
        )

    brute = max(
        (cost(path) for node in dag.order for path in root_paths(dag, node.node_id)),
        default=0,
    )
    assert plan.lead_in == brute
