"""A causal leaky accumulator of per-block activity, with its neighbours.

The coupling is folded inside the feedback loop rather than composed from a
separate blur node — the semi-implicit Euler step v2's `REFINED-VISION.md`
section C derives.

This is Bobick & Davis's **Motion History Image** (PAMI 2001) with an
exponential rather than linear decay law, so the literature to read is theirs;
the same operator is a *time surface* in neuromorphic vision and a *neural
field* in computational neuroscience. It goes after `block_signal`, and after
`temporal_baseline` if there is one: its input is a block grid, its output is
the same grid in the same units, and its output is what a detector thresholds.

**What it is for** — a behaviour that is intermittent while the event is not, and
a grid whose blocks disagree about which of them the animal is in — is `GUIDANCE`
below, with when to leave it out. What the rest of this docstring holds is why
the operator has the shape it does.

**Decay and coupling are one node, two parameters.** Coupling applies to the
previous state before it decays and before this frame's signal mixes in —
`a[t] = lambda * C(a[t-1]) + (1 - lambda) * s[t]` — so `a[t]` carries `C`
applied `t` times rather than once. A `motion_history` node followed by a blur
node cannot produce this; the composition that could would need the two to share
state.

**`tau_seconds` is the primary parameter and has no correct value.** The same
shape of argument as `temporal_baseline`'s window, resolving the opposite way
(`adr/param-not-preference.md`); the rule of thumb it resolves to is `GUIDANCE`'s.

**Two coupling operators, agreeing on the scale and not on the profile.**
`dilate` is a grayscale morphological dilation: a block takes the largest of its
own value and its neighbours' attenuated ones, so it *gates* rather than smears
and the peak of a sustained event is exactly what it would have been uncoupled.
`diffuse` is the literal PDE term and is conservative — it spreads the peak down
as it spreads it out, which fights the threshold downstream. Under a driven
block at `tau = 1 s` and 30 fps it drops the peak to 0.39, 0.16 and 0.066 of the
input at reaches of 1, 2 and 4, so switching operators means re-tuning the
threshold, and by an amount that moves with a parameter that looks like it is
only about width (v2's
`docs/findings/2026.07.27-dilation-creates-activity-and-diffusion-conserves-it.md`).
`dilate` is the one to reach for; `diffuse` ships because "much testing would be
needed" is the correct answer to which operator suits real footage, not because
it is expected to win.

**Group delay is declared, not removed.** A causal leaky integrator lags its
event by `lambda / (1 - lambda)` frames — the mean lag of the impulse response
and the one-pole IIR's group delay at DC, which are the same number, and about
`tau * fps - 0.5` frames. That matters the moment an onset is reported or
aligned against another data stream, and it matters particularly against a
centred window, which has no delay of its own: mixing the two means the
latencies do not cancel. The zero-phase repair — running the accumulator forward
and then backward, legitimate offline — needs the whole record in hand, which is
`Mode.WINDOWED` over a span this contract can express and no tool has yet asked
for. `group_delay` is therefore a function with a test rather than a `ToolSpec`
field, since no consumer reads it (`adr/declared-means-verified.md`); the
declaration is exact only at `reach_blocks = 0`, because with coupling a block
`d` away first hears about the activity some frames later.

**It does not saturate.** MHI's convention sets the value to `tau` where motion
is present, which puts the output in units of time. Here the source is weighted
by `(1 - lambda)`, so a constant input settles to exactly that input and the
output stays in the input's units — a threshold in `temporal_baseline`
deviations is still a threshold in deviations after this node.

**An epsilon warmup, and therefore uncacheable**, for `background_ema`'s reason
verbatim: `lambda` decays the run's origin out of the answer without ever
removing it, so `settle_frames` is a tolerance rather than a bound
(`adr/cache-admission-is-bounded-warmup.md`). The accumulator
starts at zero, which is the correct initial condition — no prior activity,
unlike a background model where zero would mean a black arena — and what that
costs is first outputs biased low, which is what the warmup is the length of.

v2 declared a `CostEstimate` here; it is cut for `block_signal.py`'s reason — it
fed machinery v3 has not built, and a declaration arrives with its consumer
(`adr/declared-means-verified.md`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import numpy as np
from numpy.typing import NDArray
from pydantic import Field

from sieve.core.tool_base import (
    ArraySpec,
    CaptionPart,
    ElementRelation,
    Emission,
    Mode,
    ParamsBase,
    ParamStereotype,
    WarmupKind,
)
from sieve.core.tool_registry import register_tool
from sieve.core.types import ChannelSpec, Frame, FrameCount, FrameIndex, FrameSpan

#: Below ~0.1s the accumulator is a frame difference with extra steps.
TAU_SECONDS_MIN = 0.1

#: Exceeds any bout this holds; keeps warmup comparable to `temporal_baseline`.
TAU_SECONDS_MAX = 10.0

#: `temporal_baseline`'s number, deliberately the same one.
FPS_MAX = 240.0

#: Quarter of a 1080p frame — past where "neighbours" still means one animal.
REACH_BLOCKS_MAX = 16.0

#: `background_ema`'s constant: settled-to-epsilon, not exact.
SETTLED_EPSILON = 0.01

#: 2D explicit-heat stability limit; `diffuse` sub-steps to stay under it.
MAX_DIFFUSION_NUMBER = 0.25

#: Float, GRAY only: a channel axis would become a third spatial one in the
#: stencil.
SUPPORTED_DTYPES = ("float32", "float64")

FloatArray = NDArray[np.floating[Any]]

#: What this tool is for, in the words of somebody tuning it.
GUIDANCE = """\
Gives the signal a memory, so that a behaviour that comes in bursts reads as one
event rather than ten. An animal grooming produces motion with pauses in it, and
a per-frame measure thresholded per frame breaks that into a handful of short
detections; a second of persistence bridges the pauses and reports the bout.

