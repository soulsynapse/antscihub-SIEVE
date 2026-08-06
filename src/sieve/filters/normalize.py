"""Per-frame contrast normalization: `off` or `zscore`.

v1's normalize (`Preprocessor._normalize`), ported with its fused-affine
implementation: the z-score is affine, so `(g - mean) / std * 32 + 128` is
`g * a + b` with `a = 32 / std` — one multiply and one in-place add instead
of four full-frame temporaries, measured 2.3-3x by v1. Statistics come from
`cv2.meanStdDev`, which accumulates in float64.

**Where the statistics come from on a color frame.** v1 normalized *after*
grayscale conversion; in this graph the extraction filter converts to gray
*after* this node. The gray projection is a fixed convex combination of the
channels, and an affine map commutes with it: `gray(a*x + b) = a*gray(x) + b`.
So computing `a` and `b` from the frame's gray projection and applying them
to every channel makes the downstream gray series *exactly* v1's normalized
gray — same numbers, different point in the chain. Computing the statistics
over all channels pooled would instead shift every band-power value by the
ratio of pooled to luma std, and the parity comparison (plan item 9) would
be comparing detectors tuned against different signals. On GRAY input the
projection is the identity and this is v1 verbatim.

`clahe` is deliberately absent — see the guidance file.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

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
from sieve.core.types import ChannelSpec, Frame, WorkUnits

#: Target first moments of the normalized frame, from v1: mean 128 and sd 32
#: place the signal comfortably inside uint8 range with ~4 sigma of headroom
#: either side, so a downstream display or uint8 narrowing clips almost
#: nothing.
TARGET_MEAN = 128.0
TARGET_SD = 32.0

#: Below this standard deviation a frame is treated as constant and only
#: centered, never divided. v1's cutoff, kept exactly.
MIN_STD = 1e-6

#: Layouts and dtypes the statistics pass handles. Float64 is absent from the
#: *emit* side story but present here because `zscore` widens everything to
#: float32 anyway and `off` passes anything through.
SUPPORTED_DTYPES = ("uint8", "uint16", "float32", "float64")


class NormalizeMode(StrEnum):
    """Whether to touch the pixels at all."""

    OFF = "off"
    ZSCORE = "zscore"


@register_filter(
    filter_id="normalize",
    version="1.0.0",
    summary="Per-frame contrast normalization to a fixed mean and spread.",
    accepts=ArraySpec(dtypes=SUPPORTED_DTYPES),
    # `off` emits the input dtype unchanged; `zscore` emits float32. The
    # declared set is the union, because a declaration holds for every
    # parameter setting. Channels are preserved either way.
    emits=ArraySpec(dtypes=SUPPORTED_DTYPES),
    # An affine map applied elementwise: whatever one value described going in,
    # it describes coming out.
    element=ElementRelation.PRESERVED,
    cost=CostEstimate(
        # One gray statistics pass plus one fused multiply-add over the frame.
        work_per_megapixel=WorkUnits(3.0),
        # Input, a float32 copy, and the gray projection for stats.
        peak_bytes_per_input_byte=6.0,
    ),
    authoring_group=AuthoringGroup.SPATIAL_PREP,
    mode=Mode.STREAMING,
    primary_params=("mode",),
    caption=(CaptionPart(param="mode"),),
)
class NormalizeParams(ParamsBase):
    """Which normalization, if any."""

    mode: NormalizeMode = NormalizeMode.OFF


@kernel(NormalizeParams, Backend.CPU)
def normalize_cpu(frame: Frame, params: NormalizeParams) -> Frame:
    """Normalize per-frame global statistics to mean 128, sd 32.

    `off` hands the frame through untouched — the same zero-cost no-op path
    as `rescale` at 1.0. `zscore` emits float32 whatever came in: the affine
    lands values on a continuous scale and narrowing back to an integer dtype
    would quantize exactly the contrast the step exists to standardize.

    A constant frame (std below `MIN_STD`) is centered but never divided —
    v1's guard, kept because a black lead-in frame must not become a frame of
    NaN that poisons every block series downstream.
    """
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


def _gray_stats(data: NDArray[np.float32], channels: ChannelSpec) -> tuple[float, float]:
    """Mean and std of the frame's gray projection (see module docstring).

    The projection uses the same BT.601 weights `cv2.cvtColor` applies, so
    these statistics are computed on exactly the series the extraction filter
    will produce downstream.
    """
    if channels is ChannelSpec.GRAY:
        gray = data
    else:
        code = cv2.COLOR_BGR2GRAY if channels is ChannelSpec.BGR else cv2.COLOR_RGB2GRAY
        gray = cv2.cvtColor(data, code)
    m: Any
    s: Any
    m, s = cv2.meanStdDev(gray)
    return float(m[0, 0]), float(s[0, 0])
