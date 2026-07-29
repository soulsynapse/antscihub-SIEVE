











from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from typing import TypeVar

from sieve.core.filter_base import (
    CostEstimate,
    ElementDeclaration,
    FilterSpec,
    Mode,
    ParamsBase,
    StreamSpec,
)




ParamsT = TypeVar("ParamsT", bound=ParamsBase)


class UnknownFilterError(LookupError):
    pass


class DuplicateFilterError(LookupError):
    pass


class FilterRegistry:


    def __init__(self) -> None:
        self._specs: dict[tuple[str, str], FilterSpec] = {}

    def __len__(self) -> int:
        return len(self._specs)

    def __iter__(self) -> Iterator[FilterSpec]:
        return iter(self._specs.values())

    def __contains__(self, key: tuple[str, str]) -> bool:
        return key in self._specs

    def register(self, spec: FilterSpec) -> FilterSpec:











        if spec.key in self._specs:
            raise DuplicateFilterError(f"{spec.filter_id} {spec.version} is already registered")
        self._specs[spec.key] = spec
        return spec

    def get(self, filter_id: str, version: str) -> FilterSpec:





        try:
            return self._specs[filter_id, version]
        except KeyError:
            raise UnknownFilterError(f"no filter {filter_id} at version {version}") from None

    def latest(self, filter_id: str) -> FilterSpec:








        candidates = [spec for spec in self._specs.values() if spec.filter_id == filter_id]
        if not candidates:
            raise UnknownFilterError(f"no filter {filter_id} at any version")
        return max(candidates, key=lambda spec: spec.version_tuple)

    def versions(self, filter_id: str) -> tuple[str, ...]:

        candidates = sorted(
            (spec for spec in self._specs.values() if spec.filter_id == filter_id),
            key=lambda spec: spec.version_tuple,
        )
        return tuple(spec.version for spec in candidates)

    def ids(self) -> tuple[str, ...]:

        return tuple(sorted({spec.filter_id for spec in self._specs.values()}))

    def clear(self) -> None:

        self._specs.clear()



REGISTRY = FilterRegistry()


def register_filter(
    *,
    filter_id: str,
    version: str,
    summary: str,
    accepts: StreamSpec | Mapping[str, StreamSpec],
    emits: StreamSpec,
    cost: CostEstimate,
    mode: Mode = Mode.STREAMING,
    warmup_frames: int = 0,
    rate_changing: bool = False,
    deterministic: bool = True,
    stateful: bool = False,
    backend_agnostic: bool = False,
    primary_params: tuple[str, ...] = (),
    element: ElementDeclaration | None = None,
    registry: FilterRegistry | None = None,
) -> Callable[[type[ParamsT]], type[ParamsT]]:












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
            stateful=stateful,
            backend_agnostic=backend_agnostic,
            primary_params=primary_params,
            element=element,
        )
        (registry if registry is not None else REGISTRY).register(spec)
        params_model.__filter_spec__ = spec
        return params_model

    return decorate