`reach_blocks` is the same repair across space. A grooming ant straddles two or
three blocks and which one carries the signal flickers between frames, so letting
a quiet block be held up by its busy neighbours makes the detection about the
animal instead of about where the grid happened to fall.

`tau_seconds` has no correct value and is the parameter to spend time on. Too
short and one bout with pauses in it becomes several; too long and two genuinely
separate bouts merge. Aim somewhat longer than the longest pause inside a bout,
and shorter than the shortest gap between two bouts you want counted separately.

Two coupling operators, and they are not interchangeable. `dilate` lets a block
take the strongest of itself and its neighbours, so a sustained event peaks
exactly where it would have without coupling — reach for this one. `diffuse`
spreads the peak down as it spreads it out, which fights the threshold below it,
and by an amount that moves with the reach: switching operators means re-tuning
the threshold. It ships because which one suits real footage is an open question,
not because it is expected to win.

The output lags. A persistence of `tau` reports an event about `tau` late, which
matters the moment an onset is timed or aligned against another data stream, and
particularly against a detector whose window is centred and has no lag of its
own.

Leave it out when the number you are reporting is instantaneous. A flow speed in
pixels per second smeared over a second is not a better speed, it is a wrong
one."""


def decay_lambda(tau_seconds: float, fps: float) -> float:
    # The one definition; every other quantity here is denominated in it.
    return math.exp(-1.0 / (tau_seconds * fps))


def settle_frames(tau_seconds: float, fps: float, epsilon: float = SETTLED_EPSILON) -> int:
    return math.ceil(math.log(epsilon) / math.log(decay_lambda(tau_seconds, fps)))


def group_delay(tau_seconds: float, fps: float) -> float:
    lam = decay_lambda(tau_seconds, fps)
    return lam / (1.0 - lam)


def diffusion_number(reach_blocks: float, tau_seconds: float, fps: float) -> float:
    return reach_blocks * reach_blocks / (2.0 * tau_seconds * fps)


def diffusion_substeps(reach_blocks: float, tau_seconds: float, fps: float) -> int:
    number = diffusion_number(reach_blocks, tau_seconds, fps)
    return max(1, math.ceil(number / MAX_DIFFUSION_NUMBER))


def coupling_weight(reach_blocks: float) -> float:
    if reach_blocks <= 0.0:
        return 0.0
    return math.exp(-1.0 / reach_blocks)


def dilate_radius(reach_blocks: float, tau_seconds: float, fps: float) -> int:
    if reach_blocks <= 0.0:
        return 0
    return max(1, math.ceil(reach_blocks / (tau_seconds * fps)))


class Couple(StrEnum):
    """How a block's neighbours hold it up."""

    #: Grayscale morphological dilation: the largest of a block's own value and
    #: its neighbours' attenuated ones. Attenuates by `1/e` per `reach_blocks`
    #: blocks of separation, and does not lower the peak.
    DILATE = "dilate"
    #: The explicit heat step: activity spreads to a Gaussian standard deviation
    #: of `reach_blocks` blocks over one persistence time, conserving it.
    DIFFUSE = "diffuse"


