









from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pytest

from sieve.backend.dispatch import Backend, KernelRegistry, NoKernelError, kernel, merging_kernel
from sieve.core.filter_base import ArraySpec, CostEstimate, ElementRelation, Mode, ParamsBase
from sieve.core.filter_registry import FilterRegistry, register_filter
from sieve.core.pipeline_model import ClipRange, Edge, Node, Pipeline
from sieve.core.replicates import Replicate
from sieve.core.types import ROI, ChannelSpec, Frame
from sieve.pipeline import cache_key
from sieve.pipeline.cache import FrameStore, MemoryFrameStore
from sieve.pipeline.dag import Dag
from sieve.pipeline.executor import FrameResult, FrameSource, UnrunnableNodeError, execute
from sieve.pipeline.plan import ExecutionPlan

COST = CostEstimate(seconds_per_megapixel=0.001)
SOURCE = "footage|1|2"
SHELF = FilterRegistry()
KERNELS = KernelRegistry()

WIDTH, HEIGHT = 32, 24
ARENA = ROI(x=4, y=2, width=10, height=6)


@register_filter(
    filter_id="tag",
    version="1.0.0",
    summary="Adds `amount` to every pixel, and remembers being called.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    element=ElementRelation.PRESERVED,
    cost=COST,
    warmup_frames=3,
    registry=SHELF,
)
class TagParams(ParamsBase):
    amount: int = 1





CALLS: list[tuple[int, int]] = []


@kernel(TagParams, Backend.CPU, registry=KERNELS)
def tag_cpu(frame: Frame, params: TagParams) -> Frame:
    CALLS.append((frame.index, params.amount))
    return Frame(
        data=frame.data + np.uint8(params.amount),
        index=frame.index,
        channels=frame.channels,
    )


@register_filter(
    filter_id="cpu_only",
    version="1.0.0",
    summary="A filter nobody wrote a GPU kernel for, which is not a defect.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    element=ElementRelation.PRESERVED,
    cost=COST,
    registry=SHELF,
)
class CpuOnlyParams(ParamsBase):
    pass


def cpu_only_cpu(frame: Frame, params: CpuOnlyParams) -> Frame:







    return Frame(data=frame.data, index=frame.index, channels=frame.channels)


@register_filter(
    filter_id="minus",
    version="1.0.0",
    summary="Left minus right, so a swapped wiring is a different result.",
    accepts={"left": ArraySpec(), "right": ArraySpec()},
    emits=ArraySpec(),
    element=ElementRelation.PRESERVED,
    cost=COST,
    registry=SHELF,
)
class MinusParams(ParamsBase):
    pass


@merging_kernel(MinusParams, Backend.CPU, registry=KERNELS)
def minus_cpu(frames: Mapping[str, Frame], params: MinusParams) -> Frame:
    left, right = frames["left"], frames["right"]



    assert left.index == right.index, f"misaligned merge: {left.index} vs {right.index}"
    return Frame(data=left.data - right.data, index=left.index, channels=left.channels)


@register_filter(
    filter_id="span",
    version="1.0.0",
    summary="Needs a window, so nothing can call it.",
    accepts=ArraySpec(),
    emits=ArraySpec(),
    element=ElementRelation.PRESERVED,
    cost=COST,
    mode=Mode.WINDOWED,
    registry=SHELF,
)
class SpanParams(ParamsBase):
    pass


class ListSource:







    def __init__(self) -> None:
        self.reads: list[int] = []

    def read(self, index: int) -> Frame:
        self.reads.append(index)





        data = np.full((HEIGHT, WIDTH), index % 200, dtype=np.uint8)
        return Frame(data=data, index=index, channels=ChannelSpec.GRAY)


class RefusingSource:


    def read(self, index: int) -> Frame:
        raise AssertionError(f"decoded frame {index} when every node was cached")


def node(node_id: str, filter_id: str = "tag", **params: object) -> Node:
    return Node(node_id=node_id, filter_id=filter_id, version="1.0.0", params=dict(params))






DEFAULT_SPAN = ClipRange(start=20, end=23)


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


def _every_backend_runs(backend: Backend) -> bool:





    return True


def _pretend_identity(backend: Backend) -> str:






    return f"pretend-{backend}"


@pytest.fixture(autouse=True)
def forget_calls() -> None:
    CALLS.clear()


