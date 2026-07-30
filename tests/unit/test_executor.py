"""What the loop has to do that nothing above it already did.

The plan settled ordering, keys, and lead-in, and those are tested where they
live. What is left here is the four things only the loop can get wrong: the
lead-in has to reach the kernels and *not* reach the caller; a cache hit has to
skip both the kernel and the decode; every root has to see the replicate's crop
on every frame; and a node that cannot be called has to say so before anything
is read rather than after half a clip has been decoded.
"""

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


#: `(frame index, amount)` for every kernel call. A list rather than a counter
#: because the lead-in test needs to know *which* frames reached the kernel, and
#: "how many" would be satisfied by the wrong three.
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
    """Registered by hand rather than by `@kernel`, which binds to `KERNELS`.

    The mixed-backend test needs this on its own shelf alongside a GPU kernel
    for another filter, and `@kernel` has no way to say "not the default shelf"
    without a registry argument this module would then have to thread through
    every fixture.
    """
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
    # The alignment claim, asserted where it would break: the executor may
    # never hand a merge two different source frames, whatever the two
    # branches' warmups are.
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
    """Frames in a list, counting the reads.

    A source rather than a `VideoReader` because three of these tests are about
    *whether* a read happened, which a real decoder can only be asked about by
    timing it.
    """

    def __init__(self) -> None:
        self.reads: list[int] = []

    def read(self, index: int) -> Frame:
        self.reads.append(index)
        # Frame `n` is a field of intensity `n`, so a later assertion can say
        # which frame an output came from rather than that one arrived.
        # Gray, because these plans are keyed for luma: every graph here is
        # built from filters that accept a single channel, so `plan.luma` is
        # True and `executor._check_format` refuses a colour reader against it.
        data = np.full((HEIGHT, WIDTH), index % 200, dtype=np.uint8)
        return Frame(data=data, index=index, channels=ChannelSpec.GRAY)


class RefusingSource:
    """A source that fails if it is read at all."""

    def read(self, index: int) -> Frame:
        raise AssertionError(f"decoded frame {index} when every node was cached")


def node(node_id: str, filter_id: str = "tag", **params: object) -> Node:
    return Node(node_id=node_id, filter_id=filter_id, version="1.0.0", params=dict(params))


#: The span these tests run over unless they are about the span. A module-level
#: constant rather than a default argument because a `ClipRange` built in a
#: signature is built once at import and shared, which ruff's B008 is right to
#: flag even where the object is frozen.
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
    """What `runtime_available` answers once cupy is installed.

    Module level so the two backend tests share one definition rather than
    each declaring its own lambda, which pyright cannot type.
    """
    return True


def _pretend_identity(backend: Backend) -> str:
    """What `backend_identity` returns once cupy's dist-info is readable.

    Distinct per backend, which is the only property the key derivation needs
    of it — the real string names a numpy or cupy version, and nothing hashes
    it for anything but inequality.
    """
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
    """Drain the generator.

    `kernels` defaults to the scratch shelf, not the process-wide one: a test
    that forgot to pass it would silently run against whatever
    `sieve.filters.discover()` had put on the real shelf, and pass or fail for
    a reason that has nothing to do with this module.
    """
    return list(execute(plan, source, store=store, kernels=kernels))


def test_the_lead_in_reaches_the_kernel_and_not_the_caller() -> None:
    """Three warmup frames are computed; the caller sees only the span.

    The two halves fail differently and both are silent. Skipping the lead-in
    leaves a stateful filter unsettled on the first frame anyone looks at.
    Yielding it makes the caller's first frame the wrong frame, and since the
    frames are adjacent and plausible, nothing downstream would notice.
    """
    plan = plan_for(Pipeline(nodes=(node("t"),)))
    assert plan.lead_in == 3

    results = run(plan, ListSource())

    assert [call[0] for call in CALLS] == [17, 18, 19, 20, 21, 22]
    assert [result.index for result in results] == [20, 21, 22]