@dataclass(slots=True)
class MotionHistoryState:
    """One run's accumulator. Minted per run by the executor.

    Mutable, and safe because nothing else can reach it: made from
    `ToolSpec.state_factory` per run rather than closed over, so two replicates
    previewing this node concurrently cannot mix their histories
    (`adr/no-kernel-apparatus.md`).
    """

    #: None until the first frame: no state factory knows the footage's shape.
    accumulator: FloatArray | None = None

    def for_frame(self, data: FloatArray, index: FrameIndex) -> FloatArray:
        """This run's accumulator, sized on `data` if it is the first frame.

        Raises:
            ValueError: if the frame is not a two-dimensional grid, or if its
                shape changed since the accumulator was sized. The executor
                crops every root to a fixed ROI, so a shape change here is a
                resized proxy or a spliced source rather than the graph — and a
                silent restart of the warmup is worse than either.
        """
        if self.accumulator is None:
            if data.ndim != 2:
                raise ValueError(
                    f"motion_history couples over a block neighbourhood and was handed a "
                    f"{data.ndim}-dimensional frame at index {index}; its input is a GRAY grid"
                )
            self.accumulator = np.zeros(data.shape, np.float32)
        elif self.accumulator.shape != data.shape:
            raise ValueError(
                f"motion_history was sized on a {self.accumulator.shape} frame and handed a "
                f"{data.shape} one at index {index}; one run is one geometry"
            )
        return self.accumulator


def run(params: MotionHistoryParams, window: FrameSpan, state: MotionHistoryState, /) -> Frame:
    """Couple, decay, then mix in this frame's rectified signal.

    That order is the semi-implicit step and not an arrangement of three
    commuting operations: coupling the *previous* state means `a[t]` carries the
    coupling applied `t` times, which is what a separate blur node downstream
    cannot reproduce.

    The source is half-wave rectified. A `temporal_baseline` deviation below
    baseline is *less activity than usual*, which contributes nothing to a
    history of activity — and passing the sign through would let `dilate`
    propagate the least-negative value outward and let a lull cancel a bout that
    really happened.

    Raises:
        ValueError: if the frame is not a GRAY grid, or its shape changes
            mid-run. See `MotionHistoryState.for_frame`.
    """
    frame = window.target
    data = np.asarray(frame.data, np.float32)
    accumulator = state.for_frame(data, frame.index)

    coupled = _couple(accumulator, params)
    lam = np.float32(decay_lambda(params.tau_seconds, params.fps))
    np.multiply(coupled, lam, out=accumulator)
    accumulator += (np.float32(1.0) - lam) * np.maximum(data, np.float32(0.0))

    # Copied, not handed out: the next frame overwrites the accumulator in
    # place, and a view would change under a result the GUI is still painting or
    # a store entry that has already been keyed.
    return Frame(data=accumulator.copy(), index=frame.index, channels=ChannelSpec.GRAY)


