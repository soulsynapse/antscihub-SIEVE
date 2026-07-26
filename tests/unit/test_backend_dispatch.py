"""What the dispatcher answers so that no filter has to.

The claim under test is that "a filter with no GPU kernel is complete": absence
is resolved here, once, rather than by an `if cupy` in every filter module. The
two tests are the two halves of that — falling back when a preferred backend has
nothing, and refusing when no backend does.
"""

from __future__ import annotations

import pytest

from sieve.backend.dispatch import (
    Backend,
    DuplicateKernelError,
    KernelRegistry,
    NoKernelError,
    kernel,
)
from sieve.core.filter_base import ArraySpec, CostEstimate, ParamsBase
from sieve.core.filter_registry import FilterRegistry, register_filter
from sieve.core.types import Frame


@pytest.fixture
def cpu_only() -> tuple[type[ParamsBase], KernelRegistry]:
    """A filter registered into scratch registries with a CPU kernel only."""
    specs = FilterRegistry()
    kernels = KernelRegistry()

    @register_filter(
        filter_id="passthrough",
        version="1.0.0",
        summary="Returns its input.",
        accepts=ArraySpec(),
        emits=ArraySpec(),
        cost=CostEstimate(seconds_per_megapixel=0.0),
        registry=specs,
    )
    class PassthroughParams(ParamsBase):
        pass

    @kernel(PassthroughParams, Backend.CPU, registry=kernels)
    def run(frame: Frame, params: PassthroughParams) -> Frame:
        return frame

    return PassthroughParams, kernels


def test_missing_gpu_kernel_falls_back_to_cpu(
    cpu_only: tuple[type[ParamsBase], KernelRegistry],
) -> None:
    # The default preference asks for GPU first. A filter that only wrote a CPU
    # kernel must still run, and must report `cpu` — the backend is what enters
    # the cache key, so a binding that lied about it would cross two machines'
    # entries under one hash.
    params_model, kernels = cpu_only
    spec = params_model.__filter_spec__
    assert spec is not None

    binding = kernels.select(spec)

    assert binding.backend is Backend.CPU
    assert kernels.backends_for(spec) == (Backend.CPU,)


def test_pinning_a_backend_with_no_kernel_refuses(
    cpu_only: tuple[type[ParamsBase], KernelRegistry],
) -> None:
    # Fallback is the policy for an unexpressed preference, not for an expressed
    # one. A cross-backend equivalence test pins GPU precisely to compare it
    # against CPU, and silently handing it the CPU kernel would make that test
    # pass by comparing a result with itself.
    params_model, kernels = cpu_only
    spec = params_model.__filter_spec__
    assert spec is not None

    with pytest.raises(NoKernelError, match="registered \\['cpu'\\]"):
        kernels.select(spec, preference=(Backend.GPU,))


def test_duplicate_kernel_is_refused(
    cpu_only: tuple[type[ParamsBase], KernelRegistry],
) -> None:
    # A module copy-pasted without changing its id would otherwise replace
    # another filter's kernel while leaving that filter's cache entries valid.
    params_model, kernels = cpu_only

    with pytest.raises(DuplicateKernelError, match="already has a cpu kernel"):

        @kernel(params_model, Backend.CPU, registry=kernels)
        def other(frame: Frame, params: ParamsBase) -> Frame:
            return frame


def test_kernel_without_a_spec_is_refused() -> None:
    # `@kernel` names a filter by its params class, so a class that never went
    # through `@register_filter` has no id, version, or declared I/O for the
    # kernel to implement.
    class Unregistered(ParamsBase):
        pass

    with pytest.raises(TypeError, match="has no filter spec"):
        kernel(Unregistered, Backend.CPU)
