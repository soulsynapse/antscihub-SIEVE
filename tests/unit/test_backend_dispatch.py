







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
)
from sieve.core.filter_base import ArraySpec, CostEstimate, ElementRelation, FilterSpec, ParamsBase
from sieve.core.filter_registry import FilterRegistry, register_filter
from sieve.core.types import Frame


class Registered(NamedTuple):


    spec: FilterSpec
    kernels: KernelRegistry
    run: Kernel[ParamsBase]


@pytest.fixture
def cpu_only() -> Registered:

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




    kernel(PassthroughParams, Backend.CPU, registry=kernels)(run)

    spec = PassthroughParams.__filter_spec__
    assert spec is not None
    return Registered(spec=spec, kernels=kernels, run=run)


def test_missing_gpu_kernel_falls_back_to_cpu(cpu_only: Registered) -> None:




    binding = cpu_only.kernels.select(cpu_only.spec)

    assert binding.backend is Backend.CPU
    assert binding.run is cpu_only.run
    assert cpu_only.kernels.backends_for(cpu_only.spec) == (Backend.CPU,)


def test_pinning_a_backend_with_no_kernel_refuses(cpu_only: Registered) -> None:




    with pytest.raises(NoKernelError, match=r"registered \['cpu'\]"):
        cpu_only.kernels.select(cpu_only.spec, preference=(Backend.GPU,))


def test_duplicate_kernel_is_refused(cpu_only: Registered) -> None:


    bind = kernel(cpu_only.spec.params_model, Backend.CPU, registry=cpu_only.kernels)

    with pytest.raises(DuplicateKernelError, match="already has a cpu kernel"):
        bind(cpu_only.run)


def test_kernel_without_a_spec_is_refused() -> None:



    class Unregistered(ParamsBase):
        pass

    with pytest.raises(TypeError, match="has no filter spec"):
        kernel(Unregistered, Backend.CPU)
