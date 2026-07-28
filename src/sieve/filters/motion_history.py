"""A leaky accumulator of activity, with the neighbours holding each other up.

VISION step 3 category C names MEI and MHI; this is them. Bobick & Davis's
Motion History Image ("The recognition of human movement using temporal
templates", PAMI 2001) is the same operator with a linear rather than
exponential decay law, so the filter is named for the literature a user should
go read. `REFINED-VISION.md` **C** writes the continuous form:

    da/dt = -a/tau + D nabla^2 a + s(x, t)

the linear inhomogeneous heat equation with decay and a source: exponential
decay is `-a/tau`, the vision's "blooming touch" is `D nabla^2 a`, and `s` is
the incoming per-block signal. The discrete recursion is its semi-implicit
Euler step,

    a[t] = lambda * C(a[t-1]) + (1 - lambda) * s[t],   lambda = exp(-dt/tau)

with `C` the coupling operator. The same equation is neuromorphic vision's time
surface (Lagorce et al., HOTS), neuroscience's neural field equation (Amari
1977; Wilson-Cowan 1972), and pattern formation's reaction-diffusion; Amari's
result that a lateral-inhibition kernel admits stable localized *bumps* which
cannot form under advecting input above a critical speed is the grooming versus
walking separation with a stability theory attached, and is why the coupling is
worth having at all.

**Decay and coupling are one node, two parameters.** Blurring the output of a
leaky integrator is a different operator: here the coupling sits *inside* the
feedback path and compounds through it, so `a[t]` carries `C` applied `t` times
rather than once. A `motion_history` node followed by a blur node cannot
produce this, and the composition that could would need the two to share state.

**`(1 - lambda)` on the source, so the output stays in the input's units.**
Under a constant input the accumulator settles to exactly that input, which is
what lets a threshold set in `temporal_baseline`'s deviations stay a threshold
in deviations after this node. The MHI convention of saturating to `tau` is the
alternative and was rejected: it puts the output in units of *time*, which is
not a thing the detection chain downstream compares against anything.

**The source is half-wave rectified.** `s[t]` is `max(input, 0)`. The upstream
this filter is built for is `block_signal` (non-negative by construction) or
`temporal_baseline` (signed deviations), and a deviation *below* baseline is
less activity than usual, which is no contribution to a history of activity.
Passing the sign through was the alternative: it makes `dilate` propagate the
*least negative* value outward, which is a spreading of quiet, and it lets an
accumulator cancel its own history against a subsequent lull.

**Two coupling modes, and the difference is the point.**

- `diffuse` is the PDE's own term: one explicit heat step `a + c * nabla^2 a`
  with `c = reach^2 / (2 * tau * fps)`, sub-stepped so the diffusion number
  never exceeds `MAX_DIFFUSION_NUMBER`. It is *conservative* — it spreads the
  peak down while it spreads it out, which fights the threshold downstream. A
  long bout smears into sub-threshold mush.
- `dilate` is grayscale morphological: `max` over the neighbourhood with an
  exponential weight, `kappa = exp(-1 / reach)` per block of separation. It
  *gates* rather than smears — it sustains the support without lowering the
  peak, which is what "the active detections touch the ones around them to keep
  them from the exponential decay" actually describes.

Expect `dilate` to win. Both ship, because which one is right is an empirical
question about footage and `tests/unit/test_motion_history.py` pins the
difference rather than the winner.

**Group delay is declared, not removed.** A causal leaky integrator lags its
event, and mixing it with `core/detection.py`'s `centered` windowed mean means
the two latencies do not cancel and reported onsets are biased late by an
amount nothing wrote down. The zero-phase repair — run the accumulator forward
and backward, the `filtfilt` trick, legitimate offline — needs the whole record
in hand, which is `Mode.WINDOWED` and a kernel protocol that does not exist
(`docs/todo/kernel-protocol-beyond-one-frame.md`). So this filter runs causally
and *declares*: `group_delay` below is the impulse response's centroid in
frames, exactly `lambda / (1 - lambda)`, and `MotionHistoryParams` exposes it in
frames and in seconds. It is declared as a function with a test rather than as a
`FilterSpec` field because no consumer reads it yet and a contract field nothing
consumes is a number, not a declaration — the day the detection chain corrects
onsets is the day it becomes one.

Stateful (the accumulator is the state) and therefore uncacheable, for
`background_ema`'s reason verbatim: nothing that derives a key can tell an
honest `warmup_frames` from a false one, so the exclusion is on the category.
See `docs/findings/2026.07.26-stateful-output-is-not-keyed-by-what-it-is.md`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import numpy as np
from numpy.typing import NDArray
from pydantic import Field

from sieve.backend.dispatch import Backend, stateful_kernel
from sieve.core.filter_base import ArraySpec, CostEstimate, Mode, ParamsBase
from sieve.core.filter_registry import register_filter
from sieve.core.types import ChannelSpec, Frame

#: The shortest persistence. Below about a tenth of a second the accumulator is
#: a frame difference with extra steps at any plausible frame rate.
TAU_SECONDS_MIN = 0.1

#: The longest persistence, and one of the two factors in `MAX_WARMUP_FRAMES`.
#: Ten seconds is already several times the longest grooming bout anyone has
#: asked this to hold, and it is the number that keeps the declared lead-in
#: inside the same order of magnitude as `temporal_baseline`'s.
TAU_SECONDS_MAX = 10.0

#: The highest frame rate a persistence may be denominated against. High-speed
#: insect footage runs here; the bound exists so the warmup bound is finite.
#: `temporal_baseline`'s number, and deliberately the same one.
FPS_MAX = 240.0

#: The furthest coupling may reach, in blocks. A block is 64 source pixels by
#: default, so sixteen of them is a quarter of a 1080p frame — past the point
#: where "the detections around it" is still a statement about one animal.
REACH_BLOCKS_MAX = 16.0

#: How much of the initial (zero) state is allowed to remain before the
#: accumulator counts as settled. `background_ema`'s constant and the same
#: meaning: `warmup_frames` is a settled-to-within-epsilon choice, not a truth.
SETTLED_EPSILON = 0.01

#: The explicit heat scheme's stability limit in 2D: above `1/4` the five-point
#: update oscillates and diverges rather than diffusing. `diffuse` sub-steps to
#: stay at or below it, which is why a large `reach_blocks` costs time rather
#: than producing a checkerboard.
MAX_DIFFUSION_NUMBER = 0.25

#: Float grids only, and for `temporal_baseline`'s reason: this filter belongs
#: on a block grid downstream of extraction, and the coupling is denominated in
#: *blocks*. GRAY on both sides because the coupling is a two-dimensional
#: neighbourhood operation — a channel axis would silently become a third
#: spatial one in the Laplacian's stencil.
SUPPORTED_DTYPES = ("float32", "float64")

FloatArray = NDArray[np.floating[Any]]


def decay_lambda(tau_seconds: float, fps: float) -> float:
    """Weight the previous state keeps across one frame: `exp(-dt/tau)`.

    The one definition. Every other quantity in this module — the settling
    bound, the group delay, the diffusion number — is denominated in it, and a
    second copy is how a filter decays at a rate other than the one it declares.
    """
    return math.exp(-1.0 / (tau_seconds * fps))


def settle_frames(tau_seconds: float, fps: float, epsilon: float = SETTLED_EPSILON) -> int:
    """Frames until less than `epsilon` of the zero initial state remains.

    `ceil(ln epsilon / ln lambda)`, which is `background_ema.settle_frames`'
    arithmetic against a decay written in physical units instead of as a weight.
    Exposed rather than inlined for that filter's reason: it is the definition
    `warmup_frames` is a worst case *of*, and the test that earns it runs the
    kernel and checks the accumulator actually reached its steady state by then.

    An accumulator seeded at zero is a real claim and not a convenience: no
    prior activity is the correct initial condition, unlike a background model
    where zero would mean a black arena. What it costs is that the first outputs
    are biased *low*, and this is how many frames that lasts.
    """
    return math.ceil(math.log(epsilon) / math.log(decay_lambda(tau_seconds, fps)))


def group_delay(tau_seconds: float, fps: float) -> float:
    """The accumulator's lag behind its input, in frames: `lambda / (1 - lambda)`.

    The centroid of the impulse response, which for `h[n] = (1 - lambda) *
    lambda**n` is `sum(n h[n]) / sum(h[n]) = lambda / (1 - lambda)` exactly —
    and is also the one-pole IIR's group delay at DC, so the same number answers
    "where did the energy land" and "what phase did this filter add".

    Fractional on purpose. Rounding it to frames here would make the
    declaration wrong by up to half a frame for the benefit of nobody: the
    consumer that corrects an onset is doing arithmetic on a timeline, not
    indexing an array.

    Exact only when `reach_blocks` is zero. Coupling can add delay away from
    where the activity happened — in `dilate` a block `d` away first hears about
    it `ceil(d / radius)` frames later — so with coupling this is a lower bound
    at the source block and the truth nowhere else. That is the honest statement
    and it is why the declaration names the temporal operator rather than the
    node.
    """
    lam = decay_lambda(tau_seconds, fps)
    return lam / (1.0 - lam)


def diffusion_number(reach_blocks: float, tau_seconds: float, fps: float) -> float:
    """`D * dt` in blocks squared per frame — `diffuse`'s stencil coefficient.

    From the PDE's own parameter. `reach_blocks` is the standard deviation a
    spot of activity spreads to over one persistence time, and a 2D diffusion
    spreads to variance `2 D t`, so `D = reach**2 / (2 tau)` in blocks squared
    per second and this is that times `dt`.
    """
    return reach_blocks * reach_blocks / (2.0 * tau_seconds * fps)


def diffusion_substeps(reach_blocks: float, tau_seconds: float, fps: float) -> int:
    """Explicit sub-steps one frame's diffusion is split into. At least one.

    The alternative was refusing the combination that exceeds
    `MAX_DIFFUSION_NUMBER` — a validator on the params rejecting a large reach
    against a short persistence. Rejected because the constraint couples three
    parameters, two of which (`fps`, and `tau_seconds` on a slider) the user is
    not thinking about while dragging the third, so the refusal would land as a
    control that stops responding. Sub-stepping makes the same configuration
    cost time instead, which is visible in the benchmark readout where a user is
    already looking.
    """
    number = diffusion_number(reach_blocks, tau_seconds, fps)
    return max(1, math.ceil(number / MAX_DIFFUSION_NUMBER))


def coupling_weight(reach_blocks: float) -> float:
    """`dilate`'s attenuation per block of separation: `exp(-1 / reach)`.

    Zero reach is no coupling, and returns 0 so that every weighted neighbour
    contributes nothing and the dilation collapses to the identity.
    """
    if reach_blocks <= 0.0:
        return 0.0
    return math.exp(-1.0 / reach_blocks)


def dilate_radius(reach_blocks: float, tau_seconds: float, fps: float) -> int:
    """`dilate`'s structuring element radius in blocks. At least one.

    A max over a radius-one neighbourhood advances a front at one block per
    frame, which is the grid's speed limit and is usually far *faster* than
    `reach_blocks` per persistence time — the attenuation, not the radius, is
    what makes the reach mean something. The radius only has to grow when the
    requested reach outruns even that: `reach / (tau * fps)` blocks per frame.
    """
    if reach_blocks <= 0.0:
        return 0
    return max(1, math.ceil(reach_blocks / (tau_seconds * fps)))


#: The worst case over the legal parameter range, which is what the spec's bound
#: has to be: a 10 s persistence at 240 fps. No run pays it —
#: `MotionHistoryParams.warmup_frames` refines it to the configured decay.
MAX_WARMUP_FRAMES = settle_frames(TAU_SECONDS_MAX, FPS_MAX)


class Couple(StrEnum):
    """How a block's activity reaches the blocks around it."""

    #: Grayscale morphological dilation with an exponential weight. Gates: it
    #: sustains a neighbour's support without lowering this block's peak.
    DILATE = "dilate"
    #: One explicit heat step. Conservative: it spreads the peak down as it
    #: spreads it out, which is the PDE's literal term and fights a threshold.
    DIFFUSE = "diffuse"


