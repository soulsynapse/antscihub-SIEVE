"""Reduce spatial resolution by an integer factor.

The first filter, chosen because it is trivially checkable against arithmetic
rather than against a reference image: the output shape is `(h // factor,
w // factor)` and, with anti-aliasing off, every output pixel is a pixel that
was in the input. It exercises everything the contract has to carry — a params
model, declared I/O, streaming mode, a params-derived output size, and a kernel
registered per backend — without any of the correctness questions a detector
would drag in.

It is also the filter VISION step 4's storage readout most wants to exist:
`frame_bytes_ratio` is `1 / factor**2`, so putting a 4x downsample in front of a
checkpoint is the difference between storing a run and not being able to.
"""

from __future__ import annotations

import cv2
import numpy as np
from pydantic import Field

from sieve.backend.dispatch import Backend, kernel
from sieve.core.filter_base import (
    ArraySpec,
    AuthoringGroup,
    CaptionPart,
    CostEstimate,
    ElementRelation,
    Mode,
    ParamsBase,
)
from sieve.core.filter_registry import register_filter
from sieve.core.types import Frame, WorkUnits

#: What `cv2.INTER_AREA` will actually accept. Narrower than the stride path,
#: which works on anything, but a declaration has to hold for every setting of
#: every parameter — a spec that is true only when `anti_alias` is off is not a
#: static declaration, it is a runtime branch written in the wrong place.
SUPPORTED_DTYPES = ("uint8", "uint16", "float32", "float64")


@register_filter(
    filter_id="downsample",
    version="1.0.0",
    summary="Reduce spatial resolution by an integer factor.",
    accepts=ArraySpec(dtypes=SUPPORTED_DTYPES),
    # Channels are unstated on both sides because the filter preserves them:
    # constraining `emits` would claim knowledge of the source that this filter
    # does not have, and constraining `accepts` would reject frames it handles.
    emits=ArraySpec(dtypes=SUPPORTED_DTYPES),
    # One output element is `factor**2` input elements. Kind-dependent rather
    # than destructive: a mean of pixels is the scene sampled more coarsely and
    # is still pixels, so a detection here counts pixels honestly; a mean of
    # `block_signal`'s blocks is not a block, and a count threshold denominated
    # in blocks has nothing to be taken over.
    element=ElementRelation.AGGREGATED,
    cost=CostEstimate(
        # The static declaration takes the anti-aliased path: one neighborhood
        # read and one smaller write, stated relative to a full-frame copy
        # rather than as one machine's elapsed time.
        work_per_megapixel=WorkUnits(2.0),
        # Input plus an output that is at most a quarter of it, no scratch.
        # Static, so it takes the largest value any legal `factor` produces.
        peak_bytes_per_input_byte=1.25,
    ),
    authoring_group=AuthoringGroup.SPATIAL_PREP,
    mode=Mode.STREAMING,
    primary_params=("factor",),
    caption=(CaptionPart(label="factor", param="factor"),),
)
class DownsampleParams(ParamsBase):
    """How far to reduce, and whether to average or to sample."""

    #: Lower bound 2 because a factor of 1 is a filter that should not be in the
    #: graph rather than a filter that does nothing — a no-op node still costs a
    #: cache entry and a copy. Upper bound 64 keeps the guard below from being
    #: the only thing standing between a typo and a zero-sized frame.
    factor: int = Field(default=2, ge=2, le=64)
    #: True averages each `factor`x`factor` block (`cv2.INTER_AREA`); False
    #: takes the top-left pixel of it. Averaging is right for measuring
    #: intensity and wrong for preserving a one-pixel marker, which is a
    #: question about the footage and so is a parameter rather than a default
    #: this module gets to make on the user's behalf.
    anti_alias: bool = True

    def frame_bytes_ratio(self) -> float:
        """Both axes shrink, so bytes go as the square.

        Exact only when `factor` divides both extents; off by less than a row
        and a column otherwise. This feeds a storage prediction and never a
        correctness decision, which is why an approximation is allowed to stand
        here and would not be allowed to stand in `output_rate`.
        """
        return 1.0 / (self.factor**2)


@kernel(DownsampleParams, Backend.CPU)
def downsample_cpu(frame: Frame, params: DownsampleParams) -> Frame:
    """Downsample on the host.

    Raises:
        ValueError: if `factor` exceeds either extent, which would produce a
            frame with a zero-length axis. Raising is deliberate over clamping:
            it means a crop small enough to vanish under the graph's own
            downsample, and silently returning a 1x1 frame would let a tuning
            session proceed against nothing.
    """
    height, width = frame.data.shape[:2]
    out_height, out_width = height // params.factor, width // params.factor
    if out_height == 0 or out_width == 0:
        raise ValueError(
            f"downsample by {params.factor} leaves nothing of a {width}x{height} frame"
        )

    if params.anti_alias:
        data = cv2.resize(frame.data, (out_width, out_height), interpolation=cv2.INTER_AREA)
    else:
        # Sliced to a multiple of `factor` first so both paths agree on shape;
        # a bare `[::factor]` rounds up and would make the output size depend on
        # a parameter that is supposed to only change pixel values.
        #
        # `ascontiguousarray` because a stride view keeps the whole source frame
        # alive — in a streaming pipeline that is the entire point of
        # downsampling defeated, one retained frame at a time.
        stride = params.factor
        view = frame.data[: out_height * stride : stride, : out_width * stride : stride]
        data = np.ascontiguousarray(view)

    return Frame(data=data, index=frame.index, channels=frame.channels)
