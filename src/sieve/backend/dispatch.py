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

**State belongs to the run, and this is where that is made structural.** A
streaming filter that has to remember the last frame — a background model, an
IIR, a tracker — is still one frame in, one frame out; it only needs somewhere
to keep what it learned. The obvious place is the kernel object, and it is
wrong: two replicates previewing the same node concurrently are two states, and
a kernel closing over its own would mix them silently, producing plausible
frames from a background model fed by two arenas. So the state is created by
`KernelBinding.start`, once per run, by a caller that is starting one — and a
kernel with no state to keep is unchanged, unwrapped, and pays nothing.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from importlib.util import find_spec
from typing import Any, Protocol, TypeVar, cast

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

#: Whatever a stateful kernel's factory returns. Unbounded on purpose: the
#: registry never inspects it, and requiring a base class would make every
#: filter's private scratch space a public type in this package.
StateT_contra = TypeVar("StateT_contra", contravariant=True)
StateT = TypeVar("StateT")


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


class MergingKernel(Protocol[ParamsT_contra]):
    """One frame per input port in, one frame out, on one backend.

    A temporal combination cannot be expressed one frame at a time. The frames
    arrive as a mapping keyed by
    the port names the spec declared on `accepts`, because position would make
    edge-declaration order semantic — `a - b` versus `b - a` decided by which
    line of YAML came first.

    Which shape the executor calls is decided by the spec's `input_ports`, not
    by inspecting the callable: a spec declaring one port gets `Kernel`'s
    calling convention, more than one gets this. The registration decorators
    enforce the pairing at import, so a mismatch is an error where the filter
    is written rather than at the first frame.

    The other two shapes that entry deferred stay deferred: a span in
    (`Mode.WINDOWED`) and sometimes-nothing out (`rate_changing`) each need a
    decision about what the executor does with the answer, and no filter needs
    either yet.
    """

    def __call__(self, frames: Mapping[str, Frame], params: ParamsT_contra, /) -> Frame: ...


class StatefulKernel(Protocol[ParamsT_contra, StateT_contra]):
    """The same shape, plus somewhere to keep what the last frame taught it.

    Not the second protocol the docstring above declines to invent. That one is
    about kernels whose *arity in frames* is different — a span in, a frame out;
    a frame in, sometimes nothing out; two frames in, one out — and each needs a
    decision about what the executor hands over and what it does with the
    answer. This is one frame in and one frame out, unchanged, with a third
    argument the executor does not read, does not key on, and never constructs
    itself: `start` mints it and the closure carries it.

    Positional-only for `Kernel`'s reason. `state` last because a filter author
    writing their first stateful kernel edits a signature they already know
    rather than learning a new one.
    """

    def __call__(self, frame: Frame, params: ParamsT_contra, state: StateT_contra, /) -> Frame: ...


class DuplicateKernelError(LookupError):
    """Two kernels claim the same filter, version, and backend."""


class NoKernelError(LookupError):
    """No registered kernel for this filter can run on this machine."""