@register_filter(
    filter_id="motion_history",
    version="1.0.0",
    summary="Leaky accumulator of per-block activity, with neighbourhood coupling.",
    accepts=ArraySpec(dtypes=SUPPORTED_DTYPES, channels=(ChannelSpec.GRAY,)),
    emits=ArraySpec(dtypes=("float32",), channels=(ChannelSpec.GRAY,)),
    cost=CostEstimate(
        # Measured on a 34x60 float32 grid (`block_signal`'s output at the
        # default block on 1080p): 0.035 ms/frame at the defaults, which on a
        # 0.00204 MP grid is the number below, against 0.026 for `diffuse` at
        # the same reach. `dilate` at radius one is eight weighted maxima over
        # the grid and `diffuse` at one sub-step is a five-point stencil, so the
        # two tiers are within a third of each other and this declaration takes
        # the slower, which is also the default.
        #
        # It is not the worst case and cannot be: `diffuse` sub-steps, so a
        # 16-block reach against a 0.1 s persistence at 30 fps is 171 steps and
        # measures 3.1 ms/frame — 88x this. A static number cannot branch on a
        # parameter; the honest place for that is the guidance's cost section.
        seconds_per_megapixel=0.017,
        # The accumulator, the rectified source, and the coupling's output,
        # against a float32 input frame — plus the transient the weighted max
        # allocates per offset, which is one more grid.
        peak_bytes_per_input_byte=5.0,
    ),
    mode=Mode.STREAMING,
    # The bound, not what a run pays. See MAX_WARMUP_FRAMES.
    warmup_frames=MAX_WARMUP_FRAMES,
    stateful=True,
    primary_params=("tau_seconds", "reach_blocks", "couple"),
)
class MotionHistoryParams(ParamsBase):
    """How long activity persists, how far it reaches, and by which operator."""

    #: The persistence time. The primary parameter: it is how long after an
    #: animal stops moving the accumulator still says something happened, and
    #: therefore how long a bout has to pause before it reads as two bouts.
    tau_seconds: float = Field(default=1.0, ge=TAU_SECONDS_MIN, le=TAU_SECONDS_MAX)
    #: How far activity is carried, in blocks. Zero is a pure leaky integrator
    #: per block, which is the plain MHI and a legitimate thing to want. The two
    #: modes agree on the *scale* and not on the profile: `dilate` attenuates by
    #: `1/e` per `reach_blocks` blocks of separation, `diffuse` spreads to a
    #: standard deviation of `reach_blocks` blocks over one `tau_seconds`.
    reach_blocks: float = Field(default=1.0, ge=0.0, le=REACH_BLOCKS_MAX)
    couple: Couple = Couple.DILATE
    #: Source frame rate, used only to convert `tau_seconds` and `reach_blocks`
    #: into per-frame quantities. The tab writes it from the video metadata,
    #: exactly as it does for `block_signal.fps` and `temporal_baseline.fps`: a
    #: kernel is pure and cannot ask the graph what the container's rate was.
    fps: float = Field(default=30.0, gt=0.0, le=FPS_MAX)

    def warmup_frames(self) -> int:
        """`settle_frames(tau_seconds, fps)` — the bound, refined to this decay.

        Equal to the spec's bound only at the corner where both factors are at
        their maxima, and strictly below it everywhere else, which is the
        direction `node_warmup_frames` permits. `reach_blocks` and `couple` do
        not enter: coupling redistributes the accumulator in space and does not
        change the rate at which it forgets.
        """
        return settle_frames(self.tau_seconds, self.fps)

    def group_delay_frames(self) -> float:
        """This configuration's lag behind its input, in frames. See `group_delay`."""
        return group_delay(self.tau_seconds, self.fps)

    def group_delay_seconds(self) -> float:
        """This configuration's lag behind its input, in seconds.

        The unit a consumer correcting an onset actually wants, since the thing
        it is aligning against — another data stream, a hand-scored ethogram —
        is not denominated in this video's frames.
        """
        return self.group_delay_frames() / self.fps


