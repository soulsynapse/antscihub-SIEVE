




























from __future__ import annotations

from typing import Any, cast

import numpy as np
import pytest

from sieve.backend.dispatch import (
    Backend,
    Kernel,
    KernelRegistry,
    stateful_kernel,
)
from sieve.core.filter_base import ArraySpec, CostEstimate, ElementRelation, ParamsBase
from sieve.core.filter_registry import FilterRegistry, register_filter
from sieve.core.pipeline_model import ClipRange, Node, Pipeline
from sieve.core.types import ChannelSpec, Frame
from sieve.filters.background_ema import (
    BackgroundEmaParams,
    BackgroundState,
    background_ema_cpu,
)
from sieve.pipeline.cache import MemoryFrameStore
from sieve.pipeline.dag import Dag
from sieve.pipeline.executor import execute
from sieve.pipeline.plan import ExecutionPlan

SOURCE = "footage|1|2"
WIDTH, HEIGHT = 8, 6


EMA_SPEC = BackgroundEmaParams.spec()


class RampSource:







    def __init__(self) -> None:
        self.reads: list[int] = []

    def read(self, index: int) -> Frame:
        self.reads.append(index)
        data = np.full((HEIGHT, WIDTH), min(index, 255), dtype=np.uint8)
        return Frame(data=data, index=index, channels=ChannelSpec.GRAY)


def ema_node() -> Node:
    return Node(node_id="bg", filter_id="background_ema", version="1.0.0")


def shelf() -> FilterRegistry:

    registry = FilterRegistry()
    registry.register(EMA_SPEC)
    return registry


def kernels() -> KernelRegistry:

    registry = KernelRegistry()
    registry.register(EMA_SPEC, Backend.CPU, background_ema_cpu, state_factory=BackgroundState)
    return registry


def plan_over(span: ClipRange) -> ExecutionPlan:
    return ExecutionPlan.build(
        Dag.build(Pipeline(nodes=(ema_node(),)), shelf()),
        source=SOURCE,
        span=span,
        backend=Backend.CPU,
    )


def test_a_stateful_node_gets_no_cache_key_and_writes_no_entry() -> None:








    plan = plan_over(ClipRange(start=100, end=104))
    store = MemoryFrameStore()

    assert plan.key("bg") is None
    results = list(execute(plan, RampSource(), store=store, kernels=kernels()))

    assert len(results) == 4
    assert not any(result.from_cache for result in results)
    assert len(store) == 0


def test_a_correct_warmup_is_what_makes_two_spans_agree() -> None:















    early = plan_over(ClipRange(start=100, end=151))
    late = plan_over(ClipRange(start=150, end=151))
    assert early.decode_start != late.decode_start

    from_early = list(execute(early, RampSource(), kernels=kernels()))[-1]
    from_late = list(execute(late, RampSource(), kernels=kernels()))[-1]

    assert from_early.index == from_late.index == 150
    assert np.array_equal(from_early["bg"].data, from_late["bg"].data)


def test_a_filter_whose_warmup_is_a_lie_disagrees_with_itself_across_spans() -> None:














    scratch = FilterRegistry()

    @register_filter(
        filter_id="accumulate",
        version="1.0.0",
        summary="Running sum, declaring it needs no warmup, which is false.",
        accepts=ArraySpec(),
        emits=ArraySpec(),
        element=ElementRelation.PRESERVED,
        cost=CostEstimate(seconds_per_megapixel=0.001),
        stateful=True,
        registry=scratch,
    )
    class AccumulateParams(ParamsBase):
        pass

    spec = AccumulateParams.spec()
    assert spec.warmup_frames == 0

    @stateful_kernel(
        AccumulateParams, Backend.CPU, state=list[int], registry=(shelved := KernelRegistry())
    )
    def accumulate_cpu(frame: Frame, params: AccumulateParams, state: list[int]) -> Frame:
        del params
        state.append(int(frame.data.flat[0]))
        return Frame(
            data=np.full_like(frame.data, sum(state) % 251),
            index=frame.index,
            channels=frame.channels,
        )



    assert callable(accumulate_cpu)

    def plan(span: ClipRange) -> ExecutionPlan:
        node = Node(node_id="acc", filter_id="accumulate", version="1.0.0")
        return ExecutionPlan.build(
            Dag.build(Pipeline(nodes=(node,)), scratch),
            source=SOURCE,
            span=span,
            backend=Backend.CPU,
        )

    from_five = list(execute(plan(ClipRange(start=5, end=13)), RampSource(), kernels=shelved))[-1]
    from_ten = list(execute(plan(ClipRange(start=10, end=13)), RampSource(), kernels=shelved))[-1]

    assert from_five.index == from_ten.index == 12
    assert not np.array_equal(from_five["acc"].data, from_ten["acc"].data)


    assert not spec.cacheable and spec.deterministic


