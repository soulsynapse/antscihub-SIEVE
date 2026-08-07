"""Per-frame contrast normalization: `off` or `zscore`.

v1's normalize (`Preprocessor._normalize`), ported with its fused-affine
implementation rather than its arithmetic restated: the z-score is affine, so
`(g - mean) / std * 32 + 128` is `g * a + b` with `a = 32 / std` — one multiply
and one in-place add instead of four full-frame temporaries, measured 2.3-3x by
v1. Statistics come from `cv2.meanStdDev`, which accumulates in float64.

**Where the statistics come from on a color frame.** v1 normalized *after*
grayscale conversion; in this graph whatever converts to gray does so
downstream of this node. The gray projection is a fixed convex combination of
the channels, and an affine map commutes with it: `gray(a*x + b) = a*gray(x) +
b`. So computing `a` and `b` from the frame's gray projection and applying them
to every channel makes the downstream gray series *exactly* v1's normalized
gray — same numbers, at a different point in the chain. Pooling the channels
for the statistics instead would shift every downstream band-power value by the
ratio of pooled to luma std, and the parity comparison would then be between
detectors tuned against different signals. On GRAY input the projection is the
identity and this is v1 verbatim.

`clahe` is deliberately absent: v2 left it out and nothing since has asked for
it, and a second normalization mode is a decision about what the tuning loop
exposes rather than a line of arithmetic.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

from sieve.core.tool_base import (
    ArraySpec,
    CaptionPart,
    ElementRelation,
    Mode,
    ParamsBase,
    ParamStereotype,
)
from sieve.core.tool_registry import register_tool
from sieve.core.types import ChannelSpec, Frame, FrameSpan

#: Target first moments of the normalized frame, from v1: mean 128 and sd 32
#: place the signal comfortably inside uint8 range with ~4 sigma of headroom
#: either side, so a downstream display or uint8 narrowing loses almost nothing
#: at either end.
TARGET_MEAN = 128.0
TARGET_SD = 32.0

#: Below this standard deviation a frame is treated as constant and only
#: centered, never divided. v1's cutoff, kept exactly.
MIN_STD = 1e-6

#: Layouts and dtypes the statistics pass handles. Float64 is here even though
#: `zscore` widens everything to float32 anyway, because `off` passes whatever
#: it is handed straight through and the declaration covers both modes.
SUPPORTED_DTYPES = ("uint8", "uint16", "float32", "float64")


class NormalizeMode(StrEnum):
    """Whether to touch the pixels at all."""

    OFF = "off"
    ZSCORE = "zscore"


def _gray_stats(data: NDArray[np.float32], channels: ChannelSpec) -> tuple[float, float]:
    """Mean and std of the frame's gray projection (see the module docstring).

    The projection uses the same BT.601 weights `cv2.cvtColor` applies, so these
    statistics are computed on exactly the series a downstream gray conversion
    will produce.
    """
    if channels is ChannelSpec.GRAY:
        gray = data
    else:
        code = cv2.COLOR_BGR2GRAY if channels is ChannelSpec.BGR else cv2.COLOR_RGB2GRAY
        gray = cv2.cvtColor(data, code)
    mean: Any
    std: Any
    mean, std = cv2.meanStdDev(gray)
    return float(mean[0, 0]), float(std[0, 0])


def run(params: NormalizeParams, window: FrameSpan, state: None, /) -> Frame:
    """Normalize per-frame global statistics to mean 128, sd 32.

    `off` hands the frame through untouched, which is `rescale` at 1.0 on the
    value axis and costs what the absent node would. `zscore` emits float32
    whatever came in: the affine lands values on a continuous scale, and
    narrowing back to an integer dtype would quantize away exactly the contrast
    the step exists to standardize.

    A constant frame (std below `MIN_STD`) is centered but never divided — v1's
    guard, kept because a black lead-in frame must not become a frame of NaN
    that poisons every series downstream of it.
    """
    del state
    frame = window.target
    if params.mode is NormalizeMode.OFF:
        return frame
    data = np.asarray(frame.data, np.float32)
    mean, std = _gray_stats(data, frame.channels)
    if std < MIN_STD:
        out = np.subtract(data, np.float32(mean), dtype=np.float32)
    else:
        scale = TARGET_SD / std
        out = np.multiply(data, np.float32(scale), dtype=np.float32)
        np.add(out, np.float32(TARGET_MEAN - mean * scale), out=out)
    return Frame(data=out, index=frame.index, channels=frame.channels)


@register_tool(
    tool_id="normalize",
    version="1.0.0",
    summary="Per-frame contrast normalization to a fixed mean and spread.",
    accepts=ArraySpec(dtypes=SUPPORTED_DTYPES),
    # `off` emits the input dtype unchanged and `zscore` emits float32, so the
    # declared set is the union — a declaration holds for every setting of every
    # parameter. Channels are preserved either way.
    emits=ArraySpec(dtypes=SUPPORTED_DTYPES),
    run=run,
    # An affine map applied elementwise: whatever one value described going in,
    # it describes coming out.
    element=ElementRelation.PRESERVED,
    mode=Mode.STREAMING,
    primary_params=("mode",),
    caption=(CaptionPart(param="mode"),),
    # A choice from a fixed set, and the values read as themselves — "off" and
    # "zscore" are what a user picks between, so there is nothing for
    # `param_value_labels` to translate.
    param_stereotypes={"mode": ParamStereotype.ENUM},
)
class NormalizeParams(ParamsBase):
    """Which normalization, if any."""

    #: Defaults to `OFF`, which is this tool's identity value in `crop`'s sense:
    #: the node is present in the graph and contributes nothing to the pixels,
    #: so turning normalization on is a parameter change rather than an edit to
    #: the graph's shape.
    mode: NormalizeMode = NormalizeMode.OFF