@dataclass(slots=True)
class MotionHistoryState:
    """One run's accumulator. Made by `KernelBinding.start`.

    `None` until the first frame, for `BackgroundState`'s reason: nothing tells
    a state factory what shape the footage is. Unlike a background model the
    seed is not the first frame but zero — no prior activity is the correct
    initial condition — so the first frame only supplies the geometry.
    """

    accumulator: FloatArray | None = None

    def for_frame(self, data: FloatArray, index: int) -> FloatArray:
        """This run's accumulator, allocated to `data`'s shape on the first frame.

        Raises:
            ValueError: if the shape changed since it was allocated. The
                executor crops every root to a fixed ROI, so a graph cannot
                cause this, and a silent reallocation would hide whatever did —
                a resized proxy, a second source spliced into one run — behind
                an accumulator that quietly restarted its warmup with nobody
                told.
        """
        if self.accumulator is None:
            if data.ndim != 2:
                raise ValueError(
                    f"motion_history couples over a block neighbourhood and was handed a "
                    f"{data.ndim}-dimensional frame at index {index}; its input is a GRAY grid"
                )
            self.accumulator = np.zeros(data.shape, np.float32)
        elif self.accumulator.shape != data.shape:
            raise ValueError(
                f"motion_history was sized on a {self.accumulator.shape} frame and handed a "
                f"{data.shape} one at index {index}; one run is one geometry"
            )
        return self.accumulator


