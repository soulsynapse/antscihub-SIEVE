from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


WORKING_GRID_RULES_VERSION = "working-grid-v1"
DEFAULT_BASE_SOURCE_BLOCK = 64


class BlockIntent(str, Enum):
    AUTO = "auto"
    EXPLICIT = "explicit"


@dataclass(frozen=True, slots=True)
class WorkingGridSettings:
    downsample: float = 1.0
    block_intent: BlockIntent = BlockIntent.AUTO
    explicit_block_size: int | None = None
    base_source_block: int = DEFAULT_BASE_SOURCE_BLOCK

    @classmethod
    def explicit(
        cls, block_size: int, *, downsample: float = 1.0
    ) -> WorkingGridSettings:
        return cls(
            downsample=downsample,
            block_intent=BlockIntent.EXPLICIT,
            explicit_block_size=block_size,
        )


@dataclass(frozen=True, slots=True)
class BlockBounds:
    x0: int
    y0: int
    x1: int
    y1: int

    @property
    def width(self) -> int:
        return self.x1 - self.x0

    @property
    def height(self) -> int:
        return self.y1 - self.y0

    @property
    def area(self) -> int:
        return self.width * self.height


@dataclass(frozen=True, slots=True)
class ResolvedWorkingGrid:
    source_width: int
    source_height: int
    requested_downsample: float
    work_width: int
    work_height: int
    block_intent: BlockIntent
    requested_block_size: int | None
    base_source_block: int | None
    resolved_block_size: int
    rows: int
    columns: int
    rules_version: str = WORKING_GRID_RULES_VERSION

    @property
    def right_edge_width(self) -> int:
        return self.work_width - (self.columns - 1) * self.resolved_block_size

    @property
    def bottom_edge_height(self) -> int:
        return self.work_height - (self.rows - 1) * self.resolved_block_size

    def block_bounds(self, row: int, column: int) -> BlockBounds:
        _validate_index("row", row, self.rows)
        _validate_index("column", column, self.columns)
        block = self.resolved_block_size
        x0 = column * block
        y0 = row * block
        return BlockBounds(
            x0=x0,
            y0=y0,
            x1=min(x0 + block, self.work_width),
            y1=min(y0 + block, self.work_height),
        )

    def block_area(self, row: int, column: int) -> int:
        return self.block_bounds(row, column).area

    def block_area_weight(self, row: int, column: int) -> float:
        nominal_area = self.resolved_block_size**2
        return self.block_area(row, column) / nominal_area

    def working_to_source_boundary(
        self, x: float, y: float
    ) -> tuple[float, float]:
        if not 0 <= x <= self.work_width or not 0 <= y <= self.work_height:
            raise ValueError(
                "Working boundary must lie inside the resolved working extent"
            )
        return (
            x * self.source_width / self.work_width,
            y * self.source_height / self.work_height,
        )


def resolve_working_grid(
    source_width: int,
    source_height: int,
    settings: WorkingGridSettings = WorkingGridSettings(),
) -> ResolvedWorkingGrid:
    _validate_positive_integer("source_width", source_width)
    _validate_positive_integer("source_height", source_height)
    downsample = _validate_downsample(settings.downsample)
    _validate_positive_integer(
        "base_source_block", settings.base_source_block
    )

    work_width = max(1, round(source_width * downsample))
    work_height = max(1, round(source_height * downsample))

    if settings.block_intent is BlockIntent.AUTO:
        if settings.explicit_block_size is not None:
            raise ValueError(
                "Automatic block intent cannot carry an explicit block size"
            )
        block_size = max(1, round(settings.base_source_block * downsample))
        requested_block_size = None
        base_source_block: int | None = settings.base_source_block
    elif settings.block_intent is BlockIntent.EXPLICIT:
        if settings.explicit_block_size is None:
            raise ValueError(
                "Explicit block intent requires an explicit block size"
            )
        _validate_positive_integer(
            "explicit_block_size", settings.explicit_block_size
        )
        block_size = settings.explicit_block_size
        requested_block_size = settings.explicit_block_size
        base_source_block = None
    else:
        raise ValueError(f"Unsupported block intent: {settings.block_intent!r}")

    return ResolvedWorkingGrid(
        source_width=source_width,
        source_height=source_height,
        requested_downsample=downsample,
        work_width=work_width,
        work_height=work_height,
        block_intent=settings.block_intent,
        requested_block_size=requested_block_size,
        base_source_block=base_source_block,
        resolved_block_size=block_size,
        rows=math.ceil(work_height / block_size),
        columns=math.ceil(work_width / block_size),
    )


def _validate_downsample(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Downsample must be a finite number in (0, 1]")
    resolved = float(value)
    if not math.isfinite(resolved) or not 0 < resolved <= 1:
        raise ValueError("Downsample must be a finite number in (0, 1]")
    return resolved


def _validate_positive_integer(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")


def _validate_index(name: str, value: object, stop: int) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value < stop
    ):
        raise IndexError(f"{name} must be an integer in [0, {stop})")