def test_the_lead_in_is_what_settles_the_model() -> None:







    plan = plan_over(ClipRange(start=100, end=102))
    source = RampSource()

    results = list(execute(plan, source, kernels=kernels()))

    assert plan.lead_in == EMA_SPEC.warmup_frames == 90
    assert source.reads == list(range(10, 102))
    assert [result.index for result in results] == [100, 101]


def test_two_concurrent_runs_of_one_node_do_not_share_a_model() -> None:












    span = ClipRange(start=95, end=99)
    alone = [
        result["bg"].data.copy()
        for result in execute(plan_over(span), RampSource(), kernels=kernels())
    ]

    left = execute(plan_over(span), RampSource(), kernels=kernels())
    right = execute(plan_over(span), RampSource(), kernels=kernels())
    interleaved = [
        (next(left)["bg"].data.copy(), next(right)["bg"].data.copy()) for _ in range(len(alone))
    ]

    for expected, (from_left, from_right) in zip(alone, interleaved, strict=True):
        assert np.array_equal(from_left, expected)
        assert np.array_equal(from_right, expected)


def test_a_second_run_starts_cold() -> None:







    plan = plan_over(ClipRange(start=95, end=97))
    shelved = kernels()

    first = [result["bg"].data.copy() for result in execute(plan, RampSource(), kernels=shelved)]
    second = [result["bg"].data.copy() for result in execute(plan, RampSource(), kernels=shelved)]

    for before, after in zip(first, second, strict=True):
        assert np.array_equal(before, after)


def test_start_mints_a_state_per_call_and_leaves_stateless_kernels_alone() -> None:







    from sieve.filters.downsample import DownsampleParams, downsample_cpu

    shelved = kernels()
    stateless_spec = DownsampleParams.spec()
    shelved.register(stateless_spec, Backend.CPU, downsample_cpu)

    binding = shelved.select(EMA_SPEC, (Backend.CPU,))


    one = cast("Kernel[Any]", binding.start())
    two = cast("Kernel[Any]", binding.start())

    frame = Frame(data=np.full((HEIGHT, WIDTH), 200, np.uint8), index=0, channels=ChannelSpec.GRAY)
    params = BackgroundEmaParams(alpha=0.5)
    one(frame, params)
    dark = Frame(data=np.zeros((HEIGHT, WIDTH), np.uint8), index=1, channels=ChannelSpec.GRAY)

    assert one(dark, params).data.mean() > 0
    assert not two(dark, params).data.any()

    assert shelved.select(stateless_spec, (Backend.CPU,)).start() is downsample_cpu


def test_a_stateful_kernel_behind_a_spec_that_does_not_declare_it_is_refused() -> None:








    scratch = FilterRegistry()

    @register_filter(
        filter_id="forgetful",
        version="1.0.0",
        summary="Claims to keep nothing and is about to be handed a state.",
        accepts=ArraySpec(),
        emits=ArraySpec(),
        element=ElementRelation.PRESERVED,
        cost=CostEstimate(seconds_per_megapixel=0.001),
        registry=scratch,
    )
    class ForgetfulParams(ParamsBase):
        pass

    assert ForgetfulParams.spec().cacheable

    def counter() -> list[int]:

        return []

    def forgetful_cpu(frame: Frame, params: ForgetfulParams, state: list[int]) -> Frame:
        del params, state
        return frame



    decorate = stateful_kernel(
        ForgetfulParams, Backend.CPU, state=counter, registry=KernelRegistry()
    )
    with pytest.raises(ValueError, match="does not declare stateful"):
        decorate(forgetful_cpu)
