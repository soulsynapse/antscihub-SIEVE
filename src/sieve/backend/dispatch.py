"""Which kernel runs: a shelf keyed by `(filter_id, version, backend)`.

The mirror of `core/filter_registry.py` one layer up. Core holds the shelf that
*specs* put themselves on; this holds the shelf that *kernels* put themselves
on, and it lives here rather than in core because a kernel is an implementation
and core is not allowed to reach one.

The load-bearing rule is that a filter never branches on the backend. A filter
with a CPU kernel and no GPU kernel is complete, not deficient: `select` walks
a preference order and returns the best kernel that exists and can run, so the
absence of a GPU kernel is answered here once rather than by an `if cupy` in
every filter module. That is also what keeps `backend/` free of any filter's
implementation — non-negotiable #3 fails the moment adding a filter means
editing a file in this package.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from importlib.util import find_spec
from typing import Any, Protocol, TypeVar

from sieve.core.filter_base import FilterSpec, ParamsBase
from sieve.core.types import Frame


class Backend(StrEnum):
    """A device family a kernel can be written against."""

    #: NumPy and OpenCV on the host. Always present.
    CPU = "cpu"
    #: CuPy on a CUDA device. The only v1 GPU backend — no Torch unless an
    #: isolated worker process makes it someone else's dependency problem.
    GPU = "gpu"


#: Tried in this order when a caller expresses no preference. Fastest first:
#: `select` skips a backend that has no kernel for the filter or no runtime on
#: this machine, so this is a wish list rather than a claim about the hardware.
DEFAULT_PREFERENCE: tuple[Backend, ...] = (Backend.GPU, Backend.CPU)

#: Contravariant because a kernel is *consumed* with params: a function written
#: against `DownsampleParams` is a valid kernel wherever one taking a narrower
#: params type is expected, and the registry stores them all as `Kernel[Any]`.
ParamsT_contra = TypeVar("ParamsT_contra", bound=ParamsBase, contravariant=True)
ParamsT = TypeVar("ParamsT", bound=ParamsBase)


class Kernel(Protocol[ParamsT_contra]):
    """One frame in, one frame out, on one backend.

    Positional-only because the registry calls kernels uniformly and parameter
    *names* would otherwise become part of the contract every filter author has
    to match. `Mode.WINDOWED` filters need a span rather than a frame and will
    need a second protocol; nothing declares WINDOWED yet, and inventing its
    signature before a filter needs one is how the wrong signature gets locked
    into every kernel written against this one.
    """

    def __call__(self, frame: Frame, params: ParamsT_contra, /) -> Frame: ...


class DuplicateKernelError(LookupError):
    """Two kernels claim the same filter, version, and backend."""


class NoKernelError(LookupError):
    """No registered kernel for this filter can run on this machine."""


@dataclass(frozen=True, slots=True)
class KernelBinding:
    """The kernel `select` chose, and which backend it came from.

    Both halves are needed and neither is derivable from the other: the callable
    is what runs, and the backend is what enters the cache key for every filter
    that has not declared `backend_agnostic`. Returning only the callable would
    make the executor guess at what it just ran.
    """

    backend: Backend
    run: Kernel[Any]


def runtime_available(backend: Backend) -> bool:
    """Whether this machine could execute a kernel for `backend` at all.

    Deliberately a module import check and not a device count. `find_spec`
    answers without importing cupy, which matters because this is called on a
    path that must stay cheap and because importing cupy on a machine with a
    broken driver raises rather than returning False. A real
    `getDeviceCount() > 0` probe belongs here the day the first GPU kernel
    lands and there is something to run against a device.
    """
    if backend is Backend.CPU:
        return True
    return find_spec("cupy") is not None


class KernelRegistry:
    """Lookup from a spec and a backend to the callable that implements it."""

    def __init__(self) -> None:
        self._kernels: dict[tuple[str, str, Backend], Kernel[Any]] = {}

    def __len__(self) -> int:
        return len(self._kernels)

    def register(self, spec: FilterSpec, backend: Backend, run: Kernel[Any]) -> None:
        """Bind `run` as `spec`'s implementation on `backend`.

        Raises:
            DuplicateKernelError: if that triple is already bound. The failure
                this catches is a module copy-pasted without changing its id,
                which would otherwise silently replace another filter's kernel
                while leaving that filter's cache entries in place.
        """
        key = (spec.filter_id, spec.version, backend)
        if key in self._kernels:
            raise DuplicateKernelError(
                f"{spec.filter_id} {spec.version} already has a {backend} kernel"
            )
        self._kernels[key] = run

    def backends_for(self, spec: FilterSpec) -> tuple[Backend, ...]:
        """Backends `spec` has a kernel for, in `Backend` declaration order.

        What is *registered*, not what can run — `select` applies the machine.
        """
        return tuple(
            backend
            for backend in Backend
            if (spec.filter_id, spec.version, backend) in self._kernels
        )

    def select(
        self, spec: FilterSpec, preference: tuple[Backend, ...] = DEFAULT_PREFERENCE
    ) -> KernelBinding:
        """The best kernel for `spec` that exists and can run here.

        Args:
            spec: the filter to run.
            preference: backends in descending order of preference. A caller
                pins a backend by passing a one-element tuple, which is how a
                cross-backend equivalence test drives both sides.

        Raises:
            NoKernelError: if no backend in `preference` has both a registered
                kernel and a runtime. The message names the two sets apart,
                because "no GPU kernel written" and "no CUDA on this box" are
                different problems with different fixes.
        """
        for backend in preference:
            run = self._kernels.get((spec.filter_id, spec.version, backend))
            if run is not None and runtime_available(backend):
                return KernelBinding(backend=backend, run=run)
        registered = self.backends_for(spec)
        raise NoKernelError(
            f"no usable kernel for {spec.filter_id} {spec.version}: "
            f"asked for {[str(b) for b in preference]}, "
            f"registered {[str(b) for b in registered]}, "
            f"runnable here {[str(b) for b in Backend if runtime_available(b)]}"
        )

    def clear(self) -> None:
        """Drop every registration. For tests; production registers once."""
        self._kernels.clear()


#: The process-wide shelf. `sieve.filters` modules populate it on import.
KERNELS = KernelRegistry()


def kernel(
    params_model: type[ParamsT],
    backend: Backend,
    *,
    registry: KernelRegistry | None = None,
) -> Callable[[Kernel[ParamsT]], Kernel[ParamsT]]:
    """Decorate a function as `params_model`'s kernel on `backend`.

    The filter is named by its params model rather than by an id string. That
    is the whole point: the id and version already live on the spec bound to
    that class by `register_filter`, and a string repeated here is a string that
    can be copy-pasted onto the wrong filter — the one mistake that silently
    crosses two filters' cache entries.

    The decorated function is returned unchanged, so it stays directly callable
    and stays its own type. A benchmark or an equivalence test names it.

    Raises:
        TypeError: if `params_model` carries no spec — it was never decorated
            with `@register_filter`, so there is no id, version, or declared
            I/O for this kernel to be the implementation of.
    """
    spec = params_model.__filter_spec__
    if spec is None:
        raise TypeError(
            f"{params_model.__name__} has no filter spec: @kernel implements a registered filter, "
            "so the params class it names must carry @register_filter"
        )

    def decorate(run: Kernel[ParamsT]) -> Kernel[ParamsT]:
        (registry if registry is not None else KERNELS).register(spec, backend, run)
        return run

    return decorate
