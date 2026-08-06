"""What the dispatcher answers so that no filter has to.

The claim under test is that "a filter with no GPU kernel is complete": absence
is resolved here, once, rather than by an `if cupy` in every filter module. The
first two tests are the two halves of that — falling back when a preferred
backend has nothing, and refusing when an explicitly named one does.
"""

from __future__ import annotations

from typing import NamedTuple

import pytest

from sieve.backend.dispatch import (
    Backend,
    DuplicateKernelError,
    Kernel,
    KernelRegistry,
    NoKernelError,
    kernel,
    windowed_kernel,
)
from sieve.core.filter_base import (
    ArraySpec,
    CostEstimate,
    ElementRelation,
    FilterSpec,
    Mode,
    ParamsBase,
)
from sieve.core.filter_registry import FilterRegistry, register_filter
from sieve.core.types import Frame, FrameSpan


class Registered(NamedTuple):
    """A filter in scratch registries, plus the kernel that was bound to it."""

    spec: FilterSpec
    kernels: KernelRegistry
    run: Kernel[ParamsBase]


@pytest.fixture
def cpu_only() -> Registered:
    """A filter with a CPU kernel and no GPU kernel — the ordinary case."""
    specs = FilterRegistry()
    kernels = KernelRegistry()

    @register_filter(
        filter_id="passthrough",
        version="1.0.0",
        summary="Returns its input.",
        accepts=ArraySpec(),
        emits=ArraySpec(),
        element=ElementRelation.PRESERVED,
        cost=CostEstimate(seconds_per_megapixel=0.0),
        registry=specs,
    )
    class PassthroughParams(ParamsBase):
        pass

    def run(frame: Frame, params: ParamsBase) -> Frame:
        return frame

    # Called rather than written as `@kernel`, so the test below can assert
    # which function came back out of `select` — a decorator would leave the
    # binding's identity unnameable.
    kernel(PassthroughParams, Backend.CPU, registry=kernels)(run)

    spec = PassthroughParams.__filter_spec__
    assert spec is not None
    return Registered(spec=spec, kernels=kernels, run=run)


def test_missing_gpu_kernel_falls_back_to_cpu(cpu_only: Registered) -> None:
    # The default preference asks for GPU first. A filter that only wrote a CPU
    # kernel must still run, and must report `cpu` — the backend is what enters
    # the cache key, so a binding that misreported it would file two machines'
    # entries under one hash.
    binding = cpu_only.kernels.select(cpu_only.spec)

    assert binding.backend is Backend.CPU
    assert binding.run is cpu_only.run
    assert cpu_only.kernels.backends_for(cpu_only.spec) == (Backend.CPU,)


def test_pinning_a_backend_with_no_kernel_refuses(cpu_only: Registered) -> None:
    # Fallback is the policy for an unexpressed preference, not for an expressed
    # one. A cross-backend equivalence test pins GPU precisely to compare it
    # against CPU, and silently handing it the CPU kernel would make that test
    # pass by comparing a result with itself.
    with pytest.raises(NoKernelError, match=r"registered \['cpu'\]"):
        cpu_only.kernels.select(cpu_only.spec, preference=(Backend.GPU,))


def test_duplicate_kernel_is_refused(cpu_only: Registered) -> None:
    # A module copy-pasted without changing its id would otherwise replace
    # another filter's kernel while leaving that filter's cache entries valid.
    bind = kernel(cpu_only.spec.params_model, Backend.CPU, registry=cpu_only.kernels)

    with pytest.raises(DuplicateKernelError, match="already has a cpu kernel"):
        bind(cpu_only.run)


def test_kernel_without_a_spec_is_refused() -> None:
    # `@kernel` names a filter by its params class, so a class that never went
    # through `@register_filter` has no id, version, or declared I/O for the
    # kernel to be the implementation of.
    class Unregistered(ParamsBase):
        pass

    with pytest.raises(TypeError, match="has no filter spec"):
        kernel(Unregistered, Backend.CPU)


def test_windowed_spec_refuses_single_frame_kernel() -> None:
    specs = FilterRegistry()

    @register_filter(
        filter_id="windowed",
        version="1.0.0",
        summary="Needs a span.",
        accepts=ArraySpec(),
        emits=ArraySpec(),
        element=ElementRelation.PRESERVED,
        cost=CostEstimate(seconds_per_megapixel=0.0),
        mode=Mode.WINDOWED,
        registry=specs,
    )
    class WindowedParams(ParamsBase):
        pass

    with pytest.raises(TypeError, match="@windowed_kernel"):
        kernel(WindowedParams, Backend.CPU)


def test_windowed_kernel_decorator_registers_a_span_callable() -> None:
    specs = FilterRegistry()
    kernels = KernelRegistry()

    @register_filter(
        filter_id="windowed_passthrough",
        version="1.0.0",
        summary="Returns the target frame from a span.",
        accepts=ArraySpec(),
        emits=ArraySpec(),
        element=ElementRelation.PRESERVED,
        cost=CostEstimate(seconds_per_megapixel=0.0),
        mode=Mode.WINDOWED,
        registry=specs,
    )
    class WindowedParams(ParamsBase):
        pass

    def run(span: FrameSpan, params: WindowedParams) -> Frame:
        del params
        return span.target

    windowed_kernel(WindowedParams, Backend.CPU, registry=kernels)(run)

    binding = kernels.select(WindowedParams.spec(), preference=(Backend.CPU,))

    assert binding.run is run