def test_a_warm_cache_skips_the_kernel_and_the_decode() -> None:
    """Second run over the same span reads nothing and computes nothing.

    Decode is lazy per frame, so a graph whose every root is a hit never asks
    the reader — which is what makes re-scrubbing a tuned clip free rather than
    merely cheaper. `RefusingSource` is what states that: a counter could be
    satisfied by a reader that was called and ignored.
    """
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
    """The graph never observes an uncropped frame.

    Two roots off one source, so this also pins that a second root costs a
    second crop and not a second read — the finding this rests on is about
    where the crop lives, and a per-root decode would be the same pixels at
    twice the price.
    """
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
    """`source` is the whole frame, and a warm replay carries none.

    Three distinct failures. A *cropped* source could not feed the full-frame
    viewport render-fed playback shares it with — the crop is the graph's
    input, not the frame. A source on the fully-cached replay would claim a
    decode that never ran, and the sharer would treat store-served results as
    fresh pixels. And no source at all is the second decode coming back.
    """
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
    """The message is available statically, so it is given statically.

    Resolving kernels lazily would decode the lead-in, run the reachable half
    of the graph, and then raise — a minute of work to deliver a sentence that
    was true before the file was opened.
    """
    plan = plan_for(
        Pipeline(nodes=(node("t"), node("w", "span")), edges=(Edge(upstream="t", downstream="w"),))
    )
    source = ListSource()

    with pytest.raises(UnrunnableNodeError, match="windowed filter needs a span"):
        run(plan, source)

    assert not source.reads


def _merge_pipeline(left_from: str, right_from: str) -> Pipeline:
    """Two roots into one `minus`: `a` adds 10 to the source, `b` adds 1.

    Which root feeds which port is the argument, because the pair of tests
    below differ in exactly that.
    """
    return Pipeline(
        nodes=(node("a", amount=10), node("b", amount=1), node("d", "minus")),
        edges=(
            Edge(upstream=left_from, downstream="d", port="left"),
            Edge(upstream=right_from, downstream="d", port="right"),
        ),
    )


def test_a_merging_node_gets_a_frame_per_port_and_the_ports_mean_something() -> None:
    """The wiring decides the pixels: `a - b` is 9 everywhere, `b - a` is not.

    The end-to-end statement of what named ports bought. A positional or
    sorted-upstream convention would give these two graphs the same result —
    and the same cache key — so the assertion that the swapped wiring differs
    is the one that fails if ports ever stop reaching the kernel.
    """
    forward = plan_for(_merge_pipeline("a", "b"))
    swapped = plan_for(_merge_pipeline("b", "a"))
    assert forward.keys["d"] != swapped.keys["d"]

    forward_results = run(forward, ListSource())
    swapped_results = run(swapped, ListSource())

    # Source frame n is intensity n%200; both branches see every frame, so the
    # difference is exactly the difference of the two amounts, everywhere.
    assert all((result["d"].data == 9).all() for result in forward_results)
    # uint8 arithmetic wraps: (n+1) - (n+10) is 247, and that is fine — the
    # claim is only that the swapped wiring is a different computation.
    assert all((result["d"].data == 247).all() for result in swapped_results)


