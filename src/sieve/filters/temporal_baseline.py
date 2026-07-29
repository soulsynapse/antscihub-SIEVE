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
from sieve.core.types import Frame


MAD_TO_SIGMA = 1.4826


WINDOW_SECONDS_MAX = 30.0


FPS_MAX = 240.0


MAX_SAMPLES = 256


SUPPORTED_DTYPES = ("float32", "float64")

FloatArray = NDArray[np.floating[Any]]


def window_frames(window_seconds: float, fps: float) -> int:
    return max(1, math.ceil(window_seconds * fps))


def sample_stride(frames: int) -> int:
    return max(1, -(-frames // MAX_SAMPLES))


def ring_capacity(frames: int) -> int:
    stride = sample_stride(frames)
    return min(MAX_SAMPLES, -(-frames // stride))


MAX_WARMUP_FRAMES = window_frames(WINDOW_SECONDS_MAX, FPS_MAX) - 1


class Emit(StrEnum):
    DEVIATION = "deviation"

    BASELINE = "baseline"


@register_filter(
    filter_id="temporal_baseline",
    version="1.0.0",
    summary="Per-cell trailing median/MAD baseline, and the signal in deviations from it.",
    accepts=ArraySpec(dtypes=SUPPORTED_DTYPES),
    emits=ArraySpec(dtypes=("float32",)),
    element=ElementRelation.PRESERVED,
    cost=CostEstimate(
        seconds_per_megapixel=3.9,
        peak_bytes_per_input_byte=2.0 * MAX_SAMPLES + 4.0,
    ),
    mode=Mode.STREAMING,
    warmup_frames=MAX_WARMUP_FRAMES,
    stateful=True,
    primary_params=("window_seconds", "emit"),
)
class TemporalBaselineParams(ParamsBase):
    window_seconds: float = Field(default=5.0, ge=0.5, le=WINDOW_SECONDS_MAX)

    fps: float = Field(default=30.0, gt=0.0, le=FPS_MAX)
    emit: Emit = Emit.DEVIATION

    def frames(self) -> int:
        return window_frames(self.window_seconds, self.fps)

    def warmup_frames(self) -> int:
        return self.frames() - 1


@dataclass(slots=True)
class BaselineState:
    ring: FloatArray | None = None

    scratch: FloatArray | None = None

    filled: int = 0

    write: int = 0

    seen: int = 0

    estimate: tuple[FloatArray, FloatArray] | None = None

    def admit(self, data: FloatArray, capacity: int, index: int) -> None:
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
    data = np.asarray(frame.data, np.float32)
    frames = params.frames()
    if state.seen % sample_stride(frames) == 0:
        state.admit(data, ring_capacity(frames), frame.index)
    state.seen += 1
    if state.estimate is None:
        state.estimate = _estimate(state)
    baseline, spread = state.estimate
    if params.emit is Emit.BASELINE:
        produced = baseline.copy()
    else:
        usable = spread > 0.0
        produced = np.where(
            usable, (data - baseline) / np.where(usable, spread, 1.0), 0.0
        )
    return Frame(
        data=produced.astype(np.float32, copy=False),
        index=frame.index,
        channels=frame.channels,
    )


def _estimate(state: BaselineState) -> tuple[FloatArray, FloatArray]:
    ring, scratch = state.ring, state.scratch
    assert ring is not None and scratch is not None
    held, work = ring[: state.filled], scratch[: state.filled]
    work[...] = held
    baseline = np.median(work, axis=0, overwrite_input=True)
    np.abs(np.subtract(held, baseline, out=work), out=work)
    spread = np.median(work, axis=0, overwrite_input=True) * np.float32(MAD_TO_SIGMA)
    return baseline, _floored(spread)


def _floored(spread: FloatArray) -> FloatArray:
    positive = spread[spread > 0.0]
    if positive.size == 0:
        return spread
    return np.where(spread > 0.0, spread, np.median(positive))
