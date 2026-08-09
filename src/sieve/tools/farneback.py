"""Dense per-pixel optical flow speed, by Farneback polynomial expansion.

`block_signal`'s `flow_speed` answers the same question — how fast did this move
— on the evidence of a first-order Lucas-Kanade solve over one Gaussian window,
and reports it per block. This is the other estimator: Farneback fits a local
quadratic to each neighbourhood and solves for the displacement that carries one
polynomial onto the next, over an image pyramid, so the displacement it can
express is not bounded by the window's linearization. The practical difference is
the one the pyramid buys — an animal crossing more of the frame per frame than
the window is wide reads as fast motion here and as noise there — and the cost is
a dense solve per level rather than five blurred products.

The literature is Farneback's *Two-Frame Motion Estimation Based on Polynomial
Expansion* (SCIA 2003); the implementation is `cv2.calcOpticalFlowFarneback`,
which is that paper's method and not an approximation of it.

**Per pixel, and therefore not a substitute for `block_signal`.** What leaves the
node is one speed per input pixel — `ElementRelation.PRESERVED` — so a grid still
comes from a downstream `downsample`, and a count threshold is still denominated
against whatever redefines the element. That is what makes the two flow tools
composable rather than rival: this one measures, the grid is somebody else's
declaration.

**Speed leaves the node; direction does not.** The flow field is `(u, v)` and
throwing away the angle is a real loss, but every temporal tool downstream of
here averages — `temporal_baseline` over a window, `motion_history` over a decay,
`detect` over a band — and a circular quantity averaged linearly gives a
direction nobody moved in. `block_signal._flow_agreement` is the shape a honest
direction product has to take (a resultant length, reduced circularly, over an
aggregate), and it needs an aggregation this tool deliberately does not do. So
one emission, until something exists that can consume an angle as an angle.

**`window` is two ways of weighting one neighbourhood, not two products.**
`cv2.OPTFLOW_FARNEBACK_GAUSSIAN` weights the expansion window by a Gaussian
instead of a box; it is more accurate and slower at equal `winsize`, and OpenCV's
own note is that a larger `winsize` is usually wanted with it. Both compute the
same displacement field, which is `downsample`'s area-vs-stride test and gives
the same answer: one emission (`adr/declared-means-verified.md`).

Stateful — the previous frame is the state — with `warmup_frames = 1` and a
`BOUNDED` warmup, verbatim `block_signal`'s reasoning: two frames determine every
value, nothing older reaches the estimate, so the output is keyable and the
executor re-settles the one frame of state when a served range leaves it behind
(`adr/cache-admission-is-bounded-warmup.md`).

**uint8 in, by declaration rather than by conversion.** OpenCV's Farneback takes
8-bit single-channel, and a tool that quietly rescaled a float input would be
choosing the quantization the estimate is made at — which is a decision about the
measurement, hidden inside a cast. Declaring the dtype instead makes a float
upstream a graph the DAG refuses to build, with the node named
(`adr/correctness-is-the-default.md`), which is the failure a user can act on.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, cast

import cv2
import numpy as np
from numpy.typing import NDArray
from pydantic import Field

from sieve.core.tool_base import (
    ArraySpec,
    CaptionPart,
    ElementRelation,
    Emission,
    Mode,
    ParamsBase,
    ParamStereotype,
    WarmupKind,
)
from sieve.core.tool_registry import register_tool
from sieve.core.types import ChannelSpec, Frame, FrameCount, FrameSpan

#: OpenCV's Farneback takes 8-bit single-channel. The channel conversion is this
#: module's; the depth is not (see the docstring's last paragraph).
SUPPORTED_DTYPES = ("uint8",)

#: Past 8 the top pyramid level is a handful of pixels wide and the coarse
#: displacement it proposes is not a measurement of anything.
LEVELS_MAX = 8

#: The expansion neighbourhood, in working pixels. Bounded above where a window
#: is a large fraction of any frame worth running this on, and below at 3, which
#: is the smallest neighbourhood a quadratic can be fitted to at all.
WINSIZE_MIN = 3
WINSIZE_MAX = 101

#: OpenCV's own pairing: `poly_n=5` wants `poly_sigma=1.1`, `poly_n=7` wants
#: `1.5`. The two are free parameters here rather than one, because a value
#: between them is legal and occasionally what tuning lands on.
POLY_N_MIN = 3
POLY_N_MAX = 9

FloatArray = NDArray[np.floating[Any]]

#: What this tool is for, in the words of somebody tuning it.
GUIDANCE = """\
Measures how fast every pixel moved since the previous frame, in pixels per
second. Where `block_signal`'s flow speed reads one Gaussian window and reports
per block, this tracks motion across an image pyramid, so it still measures an
animal that crosses more of the frame per frame than a window is wide. Reach for
it when things move fast relative to the frame rate, or when the speed itself is
the number being reported rather than a proxy for activity.

