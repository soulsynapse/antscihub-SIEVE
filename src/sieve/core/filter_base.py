from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from fractions import Fraction
from typing import Any, ClassVar, TypeAlias

from pydantic import BaseModel, ConfigDict

from sieve.core.types import ChannelSpec


SEMVER_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


FILTER_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


DEFAULT_PORT = "in"


PORT_PATTERN = FILTER_ID_PATTERN


class Mode(StrEnum):
    STREAMING = "streaming"

    WINDOWED = "windowed"


class StreamKind(StrEnum):
    ARRAY = "array"

    TABLE = "table"


class ElementKind(StrEnum):
    PIXEL = "pixel"

    BLOCK = "block"


class ElementRelation(StrEnum):
    PRESERVED = "preserved"

    AGGREGATED = "aggregated"


ElementDeclaration: TypeAlias = "ElementKind | ElementRelation"


def node_element(
    declaration: ElementDeclaration | None, upstream: ElementKind | None
) -> ElementKind | None:
    if declaration is None:
        return None
    if isinstance(declaration, ElementKind):
        return declaration
    if declaration is ElementRelation.AGGREGATED:
        return upstream if upstream is ElementKind.PIXEL else None
    return upstream


UNCHANGED_RATE = Fraction(1, 1)


class ParamsBase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    __filter_spec__: ClassVar[FilterSpec | None] = None

    @classmethod
    def spec(cls) -> FilterSpec:
        if cls.__filter_spec__ is None:
            raise TypeError(
                f"{cls.__name__} has no filter spec: it was never decorated with @register_filter, "
                "so it has no id, version, or declared I/O"
            )
        return cls.__filter_spec__

    def canonical_json(self) -> str:
        return json.dumps(
            self.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        )

    def output_rate(self) -> Fraction:
        return UNCHANGED_RATE

    def warmup_frames(self) -> int:
        return 0

    def frame_bytes_ratio(self) -> float:
        return 1.0


@dataclass(frozen=True, slots=True)
class ArraySpec:
    kind: ClassVar[StreamKind] = StreamKind.ARRAY

    dtypes: tuple[str, ...] = ()
    channels: tuple[ChannelSpec, ...] = ()

    def admits(self, produced: StreamSpec) -> bool:
        if not isinstance(produced, ArraySpec):
            return False
        return self._compatible(self.dtypes, produced.dtypes) and self._compatible(
            self.channels, produced.channels
        )

    @staticmethod
    def _compatible(required: tuple[Any, ...], produced: tuple[Any, ...]) -> bool:
        if not required or not produced:
            return True
        return bool(set(required) & set(produced))


@dataclass(frozen=True, slots=True)
class TableSpec:
    kind: ClassVar[StreamKind] = StreamKind.TABLE

    columns: tuple[str, ...] = ()

    def admits(self, produced: StreamSpec) -> bool:
        if not isinstance(produced, TableSpec):
            return False
        if not self.columns or not produced.columns:
            return True
        return set(self.columns) <= set(produced.columns)


StreamSpec: TypeAlias = ArraySpec | TableSpec


@dataclass(frozen=True, slots=True)
class CostEstimate:
    seconds_per_megapixel: float

    peak_bytes_per_input_byte: float = 2.0