def test_a_merge_below_branches_of_unequal_warmup_sees_aligned_settled_inputs() -> None:
    """The part the TODO item called most likely to be got subtly wrong.

    `a` feeds `d` directly; the other branch goes through a second tag, so the
    two paths into the merge want different lead-ins (3 versus 6). The plan
    takes the max once for the whole graph and the loop computes every node at
    every index, so the merge's two inputs are the same source frame from the
    first lead-in frame on — which `minus_cpu` asserts on every call.
    """
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
    """A GPU kernel does not get to serve a CPU-keyed run.

    `select`'s default preference is GPU-first, so an executor that passed it
    through would run the GPU kernel here and store the result under a key with
    `cpu` hashed into it. That is the one cache failure nothing later can
    detect: the entry is served, the numbers are plausible, and only a machine
    that ran the CPU kernel disagrees.

    `runtime_available` is faked because the claim is about which of two
    *available* kernels is chosen, and that claim is vacuous unless two are
    available — `select` skips GPU on a machine with no cupy, so without the
    fake this test would pass on a registry that had no GPU kernel in it at
    all. Nothing about the hardware is being simulated: `runtime_available` is
    a `find_spec` call, so what is faked is a packaging fact.
    """
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
    """The failure the pinning exists to prevent, stated end to end.

    The test above proves the executor *selects* the right kernel. This proves
    the consequence that actually matters: two plans over one graph, one span,
    and one source, differing only in backend, do not share a single store
    entry. If backend identity ever stopped reaching the key — dropped from the
    digest, or a filter wrongly claiming `backend_agnostic` — selection would
    still be correct and the CPU's frames would be served to the GPU run
    anyway. Nothing downstream could detect that.

    Both fakes are packaging facts rather than hardware ones. `backend_identity`
    is patched at its import site the way `test_cache_key.py` does it, because
    the function reads cupy's *dist-info* — it never imports cupy and never
    opens a driver — so what is missing on this machine is a wheel, not a GPU.
    A real `uv pip install cupy-cuda12x` would remove both fakes and change
    nothing else about what is asserted.
    """
    monkeypatch.setattr("sieve.backend.dispatch.runtime_available", _every_backend_runs)
    monkeypatch.setattr(cache_key, "backend_identity", _pretend_identity)

    shelf = KernelRegistry()
    shelf.register(SHELF.get("tag", "1.0.0"), Backend.CPU, tag_cpu)

    def tag_gpu(frame: Frame, params: TagParams) -> Frame:
        # Distinguishable from `tag_cpu`, which adds `amount`. A GPU kernel
        # that returned the same bytes would let a served CPU entry pass.
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
    """A CPU-only node in a chain does not make the whole run impossible.

    `dispatch.py` holds that a filter with a CPU kernel and no GPU kernel is
    complete rather than deficient. A single backend on the plan contradicts
    that: asking for GPU over a chain containing one CPU-only filter would
    raise and the run would die, even though every node has *a* kernel. Per
    node, the chain runs — each node keyed on the backend that actually
    produced it, which is why the keys below differ from the all-CPU plan's at
    the GPU node and, through the ancestry fold, at everything downstream of it.
    """
    monkeypatch.setattr("sieve.backend.dispatch.runtime_available", _every_backend_runs)
    monkeypatch.setattr(cache_key, "backend_identity", _pretend_identity)

    shelf = KernelRegistry()
    shelf.register(SHELF.get("tag", "1.0.0"), Backend.CPU, tag_cpu)
    shelf.register(SHELF.get("cpu_only", "1.0.0"), Backend.CPU, cpu_only_cpu)

    def tag_gpu(frame: Frame, params: TagParams) -> Frame:
        CALLS.append((frame.index, -params.amount))  # negative marks the GPU path
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
    # The GPU kernel ran for `g`; nothing fell back to `tag_cpu` for it.
    assert all(amount < 0 for index, amount in CALLS if index >= DEFAULT_SPAN.start)

    # `c` runs on CPU in both plans and is still keyed differently, because its
    # key folds in `g`'s. A per-node backend that stopped at the node itself
    # would leave the downstream sharing entries across two different runs.
    uniform = ExecutionPlan.build(
        Dag.build(pipeline, SHELF), source=SOURCE, span=DEFAULT_SPAN, backend=Backend.CPU
    )
    assert mixed.keys["g"] != uniform.keys["g"]
    assert mixed.keys["c"] != uniform.keys["c"]


def test_a_backend_mapping_missing_a_node_is_refused() -> None:
    """Defaulting the absent one would run it on the wrong device, correctly keyed.

    A performance bug with no symptom: the entry is right, the result is right,
    and the only evidence is that the run was slower than it should have been.
    """
    pipeline = Pipeline(nodes=(node("a"), node("b")))
    with pytest.raises(KeyError):
        ExecutionPlan.build(
            Dag.build(pipeline, SHELF),
            source=SOURCE,
            span=DEFAULT_SPAN,
            backend={"a": Backend.CPU},
        )


def test_a_node_with_no_kernel_for_the_plans_backend_says_so() -> None:
    """And says which of the two problems it is.

    "no GPU kernel written" and "no CUDA on this box" have different fixes, so
    `select`'s message names both sets; what this pins is that the executor
    lets that message out rather than falling back past it.
    """
    with pytest.raises(NoKernelError, match=r"asked for \['cpu'\]"):
        run(plan_for(Pipeline(nodes=(node("t"),))), ListSource(), kernels=KernelRegistry())
