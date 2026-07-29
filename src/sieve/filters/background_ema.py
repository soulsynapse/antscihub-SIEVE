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


SUPPORTED_DTYPES = ("uint8", "uint16", "float32", "float64")


MIN_ALPHA = 0.05


SETTLED_EPSILON = 0.01


def settle_frames(alpha: float, epsilon: float = SETTLED_EPSILON) -> int:
    if alpha >= 1.0:
        return 1
    return math.ceil(math.log(epsilon) / math.log(1.0 - alpha))


class Emit(StrEnum):
    FOREGROUND = "foreground"

    BACKGROUND = "background"


@register_filter(
    filter_id="background_ema",
    version="1.0.0",
    summary="Exponential moving-average background model, and the difference from it.",
    accepts=ArraySpec(dtypes=SUPPORTED_DTYPES),
    emits=ArraySpec(dtypes=SUPPORTED_DTYPES),
    element=ElementRelation.PRESERVED,
    cost=CostEstimate(
        seconds_per_megapixel=0.0099,
        peak_bytes_per_input_byte=14.0,
    ),
    mode=Mode.STREAMING,
    warmup_frames=90,
    stateful=True,
    primary_params=("alpha", "emit"),
)
class BackgroundEmaParams(ParamsBase):
    alpha: float = Field(default=MIN_ALPHA, ge=MIN_ALPHA, le=1.0)
    emit: Emit = Emit.FOREGROUND

    def warmup_frames(self) -> int:
        return settle_frames(self.alpha)


FloatArray = NDArray[np.floating[Any]]


@dataclass(slots=True)
class _Buffers:
    model: FloatArray

    widened: FloatArray

    scratch: FloatArray


@dataclass(slots=True)
class BackgroundState:
    buffers: _Buffers | None = None

    def for_frame(self, data: NDArray[Any], index: int) -> _Buffers:
        if self.buffers is None:
            model = data.astype(np.promote_types(data.dtype, np.float32))
            self.buffers = _Buffers(
                model=model, widened=np.empty_like(model), scratch=np.empty_like(model)
            )
        elif self.buffers.model.shape != data.shape:
            raise ValueError(
                f"background_ema was seeded on a {self.buffers.model.shape} frame and handed a "
                f"{data.shape} one at index {index}; one run is one geometry"
            )
        return self.buffers


@stateful_kernel(BackgroundEmaParams, Backend.CPU, state=BackgroundState)
def background_ema_cpu(
    frame: Frame, params: BackgroundEmaParams, state: BackgroundState
) -> Frame:
    buffers = state.for_frame(frame.data, frame.index)
    model, widened, scratch = buffers.model, buffers.widened, buffers.scratch
    np.copyto(widened, frame.data, casting="unsafe")
    np.subtract(widened, model, out=scratch)
    np.multiply(scratch, scratch.dtype.type(params.alpha), out=scratch)
    np.add(model, scratch, out=model)
    if params.emit is Emit.BACKGROUND:
        produced = model
    else:
        np.subtract(widened, model, out=scratch)
        produced = np.abs(scratch, out=scratch)
    return Frame(
        data=_narrow(produced, frame.data.dtype),
        index=frame.index,
        channels=frame.channels,
    )


def _narrow(values: FloatArray, dtype: np.dtype[Any]) -> NDArray[Any]:
    if np.issubdtype(dtype, np.floating):
        return values.astype(dtype)
    return np.rint(values).astype(dtype)
