"""The walk equals the definition it is an optimization of.

`plan._lead_in` propagates a maximum backwards over the topological order and
never enumerates a path. That is only correct because `input_warmup_frames` is
monotone non-decreasing in its second argument, and monotonicity is a fact about
`ceil` and `+` that no amount of reading the walk will show. So the walk is
checked against the thing it replaced: for every root-to-node path in a random
DAG, `source_warmup_frames` of that path, maximized.

An example test cannot state this. Any particular graph is a graph the walk
could have been written to pass, and the failure mode being guarded against —
a graph shape where max-node-by-node and max-over-paths come apart — is
precisely the shape nobody thought to write down.

The generated graphs are deliberately dense in forks and rate changes, because
a chain has one path and would agree with anything.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any, ClassVar

from hypothesis import given
from hypothesis import strategies as st

from sieve.backend.dispatch import Backend
from sieve.core.filter_base import ArraySpec, CostEstimate, ParamsBase, source_warmup_frames
from sieve.core.filter_registry import FilterRegistry, register_filter
from sieve.core.pipeline_model import ClipRange, Edge, Node, Pipeline
from sieve.pipeline.dag import Dag
from sieve.pipeline.plan import ExecutionPlan, root_paths

COST = CostEstimate(seconds_per_megapixel=0.001)
SHELF = FilterRegistry()

#: Warmups a filter may declare. Kept small so a hundred-node graph's lead-in
#: stays a number a failure message can be read from, and 0 is included because
#: a node that contributes nothing is where an off-by-one in the fold hides.
WARMUPS = (0, 1, 2, 7)

#: Output frames per input frame. A rate change is what makes the fold
#: non-linear, so a generator without one would only ever be testing addition.
#:
#: **Not all of the form 1/n**, and that is the point of `2/3` and `3/2` being
#: here. A decimator's `need / rate` is `need * factor`, always exact, so a
#: generator of decimators alone cannot tell `ceil` from `floor` — the rounding
#: `source_warmup_frames` exists to get right would be untested by a suite that
#: looked thorough. Nothing in the contract restricts `output_rate` to a unit
#: numerator; a filter emitting two frames for every three is legal and is what
#: makes the division inexact.
RATES = (Fraction(1, 1), Fraction(1, 2), Fraction(1, 10), Fraction(2, 3), Fraction(3, 2))


#: The most upstreams a generated node can have: one per earlier node in a
#: seven-node graph. A filter declares its input ports, so a node with `k`
#: parents needs a spec with `k` ports registered ahead of time.
MAX_ARITY = 6


def _spec_id(warmup: int, rate: Fraction, arity: int) -> str:
    return f"w{warmup}_r{rate.numerator}_{rate.denominator}_a{arity}"


def _register(warmup: int, rate: Fraction, arity: int) -> type[ParamsBase]:
    """One filter per `(warmup, rate, arity)` triple, since all three are declarations.

    Two shapes rather than one parameterized shape, because `FilterSpec`
    refuses a filter that overrides `output_rate` without declaring
    `rate_changing` — a rate-changing filter at rate 1 is not a thing the
    contract allows, and working around that here would be testing a graph the
    system cannot hold. Arity joined the id when ports became declarations:
    the wiring rules demand a node's incoming edges fill its ports exactly, so
    a two-parent node must name a two-port filter. The lead-in walk treats
    every upstream alike — `warmup_frames` is denominated at *the node's*
    input — which is why one warmup covers all `arity` ports.
    """
    common: dict[str, Any] = {
        "version": "1.0.0",
        "summary": "Settles, and maybe resamples.",
        # The mapping form even at arity 1, so the generator speaks one port
        # vocabulary: every edge feeds `p<index>`, whatever the arity. A bare
        # `ArraySpec()` here would name the single port `in` and the wiring
        # check would refuse the generator's `p0`.
        "accepts": {f"p{port}": ArraySpec() for port in range(arity)},
        "emits": ArraySpec(),
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
        #: A `ClassVar` and not a field: the rate is part of this filter's
        #: identity, and a field would let a document set it, which would make
        #: two documents naming one filter mean two different conversions.
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
    """A random DAG, wired by only ever pointing backwards in a node list.

    Edges from a lower index to a higher one cannot form a cycle, so every
    generated graph is valid by construction and Hypothesis spends its budget
    on shapes rather than on rediscovering `CycleError`. Parents are drawn
    before the filter because the filter's arity must match: `k` parents fill
    the `k` ports of a `k`-ary filter, one each, in index order.
    """
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
