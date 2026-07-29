from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from importlib.util import find_spec
from typing import Any, Protocol, TypeVar, cast

from sieve.core.filter_base import FilterSpec, ParamsBase
from sieve.core.types import Frame


class Backend(StrEnum):
    CPU = "cpu"

    GPU = "gpu"


DEFAULT_PREFERENCE: tuple[Backend, ...] = (Backend.GPU, Backend.CPU)


ParamsT_contra = TypeVar("ParamsT_contra", bound=ParamsBase, contravariant=True)
ParamsT = TypeVar("ParamsT", bound=ParamsBase)


StateT_contra = TypeVar("StateT_contra", contravariant=True)
StateT = TypeVar("StateT")


class Kernel(Protocol[ParamsT_contra]):
    def __call__(self, frame: Frame, params: ParamsT_contra, /) -> Frame: ...


class MergingKernel(Protocol[ParamsT_contra]):
    def __call__(
        self, frames: Mapping[str, Frame], params: ParamsT_contra, /
    ) -> Frame: ...


class StatefulKernel(Protocol[ParamsT_contra, StateT_contra]):
    def __call__(
        self, frame: Frame, params: ParamsT_contra, state: StateT_contra, /
    ) -> Frame: ...


class DuplicateKernelError(LookupError):
    pass


class NoKernelError(LookupError):
    pass


@dataclass(frozen=True, slots=True)
class KernelBinding:
    backend: Backend
    run: Kernel[Any] | StatefulKernel[Any, Any] | MergingKernel[Any]

    state_factory: Callable[[], Any] | None = None

    def start(self) -> Kernel[Any] | MergingKernel[Any]:
        if self.state_factory is None:
            return cast("Kernel[Any] | MergingKernel[Any]", self.run)
        stateful = cast(StatefulKernel[Any, Any], self.run)
        state = self.state_factory()
        return lambda frame, params: stateful(frame, params, state)


def runtime_available(backend: Backend) -> bool:
    if backend is Backend.CPU:
        return True
    return find_spec("cupy") is not None


class KernelRegistry:
    def __init__(self) -> None:
        self._kernels: dict[tuple[str, str, Backend], KernelBinding] = {}

    def __len__(self) -> int:
        return len(self._kernels)

    def register(
        self,
        spec: FilterSpec,
        backend: Backend,
        run: Kernel[Any] | StatefulKernel[Any, Any] | MergingKernel[Any],
        *,
        state_factory: Callable[[], Any] | None = None,
    ) -> None:
        if state_factory is not None and not spec.stateful:
            raise ValueError(
                f"{spec.filter_id} {spec.version} registers a stateful {backend} kernel but its "
                "spec does not declare stateful=True, so dag.py would give the node a cache key "
                "and serve its output to a run that started somewhere else"
            )
        key = (spec.filter_id, spec.version, backend)
        if key in self._kernels:
            raise DuplicateKernelError(
                f"{spec.filter_id} {spec.version} already has a {backend} kernel"
            )
        self._kernels[key] = KernelBinding(
            backend=backend, run=run, state_factory=state_factory
        )

    def backends_for(self, spec: FilterSpec) -> tuple[Backend, ...]:
        return tuple(
            backend
            for backend in Backend
            if (spec.filter_id, spec.version, backend) in self._kernels
        )

    def select(
        self, spec: FilterSpec, preference: tuple[Backend, ...] = DEFAULT_PREFERENCE
    ) -> KernelBinding:
        for backend in preference:
            binding = self._kernels.get((spec.filter_id, spec.version, backend))
            if binding is not None and runtime_available(backend):
                return binding
        registered = self.backends_for(spec)
        raise NoKernelError(
            f"no usable kernel for {spec.filter_id} {spec.version}: "
            f"asked for {[str(b) for b in preference]}, "
            f"registered {[str(b) for b in registered]}, "
            f"runnable here {[str(b) for b in Backend if runtime_available(b)]}"
        )

    def clear(self) -> None:
        self._kernels.clear()


KERNELS = KernelRegistry()


def kernel(
    params_model: type[ParamsT],
    backend: Backend,
    *,
    registry: KernelRegistry | None = None,
) -> Callable[[Kernel[ParamsT]], Kernel[ParamsT]]:
    spec = params_model.__filter_spec__
    if spec is None:
        raise TypeError(
            f"{params_model.__name__} has no filter spec: @kernel implements a registered filter, "
            "so the params class it names must carry @register_filter"
        )
    if len(spec.input_ports) > 1:
        raise TypeError(
            f"{spec.filter_id} declares input ports {sorted(spec.input_ports)}, so its kernel "
            "is called with a mapping of them — register it with @merging_kernel"
        )
    def decorate(run: Kernel[ParamsT]) -> Kernel[ParamsT]:
        (registry if registry is not None else KERNELS).register(spec, backend, run)
        return run
    return decorate


def merging_kernel(
    params_model: type[ParamsT],
    backend: Backend,
    *,
    registry: KernelRegistry | None = None,
) -> Callable[[MergingKernel[ParamsT]], MergingKernel[ParamsT]]:
    spec = params_model.__filter_spec__
    if spec is None:
        raise TypeError(
            f"{params_model.__name__} has no filter spec: @merging_kernel implements a registered "
            "filter, so the params class it names must carry @register_filter"
        )
    if len(spec.input_ports) < 2:
        raise TypeError(
            f"{spec.filter_id} declares one input port, so its kernel is called with a bare "
            "frame — register it with @kernel"
        )
    def decorate(run: MergingKernel[ParamsT]) -> MergingKernel[ParamsT]:
        (registry if registry is not None else KERNELS).register(spec, backend, run)
        return run
    return decorate


def stateful_kernel(
    params_model: type[ParamsT],
    backend: Backend,
    *,
    state: Callable[[], StateT],
    registry: KernelRegistry | None = None,
) -> Callable[[StatefulKernel[ParamsT, StateT]], StatefulKernel[ParamsT, StateT]]:
    spec = params_model.__filter_spec__
    if spec is None:
        raise TypeError(
            f"{params_model.__name__} has no filter spec: @stateful_kernel implements a registered "
            "filter, so the params class it names must carry @register_filter"
        )
    if len(spec.input_ports) > 1:
        raise TypeError(
            f"{spec.filter_id} declares input ports {sorted(spec.input_ports)}, and no stateful "
            "merging protocol exists yet — the filter that needs one should bring its signature"
        )
    def decorate(
        run: StatefulKernel[ParamsT, StateT],
    ) -> StatefulKernel[ParamsT, StateT]:
        shelf = registry if registry is not None else KERNELS
        shelf.register(spec, backend, run, state_factory=state)
        return run
    return decorate
