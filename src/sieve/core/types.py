"""Frame, ROI, quantities, and metadata value objects shared across all layers.

These are the vocabulary every other layer pattern-matches on. Metadata is
typed, never stringly-typed: a filter that needs to know the channel layout
reads `ChannelSpec`, not a `str` it has to parse.

**The four quantities.** `MediaTime`, `WallTime`, `WorkUnits` and `FrameCount`
are four kinds of number that a `float` makes one kind, and the confusions a
`float` permits are not hypothetical — each of the four already had a name in
this repo that read like one of the others. They are separate types with no
implicit conversion between any two, so the checker refuses the mixture where
it is written rather than leaving a plausible number to be read later.

The distinctions that are load-bearing, in the order they cost something:

- **A frame count is node-relative, and is not a duration.** Warmup is counted
  in a filter's own *input* frames, and a rate-changing node between two others
  makes them speak different index spaces — `at_input_of` is that conversion and
  the reason folding frames into media time would erase the arithmetic
  `source_warmup_frames` exists to get right. Turning frames into seconds needs
  an fps and says so in the signature.
- **Work never wears a time-flavored name.** `WorkUnits` has no `.milliseconds`
  and no conversion to `WallTime`, because the conversion is a rate that belongs
  to a particular machine. The moment a work estimate is spelled `estimated_ms`,
  the anchor it was denominated against is gone and no reader can recover it.
- **Media time is rational**, and the reason is not accumulated drift. Adding a
  float frame duration a million times is off by 1e-6 frames, which would never
  matter. What matters is that `floor` and `ceil` sit on a boundary: at
  30000/1001, the exact duration of 15 frames is 15/fps, and `floor(float(15 /
  fps) * float(fps))` is **14**. The first failure is at frame 15, not in hour
  two, and it is a whole frame every time — `ParamsBase.output_rate` carries the
  same argument in its own words ("`ceil(5 / 0.1)` is 50 only until the day the
  factor is 3"). Wall time is `float` seconds precisely because nothing rounds
  it to a grid: it is a measurement of the world with no exactness to lose.

Only `FrameCount` is a count and only `FrameCount` refuses to be negative: a
frame that is not there is not a frame, while a wall-clock difference is
routinely a headroom below a limit and a media offset is routinely backwards.

The four repeat their arithmetic rather than sharing a base. A base would have
to name its scalar something dimensionless, and the accessor naming the
dimension — `.frames`, `.seconds`, `.units` — is most of what these types are;
the four lines each of `__add__` are the cheap half.
"""

from __future__ import annotations

import math
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction
from pathlib import Path
from typing import Any, Self, overload

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, order=True, slots=True)
class MediaTime:
    """A position or a length on the *media* clock, exactly.

    `Fraction` rather than `float`, and the failure it closes is immediate
    rather than cumulative — see the module docstring for the arithmetic. Every
    quantity derived from a media time is eventually floored onto the frame
    grid, which is where a representation error stops being in the fifteenth
    decimal place and becomes one whole frame of a window, a seek, or a
    reported span.

    Never a measurement of the real world. A render that took 12 ms to produce
    a frame that lasts 33 ms is two different numbers about the same frame, and
    `WallTime` is the other one; there is no conversion between them because
    there is no fact that would justify one.
    """

    seconds: Fraction

    @classmethod
    def of_frames(cls, count: FrameCount, fps: Fraction) -> Self:
        """How long `count` frames last at `fps`.

        `fps` is required rather than defaulted because a frame count is
        node-relative: the same 90 frames are three seconds of source footage
        and thirty seconds of a decimator's output, and no default could be
        right for both.
        """
        if fps <= 0:
            raise ValueError(f"fps must be positive to convert frames to media time, got {fps}")
        return cls(Fraction(count.frames) / fps)

    def __add__(self, other: MediaTime) -> MediaTime:
        return MediaTime(self.seconds + other.seconds)

    def __sub__(self, other: MediaTime) -> MediaTime:
        return MediaTime(self.seconds - other.seconds)

    def __mul__(self, factor: int | Fraction) -> MediaTime:
        return MediaTime(self.seconds * factor)

    def __str__(self) -> str:
        return f"{float(self.seconds):.3f} s"