@dataclass(frozen=True, slots=True)
class FilterSpec:
    filter_id: str
    version: str
    summary: str
    params_model: type[ParamsBase]

    accepts: StreamSpec | Mapping[str, StreamSpec]
    emits: StreamSpec
    cost: CostEstimate
    mode: Mode = Mode.STREAMING

    warmup_frames: int = 0

    rate_changing: bool = False

    deterministic: bool = True

    stateful: bool = False

    backend_agnostic: bool = False

    primary_params: tuple[str, ...] = field(default_factory=tuple)

    element: ElementDeclaration | None = None

    def __post_init__(self) -> None:
        if isinstance(self.accepts, Mapping):
            if not self.accepts:
                raise ValueError(
                    f"{self.filter_id}: accepts is an empty mapping — a filter with no input "
                    "port consumes nothing, and a source is not a filter"
                )
            bad = [name for name in self.accepts if not PORT_PATTERN.match(name)]
            if bad:
                raise ValueError(
                    f"{self.filter_id}: port names must match {PORT_PATTERN.pattern!r}, "
                    f"got {sorted(bad)}"
                )
        if not FILTER_ID_PATTERN.match(self.filter_id):
            raise ValueError(
                f"filter_id must match {FILTER_ID_PATTERN.pattern!r}, got {self.filter_id!r}"
            )
        if not SEMVER_PATTERN.match(self.version):
            raise ValueError(f"version must be MAJOR.MINOR.PATCH, got {self.version!r}")
        if self.warmup_frames < 0:
            raise ValueError(
                f"warmup_frames must be non-negative, got {self.warmup_frames}"
            )
        if self.backend_agnostic and not self.deterministic:
            raise ValueError(
                f"{self.filter_id}: backend_agnostic requires deterministic — a filter that "
                "cannot reproduce its own output cannot agree with another backend's"
            )
        if isinstance(self.emits, ArraySpec) and self.element is None:
            raise ValueError(
                f"{self.filter_id}: emits an array and declares no element meaning — pass "
                "element=ElementKind.PIXEL/BLOCK if this filter decides what one value is, or "
                "element=ElementRelation.PRESERVED/AGGREGATED if it relates to what it was "
                "handed. There is no default on purpose: a filter that redefines its elements "
                "and inherited PRESERVED would still register, and the only symptom is a count "
                "written to a CSV under a noun nothing checked"
            )
        if not isinstance(self.emits, ArraySpec) and self.element is not None:
            raise ValueError(
                f"{self.filter_id}: emits rows and declares element {self.element!r} — a table "
                "has columns, not elements"
            )
        known = set(self.params_model.model_fields)
        unknown = [name for name in self.primary_params if name not in known]
        if unknown:
            raise ValueError(
                f"{self.filter_id}: primary_params names no such field: {sorted(unknown)}"
            )
        overrides = self.params_model.output_rate is not ParamsBase.output_rate
        if self.rate_changing and not overrides:
            raise ValueError(
                f"{self.filter_id}: rate_changing is set but {self.params_model.__name__} does not "
                "override output_rate, so nothing can convert a downstream warmup into source "
                "frames"
            )
        if overrides and not self.rate_changing:
            raise ValueError(
                f"{self.filter_id}: {self.params_model.__name__} overrides output_rate but the "
                "spec does not declare rate_changing"
            )

    @property
    def input_ports(self) -> Mapping[str, StreamSpec]:
        if isinstance(self.accepts, Mapping):
            return self.accepts
        return {DEFAULT_PORT: self.accepts}

    @property
    def version_tuple(self) -> tuple[int, int, int]:
        match = SEMVER_PATTERN.match(self.version)
        assert match is not None
        major, minor, patch = match.groups()
        return (int(major), int(minor), int(patch))

    @property
    def key(self) -> tuple[str, str]:
        return (self.filter_id, self.version)

    @property
    def cacheable(self) -> bool:
        return self.deterministic and not self.stateful

    @staticmethod
    def stored_bytes_ratio(params: ParamsBase) -> float:
        return float(params.output_rate()) * params.frame_bytes_ratio()


PathStep: TypeAlias = "tuple[FilterSpec, ParamsBase]"


def node_warmup_frames(step: PathStep) -> int:
    spec, params = step
    if type(params).warmup_frames is ParamsBase.warmup_frames:
        return spec.warmup_frames
    refined = params.warmup_frames()
    if refined < 0:
        raise ValueError(
            f"{spec.filter_id}: {type(params).__name__}.warmup_frames() returned {refined}"
        )
    if refined > spec.warmup_frames:
        raise ValueError(
            f"{spec.filter_id}: {type(params).__name__}.warmup_frames() returned {refined}, "
            f"which exceeds the spec's declared bound of {spec.warmup_frames} — the bound is the "
            "worst case over the legal parameter range and a configuration may only refine it "
            "downward"
        )
    return refined


def input_warmup_frames(step: PathStep, output_warmup: int) -> int:
    spec, params = step
    rate = params.output_rate()
    if rate <= 0:
        raise ValueError(f"{spec.filter_id}: output_rate must be positive, got {rate}")
    return math.ceil(Fraction(output_warmup) / rate) + node_warmup_frames(step)


def source_warmup_frames(path: Sequence[PathStep]) -> int:
    need = 0
    for step in reversed(path):
        need = input_warmup_frames(step, need)
    return need
