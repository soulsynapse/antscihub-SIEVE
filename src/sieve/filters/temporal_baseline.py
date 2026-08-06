"""Each cell's own null distribution over time, and the signal in units of it.

`change_energy` is in (intensity units)^2/frame. Its magnitude depends on
illumination, camera gain, exposure, the contrast of the animal against the
substrate, and how much of a block the animal occupies — so a threshold tuned on
one replicate under one backlight is a number *about that lighting rig*. That
collides with the two things SIEVE promises hardest: replicates that share a
pipeline, and a project artifact that reproduces. `normalize` does not fix it and
is not meant to; it removes the *global* per-frame illumination component and
leaves no per-block baseline over time. This filter is that denominator.

Per cell, over a trailing window: the **median** as the baseline and the
**median absolute deviation** as the spread, and the emitted signal is
`(x - median) / (1.4826 * MAD)` — deviations, which is a threshold a second
replicate can be given. Robust statistics rather than mean and standard
deviation because *the events are in the sample*: a block that grooms for a
fifth of the window would inflate the very spread it is being measured against,
and the mean and standard deviation would move with it while the median and MAD
would not. This is the standard procedure in spike sorting, where a filtered
trace is thresholded at k*MAD (Quiroga's), and the same instinct behind fMRI
reporting percent signal change rather than scanner units and astronomy
detecting sources at N-sigma over a locally-estimated sky rather than at an
absolute flux.

**`window_seconds` is the primary parameter because it has no correct value.**
Too short and a sustained behaviour becomes its own baseline and vanishes; too
long and the baseline stops tracking drift. That is the same shape of argument
as `background_ema`'s `alpha` and reaches the same conclusion — it is a question
about the footage, not a constant. `emit=baseline` exists so the answer is
visible: a user who has set the window too short sees their animal *in* the
baseline, in the step composite, rather than inferring it from a detector that
has quietly gone blind.

**One node rather than two ports.** Multi-upstream landed first, so a
`baseline` node feeding a `standardize` node over two ports was expressible and
was the shape the spec anticipated. It is not what shipped, because standardizing
needs *two* statistics and `emits` is still one stream per node: the composition
would be two baseline nodes, each holding the same ring and each computing the
same median, so one of them could hand over the MAD. Recomputing internally is
one ring and one median. The two-port version becomes right the day something
other than this filter's own numerator wants the baseline.

**The window is sampled, not held.** A 30 s window at 240 fps is 7200 frames,
and a per-cell median over 7200 samples every frame is neither affordable nor
worth it: the standard error of a median falls as 1/sqrt(n), so 256 samples
spread across the window estimate it to ~6% and the full 7200 to ~1%, which is
far below the difference between any two defensible window lengths. So the ring
holds at most `MAX_SAMPLES` frames taken at a fixed stride across the span — the
*span* is what tracks drift, the sample count is only what stabilizes the
estimate — and the estimate is recomputed on admission rather than per frame,
which is what makes a long window cost less per frame than a short one rather
than more.

**Why this filter is what made warmup params-derived.** Its lead-in is
`window_frames - 1`, which is a parameter twice over. As a static declaration
that has to be the product of the bounds — 7199 frames, decoded by every run of
any graph containing this node, including the one asking for a 5 s window at
30 fps that needs 149. `ParamsBase.warmup_frames` exists because of that number;
see `core/filter_base.py`.

Stateful (the ring is the state) and therefore uncacheable, for
`background_ema`'s reason verbatim: nothing that derives a key can tell an honest
`warmup_frames` from a false one, so the exclusion is on the category. See
`docs/findings/2026.07.26-stateful-output-is-not-keyed-by-what-it-is.md`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import numpy as np
from numpy.typing import NDArray
from pydantic import Field

from sieve.backend.dispatch import Backend, stateful_kernel
from sieve.core.filter_base import (
    ArraySpec,
    CaptionPart,
    CostEstimate,
    ElementRelation,
    Mode,
    ParamsBase,
)
from sieve.core.filter_registry import register_filter
from sieve.core.types import Frame, FrameCount, FrameIndex, WorkUnits

#: MAD to standard-deviation-equivalent for a normal distribution:
#: `1 / Phi^-1(0.75)`. Applied so that a deviation of 4 means roughly what four
#: standard deviations would mean if the null were Gaussian — which it is not,
#: quite, but the point of the constant is that a threshold carries its usual
#: intuition rather than needing a scale factor in the user's head.
MAD_TO_SIGMA = 1.4826

#: The longest baseline window, in seconds. Not a preference: it is one factor
#: in `TemporalBaselineParams.max_warmup_frames`, and 30 s of lead-in at a
#: plausible frame rate is already the largest decode any filter asks for.
WINDOW_SECONDS_MAX = 30.0

#: The highest frame rate a window may be denominated against. High-speed insect
#: footage runs here; the bound exists so the warmup bound is finite.
FPS_MAX = 240.0

#: Samples the ring holds, however long the window is. See the module docstring:
#: the median's standard error falls as `1/sqrt(n)`, so this is where more
#: samples stop buying anything a shorter window would not undo.
MAX_SAMPLES = 256

#: What the input may be. Float only, and narrowly so: this filter holds up to
#: `MAX_SAMPLES` copies of its input, which is nothing on a block grid of a few
#: thousand cells and 1.5 GB on a 1080p frame. Its input is a signal stream —
#: `block_signal`'s grid — and accepting a full-resolution frame would be
#: declaring support for something that would swap the machine rather than fail.
SUPPORTED_DTYPES = ("float32", "float64")

FloatArray = NDArray[np.floating[Any]]


def window_frames(window_seconds: float, fps: float) -> int:
    """The trailing window in frames — at least one.

    The one definition. `warmup_frames`, the ring's capacity, and the stride are
    all denominated in it, and a second copy is how a filter warms for a window
    it does not then use.
    """
    return max(1, math.ceil(window_seconds * fps))


def sample_stride(frames: int) -> int:
    """Frames between admissions, so the ring spans `frames` in `MAX_SAMPLES`.

    1 for any window short enough to hold whole, which is every window under
    about 8.5 s at 30 fps.
    """
    return max(1, -(-frames // MAX_SAMPLES))


def ring_capacity(frames: int) -> int:
    """Samples held for a window of `frames`. Never above `MAX_SAMPLES`."""
    stride = sample_stride(frames)
    return min(MAX_SAMPLES, -(-frames // stride))


class Emit(StrEnum):
    """Which of the two things this filter has computed leaves the node."""

    #: `(x - median) / (1.4826 * MAD)` per cell. The transferable unit, and what
    #: a detector downstream thresholds.
    DEVIATION = "deviation"
    #: The per-cell median itself, in the input's units. What a user setting
    #: `window_seconds` has to look at: a window too short to contain quiet
    #: periods shows the animal in its own baseline, and the deviation output
    #: cannot show that — it shows nothing, which looks like nothing happening.
    BASELINE = "baseline"


@register_filter(
    filter_id="temporal_baseline",
    version="1.0.0",
    summary="Per-cell trailing median/MAD baseline, and the signal in deviations from it.",
    accepts=ArraySpec(dtypes=SUPPORTED_DTYPES),
    # Channels unstated on both sides: the estimate is per cell and the layout
    # carries through untouched.
    emits=ArraySpec(dtypes=("float32",)),
    # Per cell, so the meaning carries through — and this filter is why the
    # relation exists rather than a constant on every spec: it accepts any
    # array, so it emits blocks over `block_signal` and pixels over a raw
    # frame, and either constant would be a lie in the other position.
    element=ElementRelation.PRESERVED,
    cost=CostEstimate(
        # Two medians over at most `MAX_SAMPLES` retained frames. Work rises
        # with the window until every frame is admitted, then falls as the
        # stride skips samples; calibration is the only place this becomes
        # seconds on a target machine.
        work_per_megapixel=WorkUnits(2.0 * MAX_SAMPLES),
        # The ring plus its scratch, both `MAX_SAMPLES` frames deep, plus the
        # two estimates. Enormous as a *ratio* and small as a quantity: the
        # input frame is a block grid of a few thousand cells, so 500x it is a
        # couple of megabytes. The ratio is what the storage HUD wants and the
        # honest number is the one that goes here.
        peak_bytes_per_input_byte=2.0 * MAX_SAMPLES + 4.0,
    ),
    mode=Mode.STREAMING,
    settling_epsilon=0.0,
    stateful=True,
    primary_params=("window_seconds", "emit"),
    caption=(
        CaptionPart(label="window", param="window_seconds", format_spec=".1f"),
        CaptionPart(param="emit"),
    ),
)
class TemporalBaselineParams(ParamsBase):
    """How long the null is estimated over, and which half of the result to emit."""

    #: The trailing window, in seconds. The primary parameter and the one with
    #: no correct value — see the module docstring. Lower bound is half a
    #: second because a window of a handful of frames is an estimate whose
    #: spread is mostly its own sampling error.
    window_seconds: float = Field(default=5.0, ge=0.5, le=WINDOW_SECONDS_MAX)
    #: Source frame rate, used only to convert the window into frames. The tab
    #: writes it from the video metadata, exactly as it does for
    #: `block_signal.fps` and for the same reason: a kernel is pure and cannot
    #: ask the graph what the container's rate was.
    fps: float = Field(default=30.0, gt=0.0, le=FPS_MAX)
    emit: Emit = Emit.DEVIATION

    @classmethod
    def max_warmup_frames(cls) -> FrameCount:
        """The longest legal trailing window, minus the target frame."""
        return FrameCount(window_frames(WINDOW_SECONDS_MAX, FPS_MAX) - 1)

    def frames(self) -> int:
        """This configuration's window, in frames."""
        return window_frames(self.window_seconds, self.fps)

    def warmup_frames(self) -> FrameCount:
        """The frames that must precede the first full window.

        `window_frames - 1`: the window includes the frame being measured, so
        one frame of footage is one sample and the other `n - 1` are lead-in.
        Below the spec's bound for every legal configuration, and equal to it
        only at the corner where both parameters are at their maxima.
        """
        return FrameCount(self.frames() - 1)


