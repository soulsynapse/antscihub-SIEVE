






from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Self

import numpy as np
from numpy.typing import NDArray


class ChannelSpec(StrEnum):


    GRAY = "gray"
    RGB = "rgb"
    BGR = "bgr"

    @property
    def channel_count(self) -> int:





        return 1 if self is ChannelSpec.GRAY else 3


@dataclass(frozen=True, slots=True)
class ROI:









    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError(f"ROI must have positive extent, got {self.width}x{self.height}")
        if self.x < 0 or self.y < 0:
            raise ValueError(f"ROI origin must be non-negative, got ({self.x}, {self.y})")

    @classmethod
    def from_corners(cls, x0: int, y0: int, x1: int, y1: int) -> Self:

        left, right = sorted((x0, x1))
        top, bottom = sorted((y0, y1))
        return cls(x=left, y=top, width=right - left, height=bottom - top)

    @property
    def right(self) -> int:

        return self.x + self.width

    @property
    def bottom(self) -> int:

        return self.y + self.height

    @property
    def area(self) -> int:

        return self.width * self.height

    def clamped_to(self, width: int, height: int) -> ROI:

        left = min(max(self.x, 0), max(width - 1, 0))
        top = min(max(self.y, 0), max(height - 1, 0))
        right = min(self.right, width)
        bottom = min(self.bottom, height)
        return ROI(x=left, y=top, width=max(right - left, 1), height=max(bottom - top, 1))

    @classmethod
    def placed_in(
        cls, x: int, y: int, width: int, height: int, frame: tuple[int, int] | None
    ) -> Self:























        if frame is None:
            return cls(x=max(x, 0), y=max(y, 0), width=max(width, 1), height=max(height, 1))
        frame_width, frame_height = frame
        fitted_width = min(max(width, 1), max(frame_width, 1))
        fitted_height = min(max(height, 1), max(frame_height, 1))
        return cls(
            x=min(max(x, 0), max(frame_width - fitted_width, 0)),
            y=min(max(y, 0), max(frame_height - fitted_height, 0)),
            width=fitted_width,
            height=fitted_height,
        )

    def resized_in(self, width: int, height: int, frame: tuple[int, int] | None) -> Self:













        return self.placed_in(
            self.x + (self.width - width) // 2,
            self.y + (self.height - height) // 2,
            width,
            height,
            frame,
        )

    def crop(self, array: NDArray[Any]) -> NDArray[Any]:

        return array[self.y : self.bottom, self.x : self.right]


@dataclass(frozen=True, slots=True)
class VideoMetadata:


    path: Path
    width: int
    height: int
    fps: float
    frame_count: int

    @property
    def duration_seconds(self) -> float:

        if self.fps <= 0.0:
            return 0.0
        return self.frame_count / self.fps

    def timestamp_of(self, index: int) -> float:

        if self.fps <= 0.0:
            return 0.0
        return index / self.fps


@dataclass(frozen=True, slots=True)
class Frame:






    data: NDArray[Any]
    index: int
    channels: ChannelSpec

    @property
    def height(self) -> int:

        return int(self.data.shape[0])

    @property
    def width(self) -> int:

        return int(self.data.shape[1])

    @property
    def dtype(self) -> np.dtype[Any]:

        return self.data.dtype
