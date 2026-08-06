"""An exponential moving-average background model, and the difference from it.

The second filter, and the first one that has to remember anything. `downsample`
is stateless, rate-preserving, single-upstream and pure arithmetic — which made
it the right first filter and means it exercises none of the contract's
temporal half. This does: it is VISION step 3's category C, VISION step 1 names
background subtraction first, and it is the only thing in the repo that gives
`warmup_frames` a consumer.

The model is `bg <- bg + alpha * (frame - bg)`, seeded with the first frame it
sees. `alpha` is the weight of the newest frame: small means a background that
takes a long time to accept a change and therefore keeps a stopped ant in the
foreground; large means one that absorbs the ant and leaves only its motion.
There is no correct value — that is a question about how long the animals in
this footage hold still, which is why it is the primary parameter and not a
constant.

**Why `warmup_frames` is 90 and what epsilon it is settled to.** An EMA's true
warmup is infinite: the seed frame's weight after `n` updates is `(1 - alpha)^n`,
which is never zero. What the declaration takes instead is the number of frames
after which the seed retains less than **1% of the model's weight**:
`ceil(ln 0.01 / ln (1 - alpha))`. The spec's 90 is that at `alpha = 0.05`, the
lower bound of the legal range — the worst case, which is what a bound printed
without a configuration in hand has to be. `BackgroundEmaParams.warmup_frames`
refines it to the configured `alpha`, so `alpha = 0.5` asks for the 7 frames it
actually needs rather than 90.

*That refinement did not exist when this filter was written, and the 83 frames
it saves at `alpha = 0.5` were documented here as the correct price of a
declaration true for every parameter setting. It stopped being the correct price
when `temporal_baseline` arrived with the same problem an order of magnitude
larger — a bound of 7200 frames against a typical need of 150 — and
`core/filter_base.py` grew the params-derived half. The reasoning the old
paragraph rested on still holds and is why the refinement may only shrink the
bound: a lead-in that was right on average would be wrong exactly when `alpha`
was small, which is the setting a user reaches for when the animals are still,
which is when the background matters most.*

A 90-frame lead-in is also the first one large enough that `lead_in_shortfall`
means something: a clip starting less than 90 frames into the source cannot be
warmed, `sieve run` says so, and before this filter existed no graph in this
repo could produce that warning.

**Uncacheable, and not because it is unreproducible.** The spec declares
`stateful=True`, so `cache_key.is_cacheable` is False and `dag.py` derives no key
for the node. This filter would in fact be safe to cache — the 90 above is the
claim that its output stops depending on where the run started, and that claim
is true and tested. What cannot be cached is the *category*: nothing that
derives a key can tell this declaration from a false one, so the exclusion is on
statefulness rather than on a number. See
`docs/findings/2026.07.26-stateful-output-is-not-keyed-by-what-it-is.md`.
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
from sieve.core.types import Frame, FrameCount, FrameIndex, WorkUnits

#: What the accumulator can hold without losing the input's range. Same set as
#: `downsample`'s, so the two chain in either order — the ordinary graph is a
#: downsample in front of this one, because the model is the largest thing a
#: run holds and it is float32 whatever the input was.
SUPPORTED_DTYPES = ("uint8", "uint16", "float32", "float64")

#: The smallest weight the newest frame may carry. Sets `warmup_frames` below,
#: and is a bound rather than a preference: an `alpha` of 0.01 is a legitimate
#: thing to want and would need 459 frames of lead-in, which is a different
#: filter version's decision rather than a slider position.
MIN_ALPHA = 0.05

#: How much of the seed frame's weight is allowed to remain before the model
#: counts as settled. Stated as a constant because the module docstring's
#: arithmetic is unreadable without a name for it and because a reader checking
#: the 90 below should not have to find the number in prose.
SETTLED_EPSILON = 0.01


def settle_frames(alpha: float, epsilon: float = SETTLED_EPSILON) -> int:
    """Frames until the seed frame holds less than `epsilon` of the model.

    Exposed rather than inlined because it is the definition `warmup_frames` is
    a worst case *of*, and a test that recomputed it from the same formula would
    prove only that the formula equals itself. What the test does instead is run
    the kernel and check the model actually converged by then — for which it
    needs this function to know where "then" is at an `alpha` other than the
    bound.

    `alpha = 1.0` is the legal upper bound and is the case the closed form
    cannot express: the seed's weight is exactly zero after one frame, and
    `log(1 - alpha)` is `log(0)`. Answering 1 rather than raising, because one
    frame is the true answer and not a special case — the model *is* the newest
    frame, so it has settled the moment it has seen one.
    """
    if alpha >= 1.0:
        return 1
    return math.ceil(math.log(epsilon) / math.log(1.0 - alpha))


class Emit(StrEnum):
    """Which of the two things this filter has computed leaves the node."""

    #: `|frame - background|`. What a detector downstream wants.
    FOREGROUND = "foreground"
    #: The model itself. What a user tuning `alpha` needs to look at, since the
    #: foreground only shows the model indirectly and a background that has
    #: absorbed the animals looks the same as one that never saw them.
    BACKGROUND = "background"


@register_filter(
    filter_id="background_ema",
    version="1.0.0",
    summary="Exponential moving-average background model, and the difference from it.",
    accepts=ArraySpec(dtypes=SUPPORTED_DTYPES),
    # Channels unstated on both sides: the model is per channel and the layout
    # carries through untouched, so constraining either side would reject frames
    # this handles.
    emits=ArraySpec(dtypes=SUPPORTED_DTYPES),
    # The model is per element and so is the difference from it; the geometry
    # is untouched, exactly as the unstated channels above say.
    element=ElementRelation.PRESERVED,
    cost=CostEstimate(
        # The foreground path widens, updates, subtracts, takes an absolute
        # value, and narrows. Declared as six copy-equivalent passes; the
        # calibration that turns that into wall time belongs outside the spec.
        work_per_megapixel=WorkUnits(6.0),
        # Large, and honestly so. The worst case is uint8 input, where one input
        # byte becomes four bytes of float32 model, four of widened frame, and
        # four of scratch — the three buffers `_Buffers` holds — plus the input
        # and the narrowed output: 1 + 4 + 4 + 4 + 1. Float64 input is under 1.
        # A static declaration takes the largest value any legal input produces,
        # which is why putting a downsample in front of this is the ordinary
        # graph rather than a tuning trick.
        peak_bytes_per_input_byte=14.0,
    ),
    authoring_group=AuthoringGroup.SPATIAL_PREP,
    authoring_order=40,
    mode=Mode.STREAMING,
    settling_epsilon=SETTLED_EPSILON,
    stateful=True,
    primary_params=("alpha", "emit"),
    caption=(
        CaptionPart(label="alpha", param="alpha", format_spec=".2f"),
        CaptionPart(param="emit"),
    ),
)
class BackgroundEmaParams(ParamsBase):
    """How fast the background forgets, and which half of the result to emit."""

    #: Weight of the newest frame. Lower bound is `MIN_ALPHA` because it is what
    #: `warmup_frames` was computed at and a smaller value would make the
    #: declared lead-in a lie. Upper bound 1.0 is the degenerate case — the
    #: model is the previous frame and the output is a frame difference — which
    #: is a legitimate thing to ask for, is not worth a second filter, and now
    #: costs the one frame of lead-in it needs rather than the bound's ninety.
    alpha: float = Field(default=MIN_ALPHA, ge=MIN_ALPHA, le=1.0)
    emit: Emit = Emit.FOREGROUND

    @classmethod
    def max_warmup_frames(cls) -> FrameCount:
        """Worst case over the legal `alpha` range."""
        return FrameCount(settle_frames(MIN_ALPHA))

    def warmup_frames(self) -> FrameCount:
        """`settle_frames(alpha)` — the bound, refined to the configured model.

        Equal to the spec's 90 at the default `alpha` and strictly below it
        everywhere else, which is the direction `node_warmup_frames` permits.
        `emit` does not enter: both halves are read off the same model, so a
        background that has not settled and a foreground taken against it are
        untrustworthy together.
        """
        return FrameCount(settle_frames(self.alpha))


#: Any floating array. The accumulator is `float32` for every input dtype except
#: `float64`, where narrowing the model would throw away precision the caller
#: chose that dtype to keep — `np.promote_types` against `float32` says exactly
#: that in one call and with no branch to get backwards.
FloatArray = NDArray[np.floating[Any]]


@dataclass(slots=True)
class _Buffers:
    """The three full-frame arrays one run reuses, allocated once.

    Together they are what `peak_bytes_per_input_byte=14` is counting, and they
    exist as a group because they are allocated as a group: the shape check that
    guards the model guards all three, and three independently-optional fields
    would be three places for a `None` to survive.
    """

    #: The background itself.
    model: FloatArray
    #: This frame, widened to the accumulator dtype.
    widened: FloatArray
    #: Working space for the update term and then for the difference. Reused
    #: within a frame because the update is finished before the difference
    #: starts, and reused across frames because a 25 MB allocation per frame at
    #: 1080p is most of what this filter would otherwise cost.
    scratch: FloatArray


@dataclass(slots=True)
class BackgroundState:
    """One run's model and its working arrays. Made by `KernelBinding.start`.

    Mutable, unlike almost everything else in this codebase, and that is the
    point of the item this arrived with: the state is the one thing about a run
    that changes as the run proceeds. What keeps it safe is that nothing else
    can reach it — it is created per `execute` and lives only in the binding, so
    two replicates previewing this node concurrently cannot mix their models.

    `None` until the first frame, rather than a zero array, because the seed
    matters: starting from black means the first outputs are the whole frame
    rather than the difference from it, and 90 frames of lead-in exist to make
    the seed's influence negligible rather than to hide a wrong one. It is also
    the only way the buffers can be sized — nothing tells a state factory what
    shape the footage is.
    """

    buffers: _Buffers | None = None

    def for_frame(self, data: NDArray[Any], index: FrameIndex) -> _Buffers:
        """This run's arrays, seeded on `data` if it is the first frame.

        The one place `buffers` is narrowed, so the kernel below reads three
        plain arrays rather than carrying an `is None` through every operation.

        Raises:
            ValueError: if the shape changed since the seed. The executor crops
                every root to a fixed ROI, so this cannot happen from a graph —
                and a silent reseed would hide whatever did cause it (a resized
                proxy, a second source spliced into one run) behind a model that
                quietly restarted its 90-frame warmup with nobody told.
        """
        if self.buffers is None:
            model = data.astype(np.promote_types(data.dtype, np.float32))
            self.buffers = _Buffers(
                model=model, widened=np.empty_like(model), scratch=np.empty_like(model)
            )
        elif self.buffers.model.shape != data.shape:
            raise ValueError(
                f"background_ema was seeded on a {self.buffers.model.shape} frame and handed a "
                f"{data.shape} one at index {index}; one run is one geometry"
            )
        return self.buffers


@stateful_kernel(BackgroundEmaParams, Backend.CPU, state=BackgroundState)
def background_ema_cpu(frame: Frame, params: BackgroundEmaParams, state: BackgroundState) -> Frame:
    """Update the model with this frame, then emit the requested half.

    Update first, unconditionally. Emitting the difference from the *previous*
    model would make the output depend on frame ordering in a second way beyond
    the state itself, and would make `alpha = 1.0` — where the model is the
    latest frame — emit a frame difference on one reading and zeros on the
    other. On the seed frame the update is arithmetically a no-op, because the
    model *is* the frame and the correction term is zero.

    **Every step writes into a buffer that already exists.** The readable form —
    `model += alpha * (current - model)` followed by `abs(current - model)` —
    allocates four full-frame float arrays per frame and measures 40.6 ms on
    1080p BGR against this version's 20.6 ms. At the 3 s `full_preview_render`
    budget that is the difference between 74 frames and 145. The cost is that
    the arithmetic has to be read as a sequence of `out=` writes; the comment on
    each line says which half of the formula it is.

    The 20.6 ms is not the floor. Most of what remains is `_narrow`'s two
    allocations, and they stay because removing them means rounding a buffer in
    place — safe for `scratch` on the foreground path and a corrupted model on
    the background one. A branch on which buffer may be mutated is the aliasing
    footgun `_narrow` exists to close, so the 6 ms stays until something is
    actually missing a budget by it.

    Raises:
        ValueError: if the frame's shape changes mid-run. See
            `BackgroundState.for_frame`.
    """
    buffers = state.for_frame(frame.data, frame.index)
    model, widened, scratch = buffers.model, buffers.widened, buffers.scratch

    # widened <- this frame, in the accumulator's dtype.
    np.copyto(widened, frame.data, casting="unsafe")
    # model <- model + alpha * (frame - model), in three writes and no allocation.
    np.subtract(widened, model, out=scratch)
    np.multiply(scratch, scratch.dtype.type(params.alpha), out=scratch)
    np.add(model, scratch, out=model)

    if params.emit is Emit.BACKGROUND:
        produced = model
    else:
        np.subtract(widened, model, out=scratch)
        produced = np.abs(scratch, out=scratch)

    return Frame(
        data=_narrow(produced, frame.data.dtype), index=frame.index, channels=frame.channels
    )


def _narrow(values: FloatArray, dtype: np.dtype[Any]) -> NDArray[Any]:
    """Return `values` as `dtype`, rounding rather than truncating for integers.

    Both quantities this narrows — a model of in-range samples and an absolute
    difference of two of them — are already inside the input dtype's range, so
    there is nothing to clip. What there is to get wrong is the rounding: a bare
    `astype` truncates toward zero, which biases every pixel of a background
    model downward by half a level on every frame it is read, and darkens the
    model against footage it should be tracking exactly.

    **Always a new array, never a view.** Its argument is always one of the
    state's three buffers — `model` on the background path, `scratch` on the
    foreground one — and both are written again on the very next frame. A view
    would hand the caller a frame that changes under it: a `FrameResult` the GUI
    is still painting, or a store entry that stops matching its key. `copy=False`
    here would be a one-line saving on one dtype and a use-after-free for
    everything else, which is why the float branch takes `astype`'s default.
    """
    if np.issubdtype(dtype, np.floating):
        return values.astype(dtype)
    return np.rint(values).astype(dtype)