def run(
    plan: ExecutionPlan,
    source: FrameSource,
    *,
    store: FrameStore | None = None,
    kernels: KernelRegistry = KERNELS,
) -> list[FrameResult]:







    return list(execute(plan, source, store=store, kernels=kernels))


def test_the_lead_in_reaches_the_kernel_and_not_the_caller() -> None:







    plan = plan_for(Pipeline(nodes=(node("t"),)))
    assert plan.lead_in == 3

    results = run(plan, ListSource())

    assert [call[0] for call in CALLS] == [17, 18, 19, 20, 21, 22]
    assert [result.index for result in results] == [20, 21, 22]


def test_a_warm_cache_skips_the_kernel_and_the_decode() -> None:







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


def test_every_root_sees_the_replicates_crop_on_every_frame() -> None:







    replicate = Replicate(name="arena 2", roi=ARENA)
    plan = plan_for(Pipeline(nodes=(node("a"), node("b"))), replicate=replicate)
    source = ListSource()

    results = run(plan, source)

    assert all(
        result[node_id].data.shape == (ARENA.height, ARENA.width)
        for result in results
        for node_id in ("a", "b")
    )
    assert source.reads == list(plan.decode_range)


def test_the_decoded_frame_escapes_uncropped_and_only_when_a_decode_happened() -> None:








    replicate = Replicate(name="arena 2", roi=ARENA)
    plan = plan_for(Pipeline(nodes=(node("t"),)), replicate=replicate)
    store = MemoryFrameStore()

    first = run(plan, ListSource(), store=store)
    for result in first:
        assert result.source is not None
        assert result.source.index == result.index
        assert result.source.data.shape == (HEIGHT, WIDTH), "the crop reached the source"

    second = run(plan, RefusingSource(), store=store)
    assert all(result.source is None for result in second)


def test_a_windowed_node_is_refused_before_anything_is_read() -> None:






    plan = plan_for(
        Pipeline(nodes=(node("t"), node("w", "span")), edges=(Edge(upstream="t", downstream="w"),))
    )
    source = ListSource()

    with pytest.raises(UnrunnableNodeError, match="windowed filter needs a span"):
        run(plan, source)

    assert not source.reads


def _merge_pipeline(left_from: str, right_from: str) -> Pipeline:





    return Pipeline(
        nodes=(node("a", amount=10), node("b", amount=1), node("d", "minus")),
        edges=(
            Edge(upstream=left_from, downstream="d", port="left"),
            Edge(upstream=right_from, downstream="d", port="right"),
        ),
    )


def test_a_merging_node_gets_a_frame_per_port_and_the_ports_mean_something() -> None:







    forward = plan_for(_merge_pipeline("a", "b"))
    swapped = plan_for(_merge_pipeline("b", "a"))
    assert forward.keys["d"] != swapped.keys["d"]

    forward_results = run(forward, ListSource())
    swapped_results = run(swapped, ListSource())



    assert all((result["d"].data == 9).all() for result in forward_results)


    assert all((result["d"].data == 247).all() for result in swapped_results)


def test_a_merge_below_branches_of_unequal_warmup_sees_aligned_settled_inputs() -> None:








    deep = Pipeline(
        nodes=(
            node("a", amount=10),
            node("b", amount=1),
            node("mid", amount=0),
            node("d", "minus"),
        ),
        edges=(
            Edge(upstream="a", downstream="d", port="left"),
            Edge(upstream="b", downstream="mid"),
            Edge(upstream="mid", downstream="d", port="right"),
        ),
    )
    plan = plan_for(deep)
    assert plan.lead_in == 6

    results = run(plan, ListSource())

    assert [result.index for result in results] == [20, 21, 22]
    assert all((result["d"].data == 9).all() for result in results)


def test_the_backend_is_pinned_to_the_plans(monkeypatch: pytest.MonkeyPatch) -> None:















    monkeypatch.setattr("sieve.backend.dispatch.runtime_available", _every_backend_runs)
    shelf = KernelRegistry()
    shelf.register(SHELF.get("tag", "1.0.0"), Backend.CPU, tag_cpu)

    def tag_gpu(frame: Frame, params: TagParams) -> Frame:
        raise AssertionError("ran the GPU kernel for a plan keyed on cpu")

    shelf.register(SHELF.get("tag", "1.0.0"), Backend.GPU, tag_gpu)

    results = run(plan_for(Pipeline(nodes=(node("t"),))), ListSource(), kernels=shelf)

    assert len(results) == 3


