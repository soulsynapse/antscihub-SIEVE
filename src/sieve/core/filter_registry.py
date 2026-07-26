"""The shelf filters put themselves on: a container keyed by `(id, version)`.

Core defines the shelf; `sieve.filters` puts things on it, at import time,
through the decorator below. Nothing here enumerates filters and nothing here
imports one — a manifest listing them would be the exact manual wiring that
non-negotiable #3 forbids, and an import would invert the layer stack.

Both id *and* version are part of the key. A pipeline saved against 1.0.0 has
to keep reproducing 1.0.0's output after 1.1.0 ships, so the two coexist rather
than the newer one shadowing the older.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import TypeVar

from sieve.core.filter_base import CostEstimate, FilterSpec, Mode, ParamsBase, StreamSpec

#: The decorator returns the class it was given, not `ParamsBase` — erasing the
#: subclass would cost every filter's own fields their static types at the one
#: place they are guaranteed to be read.
ParamsT = TypeVar("ParamsT", bound=ParamsBase)


class UnknownFilterError(LookupError):
    """No filter is registered under the requested id or version."""


class DuplicateFilterError(LookupError):
    """Two filters claim the same `(filter_id, version)`."""


class FilterRegistry:
    """Lookup over registered specs. Holds no kernels and executes nothing."""

    def __init__(self) -> None:
        self._specs: dict[tuple[str, str], FilterSpec] = {}

    def __len__(self) -> int:
        return len(self._specs)

    def __iter__(self) -> Iterator[FilterSpec]:
        return iter(self._specs.values())

    def __contains__(self, key: tuple[str, str]) -> bool:
        return key in self._specs

    def register(self, spec: FilterSpec) -> FilterSpec:
        """Add `spec`, returning it so a caller can bind the result.

        A repeated key always raises, even for an identical spec. The failure
        it catches is a filter module copy-pasted without changing its id, and
        the cost of that going unnoticed is two different kernels sharing cache
        entries — expensive enough to outweigh the inconvenience of a module
        that cannot be re-imported without clearing the registry first.

        Raises:
            DuplicateFilterError: if this `(filter_id, version)` is taken.
        """
        if spec.key in self._specs:
            raise DuplicateFilterError(f"{spec.filter_id} {spec.version} is already registered")
        self._specs[spec.key] = spec
        return spec

    def get(self, filter_id: str, version: str) -> FilterSpec:
        """The spec registered under exactly this id and version.

        Raises:
            UnknownFilterError: if nothing is registered under the pair.
        """
        try:
            return self._specs[filter_id, version]
        except KeyError:
            raise UnknownFilterError(f"no filter {filter_id} at version {version}") from None

    def latest(self, filter_id: str) -> FilterSpec:
        """The highest-versioned spec for `filter_id`.

        Ordered by `version_tuple`, not by the version string: `1.10.0` is
        newer than `1.9.0` and sorts below it as text.

        Raises:
            UnknownFilterError: if no version of `filter_id` is registered.
        """
        candidates = [spec for spec in self._specs.values() if spec.filter_id == filter_id]
        if not candidates:
            raise UnknownFilterError(f"no filter {filter_id} at any version")
        return max(candidates, key=lambda spec: spec.version_tuple)

    def versions(self, filter_id: str) -> tuple[str, ...]:
        """Registered versions of `filter_id`, oldest first. Empty if unknown."""
        candidates = sorted(
            (spec for spec in self._specs.values() if spec.filter_id == filter_id),
            key=lambda spec: spec.version_tuple,
        )
        return tuple(spec.version for spec in candidates)

    def ids(self) -> tuple[str, ...]:
        """Every registered filter id, sorted, each appearing once."""
        return tuple(sorted({spec.filter_id for spec in self._specs.values()}))

    def clear(self) -> None:
        """Drop every registration. For tests; production registers once."""
        self._specs.clear()


#: The process-wide shelf. `sieve.filters` modules populate it on import.
REGISTRY = FilterRegistry()


def register_filter(
    *,
    filter_id: str,
    version: str,
    summary: str,
    accepts: StreamSpec,
    emits: StreamSpec,
    cost: CostEstimate,
    mode: Mode = Mode.STREAMING,
    warmup_frames: int = 0,
    rate_changing: bool = False,
    deterministic: bool = True,
    backend_agnostic: bool = False,
    primary_params: tuple[str, ...] = (),
    registry: FilterRegistry | None = None,
) -> Callable[[type[ParamsT]], type[ParamsT]]:
    """Decorate a `ParamsBase` subclass to build and register its spec.

    The decorated class *is* the filter's parameter model, so the one thing a
    `FilterSpec` cannot be written without is supplied by the decoration rather
    than repeated in it. The built spec is bound to the class as
    `__filter_spec__`, which is how a kernel in `sieve.filters` reaches its own
    declaration without a second lookup.

    `registry` exists so a test can register into a scratch registry instead of
    the process-wide one. Filter modules omit it.
    """

    def decorate(params_model: type[ParamsT]) -> type[ParamsT]:
        spec = FilterSpec(
            filter_id=filter_id,
            version=version,
            summary=summary,
            params_model=params_model,
            accepts=accepts,
            emits=emits,
            cost=cost,
            mode=mode,
            warmup_frames=warmup_frames,
            rate_changing=rate_changing,
            deterministic=deterministic,
            backend_agnostic=backend_agnostic,
            primary_params=primary_params,
        )
        (registry if registry is not None else REGISTRY).register(spec)
        params_model.__filter_spec__ = spec
        return params_model

    return decorate
