"""Reduce spatial resolution by a float linear scale factor.

**Why a new filter rather than a params-v2 of `downsample`** (the parity plan's
item 2 open decision): the two do not share a parameter space or an output
geometry. `downsample` divides both extents by an integer and truncates —
composable, exact, the right tool for making a checkpoint fit. `rescale`
multiplies by a float and rounds — v1's semantic, the one the live tab's
Downsample spinbox exposes, where 0.250 means "25 % linear, 6.25 % of the
pixels" and the block grid arithmetic (`block_signal`'s `0 = auto`) is defined
against the same scale. Migrating `downsample` would break every existing
cache key and pipeline artifact to make one filter answer two questions; two
filters each keep one honest declaration.

The parity semantic, from v1's `Preprocessor._downsample`:
`width/height = round(src x scale)`, `cv2.INTER_AREA`, exact no-op at
`scale = 1.0`. INTER_AREA is the correct interpolation for shrinking — it
area-averages, which low-pass filters before decimating; INTER_LINEAR would
alias high spatial frequencies into the flow field the extraction filter
measures.
"""

from __future__ import annotations

import cv2
from pydantic import Field

from sieve.backend.dispatch import Backend, kernel
from sieve.core.filter_base import (
    ArraySpec,
    CaptionPart,
    CostEstimate,
    ElementRelation,
    Mode,
    ParamsBase,
)
from sieve.core.filter_registry import register_filter
from sieve.core.types import Frame, WorkUnits

#: What `cv2.resize` with INTER_AREA accepts — the same set as `downsample`,
#: for the same reason: a declaration must hold for every parameter setting.
SUPPORTED_DTYPES = ("uint8", "uint16", "float32", "float64")


@register_filter(
    filter_id="rescale",
    version="1.0.0",
    summary="Reduce spatial resolution by a float linear scale factor.",
    accepts=ArraySpec(dtypes=SUPPORTED_DTYPES),
    # Channels unstated on both sides: the filter preserves whatever layout it
    # is handed.
    emits=ArraySpec(dtypes=SUPPORTED_DTYPES),
    # `downsample`'s relation at a float scale, and for its reason.
    element=ElementRelation.AGGREGATED,
    cost=CostEstimate(
        # Same copy-equivalent tier as `downsample`'s anti-aliased path.
        work_per_megapixel=WorkUnits(2.0),
        # Input plus an output no larger than it, no scratch.
        peak_bytes_per_input_byte=2.0,
    ),
    mode=Mode.STREAMING,
    primary_params=("scale",),
    caption=(
        CaptionPart(label="scale", param="scale", format_spec=".2f"),
        CaptionPart(text="area"),
    ),
)
class RescaleParams(ParamsBase):
    """How far to shrink, as a linear factor of both extents."""

    #: Linear scale for both axes, v1's range: 0.05-1.0. 1.0 is a declared
    #: no-op (unlike `downsample`, whose factor starts at 2) because the tab's
    #: spinbox legitimately rests there — "full resolution" is a setting of
    #: this parameter, not the absence of the step.
    scale: float = Field(default=1.0, ge=0.05, le=1.0)

    def frame_bytes_ratio(self) -> float:
        """Both axes shrink linearly, so bytes go as the square.

        Exact up to rounding of each extent; feeds the storage prediction,
        never a correctness decision.
        """
        return self.scale**2


@kernel(RescaleParams, Backend.CPU)
def rescale_cpu(frame: Frame, params: RescaleParams) -> Frame:
    """Shrink on the host, or hand the frame through untouched at 1.0.

    The no-op path returns the input frame object itself: v1 verified that
    INTER_AREA at scale 1 is bit-identical to its input, so skipping the call
    is free of numerical change and saves a full-frame copy per frame.

    Output extents are `max(1, round(src x scale))` — rounding is v1's
    semantic, and the floor of 1 px means the smallest legal scale on a tiny
    crop degrades to a single pixel rather than a zero-length axis nothing
    downstream can hold.
    """
    if params.scale >= 1.0:
        return frame
    height, width = frame.data.shape[:2]
    out_width = max(1, round(width * params.scale))
    out_height = max(1, round(height * params.scale))
    data = cv2.resize(frame.data, (out_width, out_height), interpolation=cv2.INTER_AREA)
    return Frame(data=data, index=frame.index, channels=frame.channels)