`winsize` is the parameter to spend time on. A larger window is more robust to
noise and to a flat patch of arena with nothing to track, and it smears the flow
of a small animal into the still floor around it; a smaller one localizes and
gets noisier. Start near the size of the thing you are following.

`levels` is how far up the pyramid the search goes, and it is what buys the large
displacements. One level is a single-scale solve. Each further level doubles the
motion that can be resolved and costs a pass. If fast motion reads as nothing,
this is the knob before `winsize`.

`window` picks how the expansion neighbourhood is weighted. Gaussian is more
accurate and slower than box at the same `winsize`, and it usually wants a larger
one.

It emits speed and not direction, on purpose: everything downstream averages, and
an average of angles is a direction nothing moved in.

Feed it a stable picture, and feed it the frames it is denominated against — the
`fps` parameter is what turns pixels per frame into pixels per second, so a node
reading a decimated stream reports speeds off by the decimation."""


class Window(StrEnum):
    """How the polynomial expansion weights its neighbourhood."""

    #: Uniform weighting over `winsize`. OpenCV's default, and the faster one.
    BOX = "box"
    #: Gaussian of `winsize` standard deviations' extent — more accurate at
    #: equal `winsize`, and usually wanting a larger one.
    GAUSSIAN = "gaussian"


@dataclass(slots=True)
class FarnebackState:
    """The previous gray frame. `None` until the first frame of a run.

    `block_signal`'s state and, like it, minted per run by the executor rather
    than closed over, so two concurrent previews of one node cannot hand each
    other a predecessor (`adr/no-kernel-apparatus.md`).
    """

    prev: NDArray[np.uint8] | None = None


def run(params: FarnebackParams, window: FrameSpan, state: FarnebackState, /) -> Frame:
    """Estimate the displacement from the previous frame, then remember this one.

    The first frame of a run emits zeros — there is no displacement across a
    boundary with nothing on the other side — and `warmup_frames=1` is what keeps
    a requested span from starting on it.

    Raises:
        ValueError: if the frame's shape changes mid-run. One run is one
            geometry: the state is the previous frame, and there is no
            correspondence between two rasters of different sizes to estimate a
            displacement across.
    """
    frame = window.target
    gray = _to_gray(frame)

    prev = state.prev
    state.prev = gray
    if prev is None:
        return Frame(
            data=np.zeros(gray.shape, np.float32), index=frame.index, channels=ChannelSpec.GRAY
        )
    if prev.shape != gray.shape:
        raise ValueError(
            f"farneback saw a {prev.shape} frame and then a {gray.shape} one at "
            f"index {frame.index}; one run is one geometry"
        )

    flow = cast(
        NDArray[np.float32],
        cv2.calcOpticalFlowFarneback(
            prev,
            gray,
            None,  # type: ignore[arg-type]
            params.pyr_scale,
            params.levels,
            params.winsize,
            params.iterations,
            params.poly_n,
            params.poly_sigma,
            cv2.OPTFLOW_FARNEBACK_GAUSSIAN if params.window is Window.GAUSSIAN else 0,
        ),
    )
    speed = (np.hypot(flow[..., 0], flow[..., 1]) * params.fps).astype(np.float32)
    return Frame(data=speed, index=frame.index, channels=ChannelSpec.GRAY)


@register_tool(
    tool_id="farneback",
    version="1.0.0",
    summary="Dense per-pixel optical flow speed by Farneback polynomial expansion.",
    accepts=ArraySpec(dtypes=SUPPORTED_DTYPES),
    emits=ArraySpec(dtypes=("float32",), channels=(ChannelSpec.GRAY,)),
    # One product: `window` weights the same estimate two ways, which is
    # `downsample`'s area-vs-stride and not `block_signal`'s four signals.
    emissions=(Emission("speed"),),
    run=run,
    # One speed per input pixel. The grid, if a graph wants one, is downstream.
    element=ElementRelation.PRESERVED,
    mode=Mode.STREAMING,
    settling_epsilon=0.0,
    # `block_signal`'s kind for its reason: the estimate reaches exactly one
    # frame back, so two frames decide every value this emits.
    warmup_kind=WarmupKind.BOUNDED,
    stateful=True,
    state_factory=FarnebackState,
    guidance=GUIDANCE,
    primary_params=("winsize", "levels", "window"),
    caption=(
        CaptionPart(label="win", param="winsize"),
        CaptionPart(label="levels", param="levels"),
        CaptionPart(param="window"),
    ),
    param_value_labels={
        "window": {
            Window.BOX.value: "uniform (faster)",
            Window.GAUSSIAN.value: "gaussian (more accurate)",
        }
    },
    param_stereotypes={
        "pyr_scale": ParamStereotype.SCALAR_RANGE,
        "levels": ParamStereotype.SCALAR_RANGE,
        "winsize": ParamStereotype.SCALAR_RANGE,
        "iterations": ParamStereotype.SCALAR_RANGE,
        "poly_n": ParamStereotype.SCALAR_RANGE,
        "poly_sigma": ParamStereotype.SCALAR_RANGE,
        "window": ParamStereotype.ENUM,
        "fps": ParamStereotype.SCALAR_RANGE,
    },
)
class FarnebackParams(ParamsBase):
    """The pyramid, the expansion neighbourhood, and the time base."""

    #: Ratio between successive pyramid levels. Strictly below 1 — a scale of 1
    #: would build a pyramid of identical images, which OpenCV rejects and which
    #: is `levels=1` written expensively.
    pyr_scale: float = Field(default=0.5, gt=0.0, lt=1.0)
    #: Pyramid levels including the original. Each further level roughly doubles
    #: the displacement that can be resolved, at a pass's cost.
    levels: int = Field(default=3, ge=1, le=LEVELS_MAX)
    #: The expansion neighbourhood, in working pixels.
    winsize: int = Field(default=15, ge=WINSIZE_MIN, le=WINSIZE_MAX)
    #: Refinement passes per pyramid level.
    iterations: int = Field(default=3, ge=1, le=10)
    #: Pixel neighbourhood the quadratic is fitted over. OpenCV pairs 5 with a
    #: `poly_sigma` of 1.1 and 7 with 1.5.
    poly_n: int = Field(default=5, ge=POLY_N_MIN, le=POLY_N_MAX)
    #: Standard deviation of the smoothing the derivatives of that fit are taken
    #: through.
    poly_sigma: float = Field(default=1.1, gt=0.0, le=5.0)
    window: Window = Window.BOX
    #: Source frame rate, used only to express the speed in px/s rather than
    #: px/frame. Explicit for `block_signal.fps`'s reason: a `run` is pure and
    #: cannot ask the graph what the container's rate was, so whatever configures
    #: the node writes it from a value it already owns.
    fps: float = Field(default=30.0, gt=0.0)

    @classmethod
    def max_warmup_frames(cls) -> FrameCount:
        """One previous frame, at every setting: the estimate is two-frame."""
        return FrameCount(1)


def _to_gray(frame: Frame) -> NDArray[np.uint8]:
    """The frame as 8-bit gray, whatever channel layout came in.

    `block_signal._to_gray`'s conversion at the depth Farneback requires. The
    dtype needs no branch — `accepts` admits uint8 and nothing else — so this is
    only the channel reduction, on the same BT.601 weights every other tool in
    this package projects colour with.
    """
    data = np.asarray(frame.data)
    if frame.channels is ChannelSpec.GRAY:
        return cast(NDArray[np.uint8], np.ascontiguousarray(data, np.uint8))
    code = cv2.COLOR_BGR2GRAY if frame.channels is ChannelSpec.BGR else cv2.COLOR_RGB2GRAY
    return cast(NDArray[np.uint8], cv2.cvtColor(data, code))