@dataclass(frozen=True, order=True, slots=True)
class WallTime:
    """Elapsed real time — what a budget bounds and a stopwatch reports.

    `float` seconds, and the imprecision is honest: this is a measurement, its
    fourth decimal place is scheduler noise, and an exact rational would be
    claiming a precision the clock did not supply. Contrast `MediaTime`, which
    is a definition rather than a reading.

    Seconds internally with `.milliseconds` on the outside, because the budget
    table is denominated in milliseconds and a second spelling of the scale in
    every caller is how the two drift apart.
    """

    seconds: float

    @classmethod
    def of_milliseconds(cls, milliseconds: float) -> Self:
        return cls(milliseconds / 1000.0)

    @property
    def milliseconds(self) -> float:
        return self.seconds * 1000.0

    def __add__(self, other: WallTime) -> WallTime:
        return WallTime(self.seconds + other.seconds)

    def __sub__(self, other: WallTime) -> WallTime:
        """Signed: a reading below a limit is a negative difference, not zero.

        `bench/budgets.Budget.exceeded_by` is the caller that matters — it
        reports headroom as a negative overage, and a difference that clamped
        at zero would make "just made it" and "made it by a mile" the same
        number, which is the direction rule 6 refuses.
        """
        return WallTime(self.seconds - other.seconds)

    def __mul__(self, factor: float) -> WallTime:
        return WallTime(self.seconds * factor)

    def __str__(self) -> str:
        return f"{self.seconds:.3f} s"


@dataclass(frozen=True, order=True, slots=True)
class WorkUnits:
    """An amount of work, denominated against an anchor and not against a clock.

    The type exists to keep a prediction from wearing a measurement's name. A
    cost model says a kernel is *this much work*; how long that takes is that
    number divided by a rate that belongs to one machine, one backend, and one
    moment. Storing the division's result and calling it `estimated_ms` throws
    away which machine it was divided by, and nothing downstream can tell the
    estimate from a reading.

    So there is deliberately no conversion to `WallTime` here and no
    `.milliseconds`. Calibration may measure the anchor below on a target
    profile and divide by that rate; an uncalibrated machine can only display
    work units.
    """

    units: float

    def __add__(self, other: WorkUnits) -> WorkUnits:
        return WorkUnits(self.units + other.units)

    def __sub__(self, other: WorkUnits) -> WorkUnits:
        return WorkUnits(self.units - other.units)

    def __mul__(self, factor: float) -> WorkUnits:
        return WorkUnits(self.units * factor)

    def __str__(self) -> str:
        unit = "unit" if self.units == 1 else "units"
        return f"{self.units:g} work {unit}"


#: The single operation against which all `WorkUnits` are denominated.
#: Calibration measures this operation on a target profile; filter declarations
#: remain relative to it and therefore do not smuggle a reference CPU into the
#: spec.
#:
#: Denominated per megapixel, not per frame, because every declaration that
#: divides by it is (`CostEstimate.work_per_megapixel`). A frame-sized anchor
#: would make `crop`'s declared 1.0 read as *one whole-frame copy per input
#: megapixel* — off by the frame's megapixel count — and would reintroduce a
#: "reference resolution" the spec exists to keep out.
WORK_UNIT_ANCHOR = "copy one megapixel of a frame"


