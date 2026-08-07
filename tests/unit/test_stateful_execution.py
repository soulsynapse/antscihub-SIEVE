"""Where kernel state lives, and the three ways that could be wrong.

The kernel's own arithmetic is `test_background_ema.py`'s. What is here is the
machinery around it, and each of these fails for a reason nothing downstream
would report:

**State shared between runs.** Two replicates previewing one node concurrently
get one model fed by two arenas. Every frame that comes out is plausible.

**State surviving a run.** A second pass over the same clip starts warm, so the
run is not reproducible and the lead-in the plan decoded was pointless.

**A stateful node given a cache key.** Its output at a frame depends on where
the run began. Whether that dependence has decayed to nothing by the time
anything is yielded is exactly what `warmup_frames` claims, and nothing that
derives a key can check the claim — so an entry served across spans would rest
on an unverified warmup derivation.

The last is the one worth spelling out, and two tests below do it from opposite
sides: the honest filter agrees across spans, the dishonest one does not, and
they are indistinguishable to everything that decides what may be cached.
`docs/findings/2026.07.26-stateful-output-is-not-keyed-by-what-it-is.md` is the
argument in full.

A scratch registry throughout: the filter under test is the real one, because
the claims are about how the real declaration and the real machinery fit
together, but the *shelf* is local so that nothing here depends on what
`discover()` happened to import.
"""

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
from sieve.core.types import NO_FRAMES, ChannelSpec, Frame, FrameCount, WorkUnits
from sieve.filters.background_ema import (
    BackgroundEmaParams,
    BackgroundState,
    background_ema_cpu,
)
from sieve.pipeline.cache import MemoryFrameStore
from sieve.pipeline.cache_key import is_cacheable
from sieve.pipeline.dag import Dag
from sieve.pipeline.executor import execute
from sieve.pipeline.plan import ExecutionPlan

SOURCE = "footage|1|2"
WIDTH, HEIGHT = 8, 6

#: The real spec, so `warmup_frames` and `stateful` are the shipped values.
EMA_SPEC = BackgroundEmaParams.spec()


class RampSource:
    """Frame `n` is a flat field of intensity `n`, and reads are counted.

    A ramp rather than noise because the background model of a ramp is a number
    a reader can predict, which is what lets an assertion below say *which*
    frame the model had seen rather than merely that it had seen some.
    """

    def __init__(self) -> None:
        self.reads: list[int] = []

    def read(self, index: int) -> Frame:
        self.reads.append(index)
        data = np.full((HEIGHT, WIDTH), min(index, 255), dtype=np.uint8)
        return Frame(data=data, index=index, channels=ChannelSpec.GRAY)


def ema_node() -> Node:
    return Node(node_id="bg", filter_id="background_ema", version="1.0.0")


def shelf() -> FilterRegistry:
    """A registry holding only the real background_ema spec."""
    registry = FilterRegistry()
    registry.register(EMA_SPEC)
    return registry


def kernels() -> KernelRegistry:
    """A kernel shelf holding only the real background_ema CPU kernel."""
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
    """The plan carries no key for it, so nothing is stored and nothing served.

    Not a performance choice, and not a claim that this filter's output varies —
    the next test shows it does not. The rule is on the category, because the
    two tests after this one are indistinguishable to `Dag.node_keys`. The plan
    is where that becomes visible, and the store is where it would have gone
    wrong.
    """
    plan = plan_over(ClipRange(start=100, end=104))
    store = MemoryFrameStore()

    assert plan.key("bg") is None
    results = list(execute(plan, RampSource(), store=store, kernels=kernels()))

    assert len(results) == 4
    assert not any(result.from_cache for result in results)
    assert len(store) == 0


