from __future__ import annotations

from enum import StrEnum
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

from sieve.backend.dispatch import Backend, kernel
from sieve.core.filter_base import (
    ArraySpec,
    CostEstimate,
    ElementRelation,
    Mode,
    ParamsBase,
)
from sieve.core.filter_registry import register_filter
from sieve.core.types import ChannelSpec, Frame


TARGET_MEAN = 128.0
TARGET_SD = 32.0


MIN_STD = 1e-6


SUPPORTED_DTYPES = ("uint8", "uint16", "float32", "float64")


class NormalizeMode(StrEnum):
    OFF = "off"
    ZSCORE = "zscore"


@register_filter(
    filter_id="normalize",
    version="1.0.0",
    summary="Per-frame contrast normalization to a fixed mean and spread.",
    accepts=ArraySpec(dtypes=SUPPORTED_DTYPES),
    emits=ArraySpec(dtypes=SUPPORTED_DTYPES),
    element=ElementRelation.PRESERVED,
    cost=CostEstimate(
        seconds_per_megapixel=0.0015,
        peak_bytes_per_input_byte=6.0,
    ),
    mode=Mode.STREAMING,
    primary_params=("mode",),
)
class NormalizeParams(ParamsBase):
    mode: NormalizeMode = NormalizeMode.OFF


@kernel(NormalizeParams, Backend.CPU)
def normalize_cpu(frame: Frame, params: NormalizeParams) -> Frame:
    if params.mode is NormalizeMode.OFF:
        return frame
    data = np.asarray(frame.data, np.float32)
    mean, std = _gray_stats(data, frame.channels)
    if std < MIN_STD:
        out = np.subtract(data, np.float32(mean), dtype=np.float32)
    else:
        a = TARGET_SD / std
        out = np.multiply(data, np.float32(a), dtype=np.float32)
        np.add(out, np.float32(TARGET_MEAN - mean * a), out=out)
    return Frame(data=out, index=frame.index, channels=frame.channels)


def _gray_stats(
    data: NDArray[np.float32], channels: ChannelSpec
) -> tuple[float, float]:
    if channels is ChannelSpec.GRAY:
        gray = data
    else:
        code = cv2.COLOR_BGR2GRAY if channels is ChannelSpec.BGR else cv2.COLOR_RGB2GRAY
        gray = cv2.cvtColor(data, code)
    m: Any
    s: Any
    m, s = cv2.meanStdDev(gray)
    return float(m[0, 0]), float(s[0, 0])