@dataclass(frozen=True, order=True, slots=True)
class FrameCount:
    """A number of frames in one node's index space. Never a duration.

    Which node's is not carried, and cannot be: the count is meaningful only
    where it was computed, and the one operation that moves it — `at_input_of`,
    crossing a rate change — is the whole of the warmup arithmetic. That is why
    this is not seconds with an fps attached. `source_warmup_frames` walks a
    path applying that conversion once per node, and five frames behind a 10:1
    decimator being fifty source frames is the error a duration would hide.

    Non-negative, unlike the other three. A negative count is not a direction,
    it is a mistake — a warmup refinement that came back below zero, a shortfall
    subtracted the wrong way round — and refusing it here is what makes
    `FilterSpec.warmup_frames` unable to be declared negative in the first
    place, at the decorator where somebody wrote it.
    """

    frames: int

    def __post_init__(self) -> None:
        if self.frames < 0:
            raise ValueError(f"a frame count must be non-negative, got {self.frames}")

    def at_input_of(self, rate: Fraction) -> FrameCount:
        """This many frames at a node's output, counted at its *input*.

        `ceil(self / rate)`, where `rate` is `ParamsBase.output_rate` — output
        frames per input frame. Ceiling because a fraction of an input frame
        cannot be decoded, and rounding the other way would under-warm by up to
        one frame of the *coarser* stream, which behind a 10:1 decimator is ten
        source frames of an IIR that has not settled.

        Monotone non-decreasing, which `pipeline/plan.py` relies on to fold this
        over a topological order instead of enumerating a diamond's
        exponentially many paths.
        """
        if rate <= 0:
            raise ValueError(f"output rate must be positive to convert frames, got {rate}")
        return FrameCount(math.ceil(Fraction(self.frames) / rate))

    @classmethod
    def spanning(cls, duration: MediaTime, fps: Fraction) -> Self:
        """Whole frames `duration` covers at `fps`, truncating the partial one.

        Truncating rather than rounding: this answers "how many frames am I
        certain of", which is the question a window length asks. A caller whose
        gesture is "the nearest frame to where I let go" is rounding a *cursor*
        and should say so at the cursor.
        """
        if fps <= 0:
            raise ValueError(f"fps must be positive to convert media time to frames, got {fps}")
        return cls(math.floor(duration.seconds * fps))

    def __add__(self, other: FrameCount) -> FrameCount:
        return FrameCount(self.frames + other.frames)

    def __sub__(self, other: FrameCount) -> FrameCount:
        """Raises `ValueError` if the difference is negative; see the class."""
        return FrameCount(self.frames - other.frames)

    def __mul__(self, factor: int) -> FrameCount:
        return FrameCount(self.frames * factor)

    def __str__(self) -> str:
        return f"{self.frames} frame{'' if self.frames == 1 else 's'}"


#: No lead-in, no window, nothing to warm. Allocated once: it is the default on
#: `FilterSpec.warmup_frames` and the identity of the warmup fold, so it is
#: written more often than any other value of the type.
NO_FRAMES = FrameCount(0)