def test_a_correct_warmup_is_what_makes_two_spans_agree() -> None:
    """Two runs starting 50 frames apart give the same answer at a shared frame.

    Worth stating explicitly because it is the opposite of what the exclusion
    from the cache looks like it is claiming. A stateful filter whose
    `warmup_frames` is *right* is span-independent: both runs reach frame 150
    having seen at least 90 frames, both models have converged to within the
    declared epsilon, and after the narrowing back to uint8 they are identical.

    So the reason a stateful node is not cached is not that its output varies.
    It is that this agreement is a consequence of a number the filter author
    wrote down, `dag.py` cannot check it, and a key that does not carry the run's
    origin is a key resting on that unverified claim.
    `test_a_stateful_node_gets_no_cache_key_and_writes_no_entry` is the rule and
    the test below is what the rule is protecting against.
    """
    early = plan_over(ClipRange(start=100, end=151))
    late = plan_over(ClipRange(start=150, end=151))
    assert early.decode_start != late.decode_start

    from_early = list(execute(early, RampSource(), kernels=kernels()))[-1]
    from_late = list(execute(late, RampSource(), kernels=kernels()))[-1]

    assert from_early.index == from_late.index == 150
    assert np.array_equal(from_early["bg"].data, from_late["bg"].data)


def test_a_filter_whose_warmup_is_a_lie_disagrees_with_itself_across_spans() -> None:
    """And `dag.py` cannot tell it from the honest one, which is why neither caches.

    An accumulator declaring zero warmup is the whole hazard in six lines: it is
    stateful, it is deterministic, its output at frame `i` is the sum of every
    frame from wherever the run began, and every static declaration it makes is
    identical in kind to `background_ema`'s. If `cacheable` admitted stateful
    nodes on the strength of a declared warmup, this node would be keyed, the
    first run's entry for frame 12 would be served to the second, and the second
    run would report a number that no run of it ever computed.

    That failure is invisible in every way this repo cares about: the key is
    well-formed, the entry is present, the result is a plausible image, and only
    a machine that ran the other span disagrees.
    """
    scratch = FilterRegistry()

    @register_filter(
        filter_id="accumulate",
        version="1.0.0",
        summary="Running sum, declaring it needs no warmup, which is false.",
        accepts=ArraySpec(),
        emits=ArraySpec(),
        element=ElementRelation.PRESERVED,
        cost=CostEstimate(work_per_megapixel=WorkUnits(1.0)),
        stateful=True,
        registry=scratch,
    )
    class AccumulateParams(ParamsBase):
        pass

    spec = AccumulateParams.spec()
    assert spec.warmup_frames == NO_FRAMES

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

    # Registered by the decorator, which returns it unchanged; naming it here
    # is what keeps that a fact this file states rather than one pyright infers.
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
    # The declaration a key would have been derived from is identical in kind to
    # background_ema's, and this one is wrong. Neither gets a key.
    assert not is_cacheable(spec) and spec.deterministic


def test_the_lead_in_is_what_settles_the_model() -> None:
    """90 frames are decoded before the span, and the kernel sees all of them.

    `test_warmup.py` proves the lead-in *arithmetic*; this proves it has a
    consumer. Before this filter, every node in the repo declared zero warmup,
    so the decode range and the span were always the same range and the discard
    in `execute` had nothing to discard.
    """
    plan = plan_over(ClipRange(start=100, end=102))
    source = RampSource()

    results = list(execute(plan, source, kernels=kernels()))

    assert plan.lead_in == EMA_SPEC.warmup_frames == FrameCount(90)
    assert source.reads == list(range(10, 102))
    assert [result.index for result in results] == [100, 101]


