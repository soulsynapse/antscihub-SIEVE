"""Reduce spatial resolution by a float linear scale factor.

**Why this is a second tool and not `downsample` with a wider parameter**, which
is the question v2 settled and the answer carries: the two do not share a
parameter space or an output geometry. `downsample` divides both extents by an
integer and truncates — composable, exact, the right thing for making a
checkpoint fit. `rescale` multiplies by a float and rounds, which is v1's
semantic and the one a Downsample spinbox exposes, where 0.250 means "25 %
linear, 6.25 % of the pixels" and the block grid arithmetic (`block_signal`'s
`0 = auto`) is defined against the same scale. One tool answering both questions
would have to pick which of the two geometries its declaration describes.

The parity semantic, from v1's `Preprocessor._downsample`:
`width/height = round(src x scale)`, `cv2.INTER_AREA`, exact no-op at
`scale = 1.0`. INTER_AREA is the correct interpolation for shrinking — it
area-averages, which is a low-pass ahead of the decimation; INTER_LINEAR would
alias high spatial frequencies into whatever series a downstream detector
measures.

v2 declared a `CostEstimate` and a `frame_bytes_ratio` here and both are cut,
for the reason `downsample.py` records at more length: each fed machinery v3 has
not built, and a declaration arrives with its consumer
(`adr/declared-means-verified.md`). The ratio is `scale**2` when the storage
readout comes to want it.
"""

from __future__ import annotations

import cv2
from pydantic import Field

from sieve.core.tool_base import (
    ArraySpec,
    CaptionPart,
    ElementRelation,
    Emission,
    Mode,
    ParamsBase,
    ParamStereotype,
)
from sieve.core.tool_registry import register_tool
from sieve.core.types import Frame, FrameSpan

#: What `cv2.resize` with INTER_AREA accepts — `downsample`'s set, for
#: `downsample`'s reason: a declaration has to hold for every setting of every
#: parameter, so it names what the narrowest path admits rather than what this
#: configuration happens to reach.
SUPPORTED_DTYPES = ("uint8", "uint16", "float32", "float64")

#: What this tool is for, in the words of somebody tuning it.
GUIDANCE = """\
Shrinks every frame by a fraction of its width and height, so 0.25 leaves a
quarter of the width, a quarter of the height, and a sixteenth of the pixels.
This is the resolution knob to reach for first: it is how much of the footage's
detail the rest of the pipeline gets to see, and it is usually the largest single
lever on how fast the tuning loop runs.

1.0 is a real setting and does nothing at all — the frame is handed on
untouched — so the scale can be dragged back to the top without taking the node
out of the graph.

The pixels that come out are area averages of the ones that went in, which is the
right thing when anything downstream measures change over time: the alternative
lets fine texture alias into the signal as motion nothing in the arena made.

Set it before tuning a block grid or drawing a region. `block_signal` holds its
blocks fixed in the *source's* pixels, so moving this scale changes how much
compute a block costs rather than where a detection lands; a region drawn on the
canvas, though, is in the pixels of the frame the node was handed, and rescaling
underneath one moves it.

Use `downsample` instead when the frames are being kept rather than measured: a
whole-number divisor composes exactly and never rounds an extent."""


def run(params: RescaleParams, window: FrameSpan, state: None, /) -> Frame:
    """Shrink the target frame, or hand it through untouched at 1.0.

    The no-op path returns the input frame object itself rather than a copy of
    it, which `span.py` also does and for the same accounting: v1 verified that
    INTER_AREA at scale 1 is bit-identical to its input, so there is no
    numerical difference for the copy to preserve and nothing it could release —
    the output *is* the input.

    Output extents are `max(1, round(src x scale))`. The floor of 1 px is where
    this parts company with `downsample`, which raises instead: an integer
    factor larger than an extent means a graph configured for a frame it is not
    being shown, while every scale in this parameter's range is one a user may
    legitimately rest on, and it is the frame that shrank underneath it.
    """
    del state
    frame = window.target
    if params.scale >= 1.0:
        return frame
    out_width = max(1, round(frame.width * params.scale))
    out_height = max(1, round(frame.height * params.scale))
    data = cv2.resize(frame.data, (out_width, out_height), interpolation=cv2.INTER_AREA)
    return Frame(data=data, index=frame.index, channels=frame.channels)


@register_tool(
    tool_id="rescale",
    version="1.0.0",
    summary="Reduce spatial resolution by a float linear scale factor.",
    accepts=ArraySpec(dtypes=SUPPORTED_DTYPES),
    # Channels unstated on both sides: the tool preserves whatever layout it is
    # handed, and constraining either side would reject frames it handles.
    emits=ArraySpec(dtypes=SUPPORTED_DTYPES),
    emissions=(Emission("rescaled"),),
    run=run,
    # `downsample`'s relation at a float scale, and for its reason: an area
    # average of pixels is the scene sampled more coarsely and is still pixels,
    # while an average of blocks is a quantity no count threshold is
    # denominated in.
    element=ElementRelation.AGGREGATED,
    mode=Mode.STREAMING,
    guidance=GUIDANCE,
    primary_params=("scale",),
    caption=(
        CaptionPart(label="scale", param="scale", format_spec=".2f"),
        CaptionPart(text="area"),
    ),
    param_stereotypes={"scale": ParamStereotype.SCALAR_RANGE},
)
class RescaleParams(ParamsBase):
    """How far to shrink, as a linear factor of both extents."""

    #: Linear scale for both axes, v1's range. 1.0 is a declared no-op — unlike
    #: `downsample`, whose factor starts at 2 — because a spinbox legitimately
    #: rests at full resolution: that is a setting of this parameter rather than
    #: the absence of the node, which is `crop.WHOLE_FRAME` and
    #: `span`'s unbounded `end` on the two other axes.
    scale: float = Field(default=1.0, ge=0.05, le=1.0)
