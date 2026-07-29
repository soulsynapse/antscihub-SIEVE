from __future__ import annotations

import cv2
from pydantic import Field

from sieve.backend.dispatch import Backend, kernel
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


@register_filter(
    filter_id="rescale",
    version="1.0.0",
    summary="Reduce spatial resolution by a float linear scale factor.",
    accepts=ArraySpec(dtypes=SUPPORTED_DTYPES),
    emits=ArraySpec(dtypes=SUPPORTED_DTYPES),
    element=ElementRelation.AGGREGATED,
    cost=CostEstimate(
        seconds_per_megapixel=0.00035,
        peak_bytes_per_input_byte=2.0,
    ),
    mode=Mode.STREAMING,
    primary_params=("scale",),
)
class RescaleParams(ParamsBase):
    scale: float = Field(default=1.0, ge=0.05, le=1.0)

    def frame_bytes_ratio(self) -> float:
        return self.scale**2


@kernel(RescaleParams, Backend.CPU)
def rescale_cpu(frame: Frame, params: RescaleParams) -> Frame:
    if params.scale >= 1.0:
        return frame
    height, width = frame.data.shape[:2]
    out_width = max(1, round(width * params.scale))
    out_height = max(1, round(height * params.scale))
    data = cv2.resize(frame.data, (out_width, out_height), interpolation=cv2.INTER_AREA)
    return Frame(data=data, index=frame.index, channels=frame.channels)