@stateful_kernel(MotionHistoryParams, Backend.CPU, state=MotionHistoryState)
def motion_history_cpu(
    frame: Frame, params: MotionHistoryParams, state: MotionHistoryState
) -> Frame:
    """Couple the accumulator, decay it, and mix in this frame's activity.

    In that order, which is the recursion's order and not an implementation
    detail: the coupling applies to what was already there, so the frame just
    admitted has not yet been spread. Reversing it would let a single frame's
    activity appear a block away in the same frame it happened, which is a
    spatial smear masquerading as persistence.

    Raises:
        ValueError: if the frame is not a two-dimensional grid, or if its shape
            changes mid-run. See `MotionHistoryState.for_frame`.
    """
    data = np.asarray(frame.data, np.float32)
    accumulator = state.for_frame(data, frame.index)

    coupled = _couple(accumulator, params)
    lam = np.float32(decay_lambda(params.tau_seconds, params.fps))
    np.multiply(coupled, lam, out=accumulator)
    # The source, half-wave rectified: a deviation below baseline is not
    # negative activity, it is no activity. See the module docstring.
    accumulator += (np.float32(1.0) - lam) * np.maximum(data, np.float32(0.0))

    return Frame(data=accumulator.copy(), index=frame.index, channels=ChannelSpec.GRAY)