def test_two_concurrent_runs_of_one_node_do_not_share_a_model() -> None:
    """Interleaved runs give each what it would have got alone.

    The constraint the whole design is shaped around: state belongs to the run,
    not to the kernel. A kernel closing over its own model would pass this
    file's other tests and fail only here — and in production only when two
    replicates previewed at once, producing a background fed by two arenas and
    frames that look entirely reasonable.

    Interleaved rather than run one-then-the-other, because generators make the
    sharing visible: the two `execute` calls are alive at the same time and each
    step of one lands between two steps of the other.
    """
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
    """A run is reproducible, which means its state does not outlive it.

    `start()` is called from `_bind`, which `execute` calls once per generator,
    so the model's lifetime is the generator's. A factory called at registration
    instead — the obvious place, and wrong — would make the second run of a
    tuning session differ from the first with nothing in the project changed.
    """
    plan = plan_over(ClipRange(start=95, end=97))
    shelved = kernels()

    first = [result["bg"].data.copy() for result in execute(plan, RampSource(), kernels=shelved)]
    second = [result["bg"].data.copy() for result in execute(plan, RampSource(), kernels=shelved)]

    for before, after in zip(first, second, strict=True):
        assert np.array_equal(before, after)


def test_start_mints_a_state_per_call_and_leaves_stateless_kernels_alone() -> None:
    """The registry's half of the same claim, without an executor in the way.

    Two `start()` calls must not return callables sharing a state, and a
    stateless kernel must come back as the very function that was registered —
    a wrapper there would cost every existing filter an indirection and would
    break the equivalence tests that name kernels directly.
    """
    from sieve.filters.downsample import DownsampleParams, downsample_cpu

    shelved = kernels()
    stateless_spec = DownsampleParams.spec()
    shelved.register(stateless_spec, Backend.CPU, downsample_cpu)

    binding = shelved.select(EMA_SPEC, (Backend.CPU,))
    # The cast narrows `start()`'s return past the merging shape: the EMA is a
    # single-port filter, so what comes back takes a bare frame.
    one = cast("Kernel[Any]", binding.start())
    two = cast("Kernel[Any]", binding.start())

    frame = Frame(data=np.full((HEIGHT, WIDTH), 200, np.uint8), index=0, channels=ChannelSpec.GRAY)
    params = BackgroundEmaParams(alpha=0.5)
    one(frame, params)  # seeds `one`'s model at 200 and leaves `two` untouched
    dark = Frame(data=np.zeros((HEIGHT, WIDTH), np.uint8), index=1, channels=ChannelSpec.GRAY)

    assert one(dark, params).data.mean() > 0  # 100 away from a model at 200
    assert not two(dark, params).data.any()  # seeded by this very frame

    assert shelved.select(stateless_spec, (Backend.CPU,)).start() is downsample_cpu


def test_a_stateful_kernel_behind_a_spec_that_does_not_declare_it_is_refused() -> None:
    """The two declarations say the same thing to different readers.

    The factory tells this registry to make a state; `stateful=True` tells
    `dag.py` not to derive a key. A kernel that kept state behind a spec that
    did not say so would have its span-dependent output written to the store
    under a key that does not carry the span — which is the exact wrong answer
    the exclusion exists to prevent, arrived at by a different route.
    """
    scratch = FilterRegistry()

    @register_filter(
        filter_id="forgetful",
        version="1.0.0",
        summary="Claims to keep nothing and is about to be handed a state.",
        accepts=ArraySpec(),
        emits=ArraySpec(),
        element=ElementRelation.PRESERVED,
        cost=CostEstimate(work_per_megapixel=WorkUnits(1.0)),
        registry=scratch,
    )
    class ForgetfulParams(ParamsBase):
        pass

    assert is_cacheable(ForgetfulParams.spec())

    def counter() -> list[int]:
        """A state factory. Its shape is irrelevant; that there is one is not."""
        return []

    def forgetful_cpu(frame: Frame, params: ForgetfulParams, state: list[int]) -> Frame:
        del params, state
        return frame

    # Applied by hand rather than as a decorator, so the failure is attributable
    # to the registration and not to anything about defining the function.
    decorate = stateful_kernel(
        ForgetfulParams, Backend.CPU, state=counter, registry=KernelRegistry()
    )
    with pytest.raises(ValueError, match="does not declare stateful"):
        decorate(forgetful_cpu)