@dataclass(frozen=True, slots=True)
class FrameIndex:
    """A source-frame position, not a count of frames.

    The position's origin is not carried. `pipeline/resolve_source.py` is the
    one artifact boundary that translates local file numbering into source
    numbering; above that boundary, a frame index is a position in the stream a
    run is answering about. The type exists for the arithmetic: two positions
    may be subtracted to produce a `FrameCount`, and a count may move a
    position. Adding two positions is not an operation.
    """

    value: int

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError(f"a frame index must be non-negative, got {self.value}")

    @classmethod
    def of(cls, value: int | FrameIndex) -> FrameIndex:
        """Return `value` as a `FrameIndex`, preserving an existing instance."""
        return value if isinstance(value, FrameIndex) else cls(value)

    def __int__(self) -> int:
        return self.value

    def __index__(self) -> int:
        return self.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FrameIndex):
            return self.value == other.value
        if isinstance(other, int):
            return self.value == other
        return NotImplemented

    def __lt__(self, other: FrameIndex | int) -> bool:
        return self.value < int(other)

    def __le__(self, other: FrameIndex | int) -> bool:
        return self.value <= int(other)

    def __gt__(self, other: FrameIndex | int) -> bool:
        return self.value > int(other)

    def __ge__(self, other: FrameIndex | int) -> bool:
        return self.value >= int(other)

    def __add__(self, other: FrameCount) -> FrameIndex:
        if not hasattr(other, "frames"):
            raise TypeError("a frame index can only move by a frame count")
        return FrameIndex(self.value + other.frames)

    @overload
    def __sub__(self, other: FrameIndex) -> FrameCount: ...

    @overload
    def __sub__(self, other: FrameCount) -> FrameIndex: ...

    def __sub__(self, other: FrameIndex | FrameCount) -> FrameCount | FrameIndex:
        if isinstance(other, FrameIndex):
            return FrameCount(self.value - other.value)
        if not hasattr(other, "frames"):
            raise TypeError("a frame index can only subtract a frame index or frame count")
        return FrameIndex(self.value - other.frames)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class FrameRange:
    """A half-open source-frame range whose iteration yields `FrameIndex`."""

    start: FrameIndex
    stop: FrameIndex

    def __init__(self, start: int | FrameIndex, stop: int | FrameIndex) -> None:
        object.__setattr__(self, "start", FrameIndex.of(start))
        object.__setattr__(self, "stop", FrameIndex.of(stop))
        if self.stop < self.start:
            raise ValueError(f"a frame range must be ordered, got {self.start}:{self.stop}")

    def __iter__(self) -> Iterator[FrameIndex]:
        for index in range(int(self.start), int(self.stop)):
            yield FrameIndex(index)

    def __len__(self) -> int:
        return (self.stop - self.start).frames

    def __contains__(self, index: object) -> bool:
        if not isinstance(index, (FrameIndex, int)):
            return False
        return self.start <= index < self.stop

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FrameRange):
            return self.start == other.start and self.stop == other.stop
        if isinstance(other, range):
            return range(int(self.start), int(self.stop)) == other
        return NotImplemented

    def __repr__(self) -> str:
        return f"FrameRange({self.start}, {self.stop})"


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
    """An axis-aligned region in integer pixels of the array it indexes.

    This type does not choose a global coordinate space. The field that carries
    an ROI decides that: `Replicate.roi` indexes the decoded source frame, while
    `CropParams.roi` indexes that crop node's input frame.

    Integer pixels rather than normalized floats: this is what a crop slice
    actually needs, it is what a user reads off the replicate table when editing
    replicate geometry, and it survives a round trip through the pipeline
    artifact without accumulating float error. The display resolution a user
    happened to draw at is a GUI concern and never reaches here.
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
    #: The container's own rational, not a double. `decode/reader.py` probes it
    #: with PyAV because `CAP_PROP_FPS` has already divided the denominator
    #: away, and 30000/1001 recovered from that double sends frame 15 back as
    #: frame 14 — see this module's header. Zero when the container states no
    #: rate at all, which every consumer here treats as a refusal to answer.
    fps: Fraction
    frame_count: int

    @property
    def duration_seconds(self) -> MediaTime:
        """Media length of the whole source, or zero when no rate was stated."""
        if self.fps <= 0:
            return MediaTime(Fraction(0))
        return MediaTime.of_frames(FrameCount(self.frame_count), self.fps)

    def timestamp_of(self, index: int | FrameIndex) -> MediaTime:
        """Presentation time of the frame at `index`, exactly."""
        if self.fps <= 0:
            return MediaTime(Fraction(0))
        return MediaTime.of_frames(FrameCount(int(index)), self.fps)


@dataclass(frozen=True, init=False, slots=True)
class Frame:
    """One decoded frame plus the identity needed to reason about it.

    `index` is the authoritative position — timestamps are derived, because
    container timestamps drift and cache keys must not.
    """

    data: NDArray[Any]
    index: FrameIndex
    channels: ChannelSpec

    def __init__(self, data: NDArray[Any], index: int | FrameIndex, channels: ChannelSpec) -> None:
        object.__setattr__(self, "data", data)
        object.__setattr__(self, "index", FrameIndex.of(index))
        object.__setattr__(self, "channels", channels)

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


@dataclass(frozen=True, slots=True)
class FrameSpan:
    """A consecutive, non-empty run of frames handed to a windowed kernel.

    The span is half-open by index: `start` is the first frame's source index
    and `end` is one past the last. The final frame is the target the kernel is
    expected to emit for; `Mode.WINDOWED` is still one output frame per source
    frame, but the kernel is allowed to inspect the bounded history that founds
    that output.
    """

    frames: tuple[Frame, ...]

    def __post_init__(self) -> None:
        if not self.frames:
            raise ValueError("a frame span must contain at least one frame")
        previous = self.frames[0].index
        for frame in self.frames[1:]:
            if frame.index != previous + FrameCount(1):
                raise ValueError(
                    f"a frame span must be consecutive, got {previous} then {frame.index}"
                )
            previous = frame.index

    def __iter__(self) -> Iterator[Frame]:
        return iter(self.frames)

    def __len__(self) -> int:
        return len(self.frames)

    def __getitem__(self, index: int) -> Frame:
        return self.frames[index]

    @property
    def start(self) -> FrameIndex:
        """The first source frame index in the span."""
        return self.frames[0].index

    @property
    def end(self) -> FrameIndex:
        """One past the last source frame index in the span."""
        return self.frames[-1].index + FrameCount(1)

    @property
    def target(self) -> Frame:
        """The frame whose source index the windowed kernel must emit."""
        return self.frames[-1]