def _couple(accumulator: FloatArray, params: MotionHistoryParams) -> FloatArray:
    """`C(a)`: the previous state with the neighbours holding it up.

    Returns the accumulator itself when there is no coupling to apply, which the
    caller may write into — the multiply above is `out=accumulator`, and an
    uncoupled run is then genuinely allocation-free per frame.
    """
    if params.reach_blocks <= 0.0:
        return accumulator
    if params.couple is Couple.DIFFUSE:
        return _diffuse(accumulator, params)
    return _dilate(
        accumulator,
        coupling_weight(params.reach_blocks),
        dilate_radius(params.reach_blocks, params.tau_seconds, params.fps),
    )


def _diffuse(accumulator: FloatArray, params: MotionHistoryParams) -> FloatArray:
    """One frame's worth of `D nabla^2 a`, sub-stepped to stay stable.

    Five-point stencil with a reflecting (Neumann) boundary, so the arena wall
    neither absorbs activity nor invents any: `mode="edge"` makes the outward
    gradient zero, which is what "nothing flows through the wall" is. A
    zero-padded stencil would leak activity out of every edge block, and the
    edge blocks are where an animal walking the perimeter lives.
    """
    steps = diffusion_substeps(params.reach_blocks, params.tau_seconds, params.fps)
    c = np.float32(diffusion_number(params.reach_blocks, params.tau_seconds, params.fps) / steps)
    field = accumulator.astype(np.float32, copy=True)
    for _ in range(steps):
        padded = np.pad(field, ((1, 1), (1, 1)), mode="edge")
        neighbours = padded[:-2, 1:-1] + padded[2:, 1:-1] + padded[1:-1, :-2] + padded[1:-1, 2:]
        field += c * (neighbours - 4.0 * field)
    return field


def _dilate(accumulator: FloatArray, kappa: float, radius: int) -> FloatArray:
    """Grayscale dilation by a non-flat element: `max` of `kappa**dist * a`.

    Sliced rather than padded. The neutral element of a max over a signed field
    is negative infinity, and padding with it would put infinities through the
    multiply; padding with the edge value would replicate an edge block's
    activity outward, inventing support against the arena wall. Restricting each
    offset to its overlap does neither, and the centre offset — weight one, the
    whole grid — guarantees every cell has at least one contributor.
    """
    out = accumulator.copy()
    rows, cols = accumulator.shape
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dy == 0 and dx == 0:
                continue
            weight = np.float32(kappa ** math.hypot(dy, dx))
            src = accumulator[max(0, dy) : rows - max(0, -dy), max(0, dx) : cols - max(0, -dx)]
            dst = out[max(0, -dy) : rows - max(0, dy), max(0, -dx) : cols - max(0, dx)]
            np.maximum(dst, weight * src, out=dst)
    return out