@dataclass(slots=True)
class BaselineState:
    """One run's ring of samples and the estimate derived from it.

    `None` until the first frame, for `BackgroundState`'s reason: nothing tells
    a state factory what shape the footage is, and the first frame is the only
    thing that can size the ring.

    The estimate is cached beside the ring rather than recomputed per frame
    because it only changes when a sample is admitted, which is every `stride`
    frames. That is not an optimization applied to a correct implementation — it
    is why a long window is affordable at all.
    """

    #: `(capacity, *frame_shape)`. Slot order is arbitrary; a median does not
    #: care which sample is oldest, and not caring is what lets this be a ring
    #: rather than a shift.
    ring: FloatArray | None = None
    #: Working space the two medians partition in place, so neither has to copy
    #: the ring internally. Same shape as the ring.
    scratch: FloatArray | None = None
    #: Slots holding a real sample. Below `capacity` only during the window's
    #: own fill, where the estimate is over what has been seen — the best
    #: available answer, and the reason `warmup_frames` exists to make it moot.
    filled: int = 0
    #: Next slot to write.
    write: int = 0
    #: Frames consumed, which is what the stride is counted against.
    seen: int = 0
    #: `(baseline, spread)`, or `None` when a sample has invalidated it.
    estimate: tuple[FloatArray, FloatArray] | None = None

    def admit(self, data: FloatArray, capacity: int, index: FrameIndex) -> None:
        """Put `data` in the ring, allocating it on the first frame.

        Raises:
            ValueError: if the shape changed since the ring was sized. The
                executor crops every root to a fixed ROI so a graph cannot cause
                this, and a silent resize would hide whatever did — a resized
                proxy, a second source spliced into one run — behind an estimate
                that quietly restarted its window with nobody told.
        """
        if self.ring is None:
            self.ring = np.empty((capacity, *data.shape), np.float32)
            self.scratch = np.empty_like(self.ring)
        elif self.ring.shape[1:] != data.shape:
            raise ValueError(
                f"temporal_baseline was sized on a {self.ring.shape[1:]} frame and handed a "
                f"{data.shape} one at index {index}; one run is one geometry"
            )
        size = self.ring.shape[0]
        self.ring[self.write] = data
        self.write = (self.write + 1) % size
        self.filled = min(self.filled + 1, size)
        self.estimate = None


