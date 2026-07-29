













from __future__ import annotations

import cv2
import numpy as np
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
    filter_id="downsample",
    version="1.0.0",
    summary="Reduce spatial resolution by an integer factor.",
    accepts=ArraySpec(dtypes=SUPPORTED_DTYPES),



    emits=ArraySpec(dtypes=SUPPORTED_DTYPES),





    element=ElementRelation.AGGREGATED,
    cost=CostEstimate(



        seconds_per_megapixel=0.00035,


        peak_bytes_per_input_byte=1.25,
    ),
    mode=Mode.STREAMING,
    primary_params=("factor",),
)
class DownsampleParams(ParamsBase):






    factor: int = Field(default=2, ge=2, le=64)





    anti_alias: bool = True

    def frame_bytes_ratio(self) -> float:







        return 1.0 / (self.factor**2)


@kernel(DownsampleParams, Backend.CPU)
def downsample_cpu(frame: Frame, params: DownsampleParams) -> Frame:









    height, width = frame.data.shape[:2]
    out_height, out_width = height // params.factor, width // params.factor
    if out_height == 0 or out_width == 0:
        raise ValueError(
            f"downsample by {params.factor} leaves nothing of a {width}x{height} frame"
        )

    if params.anti_alias:
        data = cv2.resize(frame.data, (out_width, out_height), interpolation=cv2.INTER_AREA)
    else:







        stride = params.factor
        view = frame.data[: out_height * stride : stride, : out_width * stride : stride]
        data = np.ascontiguousarray(view)

    return Frame(data=data, index=frame.index, channels=frame.channels)
