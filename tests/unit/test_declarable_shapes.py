"""Every shape the contract can declare either runs or says why it cannot.

REWORK.md R2, as a walk rather than as an assertion about the shapes somebody
happened to think of. The space is a product of the declarations that decide
which kernel protocol a node needs — `Mode`, `rate_changing`, and the stream
kind on each side — and it is built from the enums themselves, so it grows when
they do.

What this catches is not a wrong refusal; it is a *missing* one.
`emits=TableSpec(...)` bound cleanly for as long as `_bind` checked two fields
by name, and the only symptom was a kernel that could not be written: no
protocol returns rows, so the failure landed at the author's desk with nothing
naming the field they had declared. A shape that is refused is a shape somebody
can act on. A shape that binds and then has nothing to call is not.

The suite is the second instrument here and the weaker one. A third `Mode` or
`StreamKind` member is a pyright error inside `unrunnable_reason`'s
`assert_never` branches before it is a failure here — which is the right order,
since the gate that fires at the moment the member is written is the one that
gets read.
"""

from __future__ import annotations

import itertools
from fractions import Fraction

import numpy as np
import pytest

from sieve.backend.dispatch import Backend, KernelRegistry, unrunnable_reason
from sieve.core.filter_base import (
    ArraySpec,
    CostEstimate,
    ElementRelation,
    FilterSpec,
    Mode,
    ParamsBase,
    StreamKind,
    TableSpec,
)
from sieve.core.filter_registry import FilterRegistry
from sieve.core.pipeline_model import ClipRange, Edge, Node, Pipeline
from sieve.core.types import ChannelSpec, Frame
from sieve.pipeline.dag import Dag
from sieve.pipeline.executor import UnrunnableNodeError, execute
from sieve.pipeline.plan import ExecutionPlan

COST = CostEstimate(seconds_per_megapixel=0.001)
SOURCE = "footage|1|2"
SPAN = ClipRange(start=20, end=23)
WIDTH, HEIGHT = 32, 24

#: One point of the space: mode, whether it changes rate, what it accepts, what
#: it emits. A tuple rather than a dataclass because it is the `product` element
#: and every use of it destructures immediately.
Shape = tuple[Mode, bool, StreamKind, StreamKind]

#: The whole declarable space, derived from the enums rather than listed. Adding
#: a member to either enum doubles this, which is the property the walk is for.
SHAPES: tuple[Shape, ...] = tuple(itertools.product(Mode, (False, True), StreamKind, StreamKind))


class SteadyParams(ParamsBase):
    """A filter that emits one output per input."""


class HalvingParams(ParamsBase):
    """A filter that does not, so `rate_changing=True` is a legal declaration.

    `FilterSpec.__post_init__` refuses the flag without an override and the
    override without the flag, so a rate-changing point of the space cannot be
    declared with `SteadyParams` at all — the two params models here are what
    the *contract* requires, not scaffolding this test invented.
    """

    def output_rate(self) -> Fraction:
        return Fraction(1, 2)


class ListSource:
    """Frames from nowhere, counting the reads.

    Whether a read happened is half of what these tests assert, and a real
    decoder can only be asked that by timing it.
    """

    def __init__(self) -> None:
        self.reads: list[int] = []

    def read(self, index: int) -> Frame:
        self.reads.append(index)
        data = np.full((HEIGHT, WIDTH), index % 200, dtype=np.uint8)
        return Frame(data=data, index=index, channels=ChannelSpec.GRAY)


def _identity(frame: Frame, params: ParamsBase) -> Frame:
    """The minimal kernel, registered for every shape including the refused ones.

    Registering one for a shape that cannot run is deliberate: it is what makes
    a refusal below attributable to the declaration rather than to an empty
    shelf, which raises `NoKernelError` from the same call and would let this
    file pass while `unrunnable_reason` did nothing at all.
    """
    return frame


def _shape_id(shape: Shape) -> str:
    """A filter id, and pytest's case id, derived from the shape it names.

    Derived rather than typed: a table of sixteen literal ids is a second
    spelling of the product above, and it stops being total the moment an enum
    grows.
    """
    mode, rate_changing, accepts, emits = shape
    rate = "rate_changing" if rate_changing else "steady"
    return f"{mode}_{rate}_{accepts}_in_{emits}_out"


def _spec_for(shape: Shape) -> FilterSpec:
    mode, rate_changing, accepts, emits = shape
    return FilterSpec(
        filter_id=_shape_id(shape),
        version="1.0.0",
        summary="One point of the declarable shape space.",
        params_model=HalvingParams if rate_changing else SteadyParams,
        accepts=ArraySpec() if accepts is StreamKind.ARRAY else TableSpec(),
        emits=ArraySpec() if emits is StreamKind.ARRAY else TableSpec(),
        cost=COST,
        mode=mode,
        rate_changing=rate_changing,
        # Required of an array emitter and refused of a table one, so this is
        # the declaration the emits axis forces rather than a choice.
        element=ElementRelation.PRESERVED if emits is StreamKind.ARRAY else None,
    )


