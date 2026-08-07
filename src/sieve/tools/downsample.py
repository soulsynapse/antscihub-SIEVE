"""Reduce spatial resolution by an integer factor.

The first tool, chosen because it is trivially checkable against arithmetic
rather than against a reference image: the output shape is `(h // factor,
w // factor)` and, with anti-aliasing off, every output pixel is a pixel that
was in the input. It exercises everything the contract has to carry — a params
model, declared I/O, streaming mode, an element relation, presentation
stereotypes — without any of the correctness questions a detector would drag
in.

v2 declared a `CostEstimate` and a `frame_bytes_ratio` here, and both are cut:
each fed machinery v3 has not built, and a declaration arrives with its consumer
(`adr/declared-means-verified.md`). `frame_bytes_ratio` is the one worth naming,
because it is not speculative — VISION step 4's storage readout is what wants it,
putting a 4x downsample in front of a checkpoint being the difference between
storing a run and not being able to. It comes back in Phase 5, with that readout.

v2 also reached this kernel through a per-backend dispatch table. `run` below is
the whole of what replaced it (`adr/no-kernel-apparatus.md`): the spec points at
the function, the executor calls it, and what keeps the cv2 call honest is the
declared version entering the cache key.
"""

from __future__ import annotations

import cv2
import numpy as np
from pydantic import Field

from sieve.core.tool_base import (
    ArraySpec,
    CaptionPart,
    ElementRelation,
    Mode,
    ParamsBase,
    ParamStereotype,
)
from sieve.core.tool_registry import register_tool
from sieve.core.types import Frame, FrameSpan

#: What `cv2.INTER_AREA` will actually accept. Narrower than the stride path,
#: which works on anything, but a declaration has to hold for every setting of
#: every parameter — a spec that is true only when `anti_alias` is off is not a
#: static declaration, it is a runtime branch written in the wrong place.
SUPPORTED_DTYPES = ("uint8", "uint16", "float32", "float64")


def run(params: DownsampleParams, window: FrameSpan, state: None, /) -> Frame:
    """Downsample the frame this streaming node was handed.

    `window` holds exactly one frame and `state` is `None`, which is what a
    streaming, stateless tool's half of the one signature looks like — the
    signature is one shape for every tool so that which shape a node gets is not
    something the executor decides per tool.

    Raises:
        ValueError: if `factor` exceeds either extent, which would produce a
            frame with a zero-length axis. Raising is deliberate over clamping:
            it means a crop small enough to vanish under the graph's own
            downsample, and silently returning a 1x1 frame would let a tuning
            session proceed against nothing.
    """
    frame = window.frames[-1]
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


@register_tool(
    tool_id="downsample",
    version="1.0.0",
    summary="Reduce spatial resolution by an integer factor.",
    accepts=ArraySpec(dtypes=SUPPORTED_DTYPES),
    # Channels are unstated on both sides because the tool preserves them:
    # constraining `emits` would claim knowledge of the source that this tool
    # does not have, and constraining `accepts` would reject frames it handles.
    emits=ArraySpec(dtypes=SUPPORTED_DTYPES),
    run=run,
    # One output element is `factor**2` input elements. Kind-dependent rather
    # than destructive: a mean of pixels is the scene sampled more coarsely and
    # is still pixels, so a detection here counts pixels honestly; a mean of
    # `block_signal`'s blocks is not a block, and a count threshold denominated
    # in blocks has nothing to be taken over.
    element=ElementRelation.AGGREGATED,
    mode=Mode.STREAMING,
    primary_params=("factor",),
    caption=(CaptionPart(label="factor", param="factor"),),
    param_stereotypes={
        "factor": ParamStereotype.SCALAR_RANGE,
        # A two-valued choice is still a choice from a fixed set, and the labels
        # below are what makes it read as one: `anti_alias: True` on a button
        # names the mechanism, and "average" names what the user is picking.
        "anti_alias": ParamStereotype.ENUM,
    },
    param_value_labels={"anti_alias": {"True": "average", "False": "sample"}},
)
class DownsampleParams(ParamsBase):
    """How far to reduce, and whether to average or to sample."""

    #: Lower bound 2 because a factor of 1 is a tool that should not be in the
    #: graph rather than a tool that does nothing — a no-op node still costs a
    #: cache entry and a copy. Upper bound 64 keeps the guard in `run` from being
    #: the only thing standing between a typo and a zero-sized frame.
    factor: int = Field(default=2, ge=2, le=64)
    #: True averages each `factor`x`factor` block (`cv2.INTER_AREA`); False
    #: takes the top-left pixel of it. Averaging is right for measuring
    #: intensity and wrong for preserving a one-pixel marker, which is a
    #: question about the footage and so is a parameter rather than a default
    #: this module gets to make on the user's behalf.
    anti_alias: bool = True