@stateful_kernel(TemporalBaselineParams, Backend.CPU, state=BaselineState)
def temporal_baseline_cpu(
    frame: Frame, params: TemporalBaselineParams, state: BaselineState
) -> Frame:
    """Admit this frame if the stride says so, then measure it against the ring.

    Admit first, so the first frame of a run has itself as its window rather
    than an empty one. That frame's spread is zero and its deviation is
    therefore zero everywhere — the honest answer, since a single sample is no
    evidence of anything — and it is what `warmup_frames` exists to keep out of
    a requested span.

    Between admissions the estimate is up to `stride - 1` frames stale. A stride
    above 1 means a window of at least `MAX_SAMPLES` frames, so the staleness is
    under half a percent of the span the estimate is over.

    Raises:
        ValueError: if the frame's shape changes mid-run. See
            `BaselineState.admit`.
    """
    data = np.asarray(frame.data, np.float32)
    frames = params.frames()

    if state.seen % sample_stride(frames) == 0:
        state.admit(data, ring_capacity(frames), frame.index)
    state.seen += 1

    if state.estimate is None:
        state.estimate = _estimate(state)
    baseline, spread = state.estimate

    if params.emit is Emit.BASELINE:
        # Copied, and deliberately belt-and-braces: `_estimate` allocates a new
        # baseline on every admission rather than writing into a buffer, so
        # there is nothing to alias *today*. Preallocating those two arrays is
        # the obvious next optimization on this path, and it would turn handing
        # the estimate out into a frame that changes under a `FrameResult` the
        # GUI is still painting — several frames after the edit that caused it.
        # One small allocation on a diagnostic-only path buys that off.
        produced = baseline.copy()
    else:
        usable = spread > 0.0
        produced = np.where(usable, (data - baseline) / np.where(usable, spread, 1.0), 0.0)

    return Frame(
        data=produced.astype(np.float32, copy=False), index=frame.index, channels=frame.channels
    )