@register_tool(
    tool_id="motion_history",
    version="1.0.0",
    summary="Leaky accumulator of per-block activity, with neighbourhood coupling.",
    accepts=ArraySpec(dtypes=SUPPORTED_DTYPES, channels=(ChannelSpec.GRAY,)),
    emits=ArraySpec(dtypes=("float32",), channels=(ChannelSpec.GRAY,)),
    # One product, not two: `couple` picks how a block's neighbours hold it up,
    # and what leaves the node is the accumulator either way. The test is
    # whether the settings compute different things or one thing differently.
    emissions=(Emission("history"),),
    run=run,
    # Coupling changes a cell's value, not its correspondence to the input.
    element=ElementRelation.PRESERVED,
    mode=Mode.STREAMING,
    settling_epsilon=SETTLED_EPSILON,
    # `background_ema`'s kind for `background_ema`'s reason: a leaky
    # accumulator decays its history rather than dropping it.
    warmup_kind=WarmupKind.EPSILON,
    stateful=True,
    state_factory=MotionHistoryState,
    guidance=GUIDANCE,
    primary_params=("tau_seconds", "reach_blocks", "couple"),
    caption=(
        CaptionPart(label="tau", param="tau_seconds", format_spec=".2f"),
        CaptionPart(label="reach", param="reach_blocks", format_spec=".1f"),
        CaptionPart(param="couple"),
    ),
    param_stereotypes={
        "tau_seconds": ParamStereotype.SCALAR_RANGE,
        "reach_blocks": ParamStereotype.SCALAR_RANGE,
        "couple": ParamStereotype.ENUM,
        "fps": ParamStereotype.SCALAR_RANGE,
    },
)
class MotionHistoryParams(ParamsBase):
    """How long activity persists, how far it carries, and by which operator."""

    tau_seconds: float = Field(default=1.0, ge=TAU_SECONDS_MIN, le=TAU_SECONDS_MAX)
    #: How far activity is carried from the block where it happened. Zero is a
    #: pure leaky integrator per block — the plain MHI — and is right when a
    #: block is already bigger than an animal.
    reach_blocks: float = Field(default=1.0, ge=0.0, le=REACH_BLOCKS_MAX)
    couple: Couple = Couple.DILATE
    #: Source frame rate, used only to convert the two parameters above into
    #: per-frame quantities. Explicit for `block_signal.fps`'s reason: a `run` is
    #: pure and cannot ask the graph what the container's rate was, so whatever
    #: configures the node writes it from a value it already owns.
    fps: float = Field(default=30.0, gt=0.0, le=FPS_MAX)

    @classmethod
    def max_warmup_frames(cls) -> FrameCount:
        """Worst case over the legal `tau_seconds` and `fps` range."""
        return FrameCount(settle_frames(TAU_SECONDS_MAX, FPS_MAX))

    def warmup_frames(self) -> FrameCount:
        """`settle_frames(tau, fps)` — the bound, refined to this configuration.

        139 frames at the defaults against a bound of 11053, which is what a 10 s
        persistence at 240 fps would need and what every run would decode without
        the refinement (`core/tool_base.py`).
        """
        return FrameCount(settle_frames(self.tau_seconds, self.fps))

    def group_delay_frames(self) -> float:
        return group_delay(self.tau_seconds, self.fps)

    def group_delay_seconds(self) -> float:
        return self.group_delay_frames() / self.fps


def _couple(accumulator: FloatArray, params: MotionHistoryParams) -> FloatArray:
    if params.reach_blocks <= 0.0:
        return accumulator
    if params.couple is Couple.DIFFUSE:
        return _diffuse(accumulator, params)
    return _dilate(
        accumulator,
        coupling_weight(params.reach_blocks),
        dilate_radius(params.reach_blocks, params.tau_seconds, params.fps),
    )


def _diffuse(accumulator: FloatArray, params: MotionHistoryParams) -> FloatArray:
    """The five-point explicit heat step, sub-stepped to stay stable.

    The sub-step count is a cost rather than a refusal on purpose: the stability
    constraint couples three parameters, two of which the user is not thinking
    about while dragging the third, so a validator rejecting the combination
    would land as a slider that stops responding.
    """
    steps = diffusion_substeps(params.reach_blocks, params.tau_seconds, params.fps)
    c = np.float32(diffusion_number(params.reach_blocks, params.tau_seconds, params.fps) / steps)
    field = accumulator.astype(np.float32, copy=True)
    for _ in range(steps):
        # mode="edge": reflecting boundary, zero outward gradient at the wall.
        # Zero-padding would drain every edge block, which is where an animal
        # walking the arena perimeter lives.
        padded = np.pad(field, ((1, 1), (1, 1)), mode="edge")
        neighbours = padded[:-2, 1:-1] + padded[2:, 1:-1] + padded[1:-1, :-2] + padded[1:-1, 2:]
        field += c * (neighbours - 4.0 * field)
    return field


def _dilate(accumulator: FloatArray, kappa: float, radius: int) -> FloatArray:
    # Sliced, not padded: -inf (max's neutral element) breaks the multiply,
    # edge-padding invents activity at the wall; slicing to overlap avoids
    # both, and the centre offset guarantees a contributor.
    out = accumulator.copy()
    rows, cols = accumulator.shape
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dy == 0 and dx == 0:
                continue
            weight = np.float32(kappa ** math.hypot(dy, dx))
            src = accumulator[max(0, dy) : rows - max(0, -dy), max(0, dx) : cols - max(0, -dx)]
            dst = out[max(0, -dy) : rows - max(0, dy), max(0, -dx) : cols - max(0, dx)]
            np.maximum(dst, weight * src, out=dst)
    return out