def test_a_gpu_run_is_not_served_the_cpu_runs_cache_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

















    monkeypatch.setattr("sieve.backend.dispatch.runtime_available", _every_backend_runs)
    monkeypatch.setattr(cache_key, "backend_identity", _pretend_identity)

    shelf = KernelRegistry()
    shelf.register(SHELF.get("tag", "1.0.0"), Backend.CPU, tag_cpu)

    def tag_gpu(frame: Frame, params: TagParams) -> Frame:


        return Frame(data=frame.data * np.uint8(2), index=frame.index, channels=frame.channels)

    shelf.register(SHELF.get("tag", "1.0.0"), Backend.GPU, tag_gpu)

    pipeline = Pipeline(nodes=(node("t"),))
    on_cpu = plan_for(pipeline)
    on_gpu = ExecutionPlan.build(
        Dag.build(pipeline, SHELF),
        source=SOURCE,
        span=DEFAULT_SPAN,
        backend=Backend.GPU,
    )
    assert on_cpu.keys["t"] != on_gpu.keys["t"]

    store = MemoryFrameStore()
    cpu_results = run(on_cpu, ListSource(), store=store, kernels=shelf)
    gpu_results = run(on_gpu, ListSource(), store=store, kernels=shelf)

    assert all(not result.from_cache for result in gpu_results)
    assert len(store) == 2 * len(on_cpu.decode_range)
    assert not any(
        np.array_equal(cpu["t"].data, gpu["t"].data)
        for cpu, gpu in zip(cpu_results, gpu_results, strict=True)
    )


def test_one_graph_can_span_two_backends(monkeypatch: pytest.MonkeyPatch) -> None:










    monkeypatch.setattr("sieve.backend.dispatch.runtime_available", _every_backend_runs)
    monkeypatch.setattr(cache_key, "backend_identity", _pretend_identity)

    shelf = KernelRegistry()
    shelf.register(SHELF.get("tag", "1.0.0"), Backend.CPU, tag_cpu)
    shelf.register(SHELF.get("cpu_only", "1.0.0"), Backend.CPU, cpu_only_cpu)

    def tag_gpu(frame: Frame, params: TagParams) -> Frame:
        CALLS.append((frame.index, -params.amount))
        return Frame(data=frame.data, index=frame.index, channels=frame.channels)

    shelf.register(SHELF.get("tag", "1.0.0"), Backend.GPU, tag_gpu)

    pipeline = Pipeline(
        nodes=(node("g"), node("c", "cpu_only")),
        edges=(Edge(upstream="g", downstream="c"),),
    )
    mixed = ExecutionPlan.build(
        Dag.build(pipeline, SHELF),
        source=SOURCE,
        span=DEFAULT_SPAN,
        backend={"g": Backend.GPU, "c": Backend.CPU},
    )

    assert mixed.backend_for("g") is Backend.GPU
    assert mixed.backend_for("c") is Backend.CPU

    results = run(mixed, ListSource(), kernels=shelf)

    assert len(results) == 3

    assert all(amount < 0 for index, amount in CALLS if index >= DEFAULT_SPAN.start)




    uniform = ExecutionPlan.build(
        Dag.build(pipeline, SHELF), source=SOURCE, span=DEFAULT_SPAN, backend=Backend.CPU
    )
    assert mixed.keys["g"] != uniform.keys["g"]
    assert mixed.keys["c"] != uniform.keys["c"]


def test_a_backend_mapping_missing_a_node_is_refused() -> None:





    pipeline = Pipeline(nodes=(node("a"), node("b")))
    with pytest.raises(KeyError):
        ExecutionPlan.build(
            Dag.build(pipeline, SHELF),
            source=SOURCE,
            span=DEFAULT_SPAN,
            backend={"a": Backend.CPU},
        )


def test_a_node_with_no_kernel_for_the_plans_backend_says_so() -> None:






    with pytest.raises(NoKernelError, match=r"asked for \['cpu'\]"):
        run(plan_for(Pipeline(nodes=(node("t"),))), ListSource(), kernels=KernelRegistry())
