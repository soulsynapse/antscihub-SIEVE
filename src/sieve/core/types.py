"""Frame, ROI, and metadata value objects shared across all layers.

These are the vocabulary every other layer pattern-matches on. Metadata is
typed, never stringly-typed: a filter that needs to know the channel layout
reads `ChannelSpec`, not a `str` it has to parse.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Self

import numpy as np
from numpy.typing import NDArray


class ChannelSpec(StrEnum):
    """How the trailing axis of a frame's array is laid out."""

    GRAY = "gray"
    RGB = "rgb"
    BGR = "bgr"

    @property
    def channel_count(self) -> int:
        """Number of channels this layout carries.

        Not `count`: `StrEnum` is a `str`, and `str.count` is a method with
        entirely different semantics that callers are entitled to reach for.
        """
        return 1 if self is ChannelSpec.GRAY else 3


@dataclass(frozen=True, slots=True)
class ROI:
    """An axis-aligned region in *source-pixel* coordinates.

    Source pixels rather than normalized floats: this is what a downstream
    crop actually needs, it is what a user reads off the replicate table, and
    it survives a round trip through the pipeline artifact without accumulating
    float error. The display resolution a user happened to draw at is a GUI
    concern and never reaches here.
    """

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
        """Build from two opposite corners in any order."""
        left, right = sorted((x0, x1))
        top, bottom = sorted((y0, y1))
        return cls(x=left, y=top, width=right - left, height=bottom - top)

    @property
    def right(self) -> int:
        """One past the last column covered."""
        return self.x + self.width

    @property
    def bottom(self) -> int:
        """One past the last row covered."""
        return self.y + self.height

    @property
    def area(self) -> int:
        """Pixel count covered by the region."""
        return self.width * self.height

    def clamped_to(self, width: int, height: int) -> ROI:
        """Return this ROI trimmed to fit inside a `width` x `height` frame."""
        left = min(max(self.x, 0), max(width - 1, 0))
        top = min(max(self.y, 0), max(height - 1, 0))
        right = min(self.right, width)
        bottom = min(self.bottom, height)
        return ROI(x=left, y=top, width=max(right - left, 1), height=max(bottom - top, 1))

    @classmethod
    def placed_in(
        cls, x: int, y: int, width: int, height: int, frame: tuple[int, int] | None
    ) -> Self:
        """A region of exactly `width` x `height` slid to lie inside `frame`.

        The counterpart to `clamped_to`, and the difference between them is the
        point. `clamped_to` *trims*: a region hanging off the right edge comes
        back narrower, which is the right answer for a typed width the frame
        cannot hold.

        It is the wrong answer for a placement, and for a reason that is about
        comparability rather than about appearance. A rack is a dozen arenas of
        identical size; one box that silently lost four pixels against the frame
        edge covers a different number of blocks, and every count denominated
        against that block grid then means something slightly different for that
        replicate while the box looks identical on screen. So this slides, and
        shrinks only when the region is larger than the frame and there is
        nowhere left to slide it.

        Loose integers rather than an `ROI` because the callers do not have one
        yet: a stamp centred near the origin computes a negative `x`, which
        `__post_init__` rejects before any clamping could run.

        `frame` is `None` when no source is bound. There is no edge to slide
        against then, so the only correction left is making the numbers legal.
        """
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
        """This region at a new extent, held about its own centre.

        Centre-preserving rather than origin-preserving, because the operation
        this exists for is "make every arena the same size". The boxes were
        drawn *around* the arenas, so what each one asserts is where its middle
        is; holding the top-left corner instead would walk every box off its
        arena by half the size difference, in the same direction, and a rack
        that was correct before the operation would be uniformly wrong after it.

        Slides at the frame edge rather than trimming — see `placed_in`, whose
        argument is this operation's correctness condition rather than a detail
        of it.
        """
        return self.placed_in(
            self.x + (self.width - width) // 2,
            self.y + (self.height - height) // 2,
            width,
            height,
            frame,
        )

    def crop(self, array: NDArray[Any]) -> NDArray[Any]:
        """View of `array` (row-major, rows first) covered by this region."""
        return array[self.y : self.bottom, self.x : self.right]


@dataclass(frozen=True, slots=True)
class VideoMetadata:
    """Everything known about a source video without decoding its content."""

    path: Path
    width: int
    height: int
    fps: float
    frame_count: int

    @property
    def duration_seconds(self) -> float:
        """Wall-clock length, or 0.0 when the container reports no frame rate."""
        if self.fps <= 0.0:
            return 0.0
        return self.frame_count / self.fps

    def timestamp_of(self, index: int) -> float:
        """Presentation time in seconds of the frame at `index`."""
        if self.fps <= 0.0:
            return 0.0
        return index / self.fps


@dataclass(frozen=True, slots=True)
class Frame:
    """One decoded frame plus the identity needed to reason about it.

    `index` is the authoritative position — timestamps are derived, because
    container timestamps drift and cache keys must not.
    """

    data: NDArray[Any]
    index: int
    channels: ChannelSpec

    @property
    def height(self) -> int:
        """Row count."""
        return int(self.data.shape[0])

    @property
    def width(self) -> int:
        """Column count."""
        return int(self.data.shape[1])

    @property
    def dtype(self) -> np.dtype[Any]:
        """Element type of the underlying array."""
        return self.data.dtype
