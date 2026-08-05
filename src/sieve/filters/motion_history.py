"""A causal leaky accumulator over per-block activity, with neighbourhood
coupling folded inside the feedback loop rather than composed from a separate
blur node -- the semi-implicit Euler step `REFINED-VISION.md` section C
derives. `motion_history.md` beside this file has the science, the parameter
guidance, and the two coupling modes' tradeoffs.

**Decay and coupling are one node, two parameters.** Coupling applies to the
previous state before it decays and before this frame's signal mixes in --
`a[t] = lambda * C(a[t-1]) + (1 - lambda) * s[t]` -- so `a[t]` carries `C`
applied `t` times rather than once. A `motion_history` node followed by a blur
node cannot produce this; the composition that could would need the two to
share state.

**Stateful, and therefore uncacheable**, for `background_ema`'s reason
verbatim: nothing that derives a key can tell an honest `warmup_frames` from a
false one, so the exclusion is on the category. See
`docs/findings/2026.07.26-stateful-output-is-not-keyed-by-what-it-is.md`.

**Group delay is declared, not removed.** Zero-phase removal needs the whole
record in hand, which is `Mode.WINDOWED` and a kernel protocol that does not
exist yet (`docs/todo/kernel-protocol-beyond-one-frame.md`). `group_delay`
below is exposed as a function with a test rather than a `FilterSpec` field,
because no consumer reads it yet.
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
    CostEstimate,
    ElementRelation,
    Mode,
    ParamsBase,
)
from sieve.core.filter_registry import register_filter
from sieve.core.types import ChannelSpec, Frame, FrameCount

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


#: Worst case over the legal range; no run pays it.
MAX_WARMUP_FRAMES = FrameCount(settle_frames(TAU_SECONDS_MAX, FPS_MAX))


class Couple(StrEnum):
    DILATE = "dilate"
    DIFFUSE = "diffuse"


@register_filter(
    filter_id="motion_history",
    version="1.0.0",
    summary="Leaky accumulator of per-block activity, with neighbourhood coupling.",
    accepts=ArraySpec(dtypes=SUPPORTED_DTYPES, channels=(ChannelSpec.GRAY,)),
    emits=ArraySpec(dtypes=("float32",), channels=(ChannelSpec.GRAY,)),
    # Coupling changes a cell's value, not its correspondence to the input.
    element=ElementRelation.PRESERVED,
    cost=CostEstimate(
        # 0.035ms/frame at defaults (dilate, the default); diffuse sub-steps,
        # so this isn't the worst case.
        seconds_per_megapixel=0.017,
        peak_bytes_per_input_byte=5.0,
    ),
    mode=Mode.STREAMING,
    # The bound, not what a run pays. See MAX_WARMUP_FRAMES.
    warmup_frames=MAX_WARMUP_FRAMES,
    stateful=True,
    primary_params=("tau_seconds", "reach_blocks", "couple"),
)
class MotionHistoryParams(ParamsBase):
    tau_seconds: float = Field(default=1.0, ge=TAU_SECONDS_MIN, le=TAU_SECONDS_MAX)
    reach_blocks: float = Field(default=1.0, ge=0.0, le=REACH_BLOCKS_MAX)
    couple: Couple = Couple.DILATE
    fps: float = Field(default=30.0, gt=0.0, le=FPS_MAX)

    def warmup_frames(self) -> FrameCount:
        return FrameCount(settle_frames(self.tau_seconds, self.fps))

    def group_delay_frames(self) -> float:
        return group_delay(self.tau_seconds, self.fps)

    def group_delay_seconds(self) -> float:
        return self.group_delay_frames() / self.fps


@dataclass(slots=True)
class MotionHistoryState:
    # None until the first frame: no state factory knows the footage's shape.
    accumulator: FloatArray | None = None

    def for_frame(self, data: FloatArray, index: int) -> FloatArray:
        # Executor crops every root to a fixed ROI; a shape change here is a
        # resized proxy or spliced source, not the graph -- raise rather than
        # silently restart the warmup.
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


@stateful_kernel(MotionHistoryParams, Backend.CPU, state=MotionHistoryState)
def motion_history_cpu(
    frame: Frame, params: MotionHistoryParams, state: MotionHistoryState
) -> Frame:
    data = np.asarray(frame.data, np.float32)
    accumulator = state.for_frame(data, frame.index)

    coupled = _couple(accumulator, params)
    lam = np.float32(decay_lambda(params.tau_seconds, params.fps))
    np.multiply(coupled, lam, out=accumulator)
    accumulator += (np.float32(1.0) - lam) * np.maximum(data, np.float32(0.0))

    return Frame(data=accumulator.copy(), index=frame.index, channels=ChannelSpec.GRAY)


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
    steps = diffusion_substeps(params.reach_blocks, params.tau_seconds, params.fps)
    c = np.float32(diffusion_number(params.reach_blocks, params.tau_seconds, params.fps) / steps)
    field = accumulator.astype(np.float32, copy=True)
    for _ in range(steps):
        # mode="edge": reflecting boundary, zero outward gradient at the wall.
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