@dataclass(frozen=True, slots=True)
class KernelBinding:
    """The kernel `select` chose, which backend it came from, and how to start it.

    The first two are needed and neither is derivable from the other: the
    callable is what runs, and the backend is what enters the cache key for
    every filter that has not declared `backend_agnostic`. Returning only the
    callable would make the executor guess at what it just ran.

    `run` is deliberately not the thing a caller invokes. It is the registered
    function, which for a stateful kernel takes three arguments and cannot be
    called without a state nobody has made yet; `start` is what turns either
    shape into the two-argument callable the executor's loop knows.
    """

    backend: Backend
    run: Kernel[Any] | StatefulKernel[Any, Any] | MergingKernel[Any]
    #: How to make one run's state, or `None` for a kernel that keeps none.
    state_factory: Callable[[], Any] | None = None

    def start(self) -> Kernel[Any] | MergingKernel[Any]:
        """A callable for exactly one run, with its own state if it needs any.

        Called once per `execute`, not once per frame — the state has to see
        every frame of the run in order, which is the whole reason it exists.
        Calling it twice makes two independent runs, which is the right answer
        for two concurrent previews and the wrong one for a resumed loop.

        A stateless kernel is returned unwrapped. That is not just an
        optimisation: it means every existing kernel keeps its identity, so a
        benchmark or an equivalence test that names `downsample_cpu` still gets
        the function it named.
        """
        if self.state_factory is None:
            return cast("Kernel[Any] | MergingKernel[Any]", self.run)
        stateful = cast(StatefulKernel[Any, Any], self.run)
        state = self.state_factory()
        return lambda frame, params: stateful(frame, params, state)


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
        # The value is the binding rather than the callable, so the state
        # factory travels with the kernel it belongs to. A parallel dict keyed
        # the same way would be a second place to forget.
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
        """Bind `run` as `spec`'s implementation on `backend`.

        Args:
            spec: the filter this implements.
            backend: the device family `run` is written against.
            run: the kernel. Three-argument when `state_factory` is given, two
                otherwise.
            state_factory: how to make one run's state, for a kernel that keeps
                any. Its presence is what makes `run` be called with three
                arguments, so the two travel together and cannot disagree.

        Raises:
            DuplicateKernelError: if that triple is already bound. The failure
                this catches is a module copy-pasted without changing its id,
                which would otherwise silently replace another filter's kernel
                while leaving that filter's cache entries in place.
            ValueError: if `state_factory` is given for a spec that does not
                declare `stateful`. The two say the same thing to different
                readers — the factory to this registry, the declaration to
                `dag.py`, which is what decides the node may not be cached — and
                a kernel that kept state behind a spec that did not say so would
                have its span-dependent output written into the cache under a
                key that does not carry the span.
        """
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
        self._kernels[key] = KernelBinding(backend=backend, run=run, state_factory=state_factory)

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
            I/O for this kernel to be the implementation of. Also if the spec
            declares more than one input port: the executor would call this
            kernel with a mapping it is not written to take, so the mismatch is
            named here, at import, rather than at the first frame.
    """
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
    """Decorate a mapping-taking function as `params_model`'s kernel on `backend`.

    `kernel`'s mirror for a filter whose spec declares more than one input
    port. A separate decorator for `stateful_kernel`'s reason: the two decorate
    functions of different first-argument type, and one decorator typed as the
    union would let a one-frame kernel be registered for a two-port filter and
    fail at the first frame rather than at import.

    Raises:
        TypeError: if `params_model` carries no spec, as `kernel`. Also if the
            spec declares only one input port — such a filter's kernel is
            called with a bare frame, and registering it here would hand it a
            mapping.
    """
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
    """Decorate a three-argument function as `params_model`'s kernel on `backend`.

    A separate decorator rather than an optional argument to `kernel`, because
    the two decorate functions of different arity and one decorator would have
    to type its argument as the union — which would let a two-argument kernel be
    registered with a state factory and fail at the first frame rather than at
    import.

    Args:
        params_model: the registered filter this implements.
        backend: the device family the kernel is written against.
        state: called once per run to make that run's state. A class is the
            usual argument, and anything zero-argument works.
        registry: the shelf to register on. Defaults to the process-wide one.

    Raises:
        TypeError: if `params_model` carries no spec, as `kernel`. Also if the
            spec declares more than one input port: a stateful *merging* kernel
            is a protocol nothing has needed yet, and it should be invented by
            the filter that needs it rather than here.
        ValueError: if the spec does not declare `stateful`. See
            `KernelRegistry.register`.
    """
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

    def decorate(run: StatefulKernel[ParamsT, StateT]) -> StatefulKernel[ParamsT, StateT]:
        shelf = registry if registry is not None else KERNELS
        shelf.register(spec, backend, run, state_factory=state)
        return run

    return decorate