def _estimate(state: BaselineState) -> tuple[FloatArray, FloatArray]:
    """Per-cell median and sigma-equivalent spread over the samples held.

    Both medians run with `overwrite_input=True` over `scratch`, which is what
    the second buffer is for: NumPy's median partitions its input, so without a
    scratch it would copy the whole ring twice per admission.
    """
    ring, scratch = state.ring, state.scratch
    assert ring is not None and scratch is not None  # admit() ran first
    held, work = ring[: state.filled], scratch[: state.filled]

    work[...] = held
    baseline = np.median(work, axis=0, overwrite_input=True)
    np.abs(np.subtract(held, baseline, out=work), out=work)
    spread = np.median(work, axis=0, overwrite_input=True) * np.float32(MAD_TO_SIGMA)
    return baseline, _floored(spread)


def _floored(spread: FloatArray) -> FloatArray:
    """Replace a cell's zero spread with the median of the frame's nonzero ones.

    A MAD of exactly zero means more than half the window's samples for that
    cell were bit-identical — a genuinely static region, or quantized input, or
    a window not yet filled. It is a division by an estimated zero, and neither
    obvious answer is acceptable: emitting zero blinds the detector on precisely
    the quietest cells, which is where a still animal is, and emitting infinity
    fires on any change at all.

    So the locality of the estimate is relaxed by exactly one level — the same
    move astronomy makes when a local sky estimate is degenerate — and the cell
    borrows the frame's own typical spread. This is the one place a cell's
    output depends on its neighbours, it applies only in the degenerate case,
    and where the whole frame is static there is nothing to borrow and zero is
    then the right answer: no variation anywhere is no evidence anywhere.
    """
    positive = spread[spread > 0.0]
    if positive.size == 0:
        return spread
    return np.where(spread > 0.0, spread, np.median(positive))