SHELF = FilterRegistry()
KERNELS = KernelRegistry()
SPECS: dict[Shape, FilterSpec] = {}
for _shape in SHAPES:
    _spec = _spec_for(_shape)
    SHELF.register(_spec)
    KERNELS.register(_spec, Backend.CPU, _identity)
    SPECS[_shape] = _spec


def _fields_that_cannot_run(shape: Shape) -> frozenset[str]:
    """Which of the shape's own declarations no protocol in `dispatch` takes.

    The specification `unrunnable_reason` is checked against, and stated as data
    about the shape rather than as the same branches written twice: `Kernel` and
    `MergingKernel` are both one frame in and one frame out, so a span, a
    dropped output, rows arriving, and rows leaving are each outside them.

    This shrinks as protocols land — `a-kernel-that-sees-a-span` deletes the
    first line — and a shrink that is not matched in `dispatch` fails the walk
    from both directions at once.
    """
    mode, rate_changing, accepts, emits = shape
    named: set[str] = set()
    if mode is not Mode.STREAMING:
        named.add("mode")
    if rate_changing:
        named.add("rate_changing")
    if accepts is not StreamKind.ARRAY:
        named.add("accepts")
    if emits is not StreamKind.ARRAY:
        named.add("emits")
    return frozenset(named)


def _plan_for(shape: Shape) -> ExecutionPlan:
    node = Node(node_id="n", filter_id=_shape_id(shape), version="1.0.0", params={})
    return ExecutionPlan.build(
        Dag.build(Pipeline(nodes=(node,)), SHELF),
        source=SOURCE,
        span=SPAN,
        backend=Backend.CPU,
    )


UNRUNNABLE: tuple[Shape, ...] = tuple(s for s in SHAPES if _fields_that_cannot_run(s))


@pytest.mark.parametrize("shape", SHAPES, ids=_shape_id)
def test_every_declarable_shape_runs_or_is_refused_by_its_own_field(shape: Shape) -> None:
    """The classification is total, and a refusal names what was declared.

    Both halves are the point. A shape that neither runs nor refuses is the
    `emits` gap this item closed; a refusal whose message names no field is a
    reader who knows the graph will not run and not which line to change.
    """
    cannot = _fields_that_cannot_run(shape)
    spec = SPECS[shape]
    plan = _plan_for(shape)

    if not cannot:
        assert unrunnable_reason(spec) is None
        results = list(execute(plan, ListSource(), kernels=KERNELS))
        assert [result.index for result in results] == list(range(SPAN.start, SPAN.end))
        return

    reason = unrunnable_reason(spec)
    assert reason is not None
    with pytest.raises(UnrunnableNodeError) as raised:
        list(execute(plan, ListSource(), kernels=KERNELS))
    assert any(field in str(raised.value) for field in cannot), (
        f"{_shape_id(shape)} is refused, but the message names none of {sorted(cannot)}: {reason}"
    )


@pytest.mark.parametrize("shape", UNRUNNABLE, ids=_shape_id)
def test_a_refusal_costs_no_decode(shape: Shape) -> None:
    """Nothing is read before the graph is known to be runnable.

    The answer is static — declarations only — so paying a seek for it is paying
    for nothing. Binding lazily at the node would decode the lead-in and run the
    reachable half of a graph before delivering a sentence that was true before
    the file was opened, and on a long clip that is a minute of it.
    """
    source = ListSource()

    with pytest.raises(UnrunnableNodeError):
        list(execute(_plan_for(shape), source, kernels=KERNELS))

    assert not source.reads


def test_the_refusal_names_which_node_not_only_which_filter() -> None:
    """One graph, the same filter twice, and the message says which one.

    `unrunnable_reason` is pure over the spec and so cannot know; the node id is
    what `_bind` adds, and it is the half a reader needs to edit anything. A
    graph naming one filter at two nodes is the case where losing it leaves a
    message that is true and unactionable.
    """
    windowed = _shape_id((Mode.WINDOWED, False, StreamKind.ARRAY, StreamKind.ARRAY))
    runnable = _shape_id((Mode.STREAMING, False, StreamKind.ARRAY, StreamKind.ARRAY))
    pipeline = Pipeline(
        nodes=(
            Node(node_id="keep", filter_id=runnable, version="1.0.0", params={}),
            Node(node_id="first", filter_id=windowed, version="1.0.0", params={}),
            Node(node_id="second", filter_id=windowed, version="1.0.0", params={}),
        ),
        edges=(
            Edge(upstream="keep", downstream="first"),
            Edge(upstream="first", downstream="second"),
        ),
    )
    plan = ExecutionPlan.build(
        Dag.build(pipeline, SHELF), source=SOURCE, span=SPAN, backend=Backend.CPU
    )

    with pytest.raises(UnrunnableNodeError) as raised:
        list(execute(plan, ListSource(), kernels=KERNELS))

    message = str(raised.value)
    assert message.startswith(f"first ({windowed} 1.0.0)")
    assert "second" not in message
