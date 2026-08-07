"""An exponential moving-average background model, and the difference from it.

VISION step 1 names background subtraction first, and step 3's category C is
this. Ported from v2's module of the same name; what carries is the model, the
two emits, and the convergence argument behind `warmup_frames`.

The model is `bg <- bg + alpha * (frame - bg)`, seeded with the first frame it
sees. `alpha` is the weight of the newest frame: small means a background that
takes a long time to accept a change and therefore keeps a stopped ant in the
foreground; large means one that absorbs the ant and leaves only its motion.
There is no correct value — that is a question about how long the animals in
this footage hold still, which is why it is the primary parameter and not a
constant (`adr/param-not-preference.md`).

**Why the bound is 90 frames and what epsilon it is settled to.** An EMA's true
warmup is infinite: the seed frame's weight after `n` updates is `(1 - alpha)^n`,
which is never zero. What the declaration takes instead is the number of frames
after which the seed retains less than **1% of the model's weight**:
`ceil(ln 0.01 / ln (1 - alpha))`. The spec's 90 is that at `alpha = 0.05`, the
lower bound of the legal range — the worst case, which is what a bound printed
without a configuration in hand has to be. `BackgroundEmaParams.warmup_frames`
refines it to the configured `alpha`, so `alpha = 0.5` asks for the 7 frames it
actually needs rather than 90.

The refinement may only shrink the bound, and the asymmetry has this tool's own
reason behind it as well as the contract's: a lead-in that was right on average
would be wrong exactly when `alpha` is small, which is the setting a user reaches
for when the animals are still, which is when the background matters most. v2
carried the 90 unrefined and documented the 83 wasted frames as the price of a
declaration true for every parameter setting; `temporal_baseline` arriving with
the same problem an order of magnitude larger is what bought the params-derived
half of the contract (`core/tool_base.py`).

A 90-frame lead-in is also the first one large enough that
`ExecutionPlan.lead_in_shortfall` means something: a span starting less than 90
frames into the source cannot be warmed, `sieve run` says so, and no other tool
on the shelf asks for enough lead-in to produce that warning against an ordinary
request.

**Uncacheable, and not because it is unreproducible.** The spec declares
`stateful=True`, so `cache_key.is_cacheable` is False and no key is derived for
the node. This tool would in fact be safe to cache — the 90 above is the claim
that its output stops depending on where the run started, and that claim is true
and tested. What cannot be cached is the *category*: nothing that derives a key
can tell this declaration from a false one, so the exclusion is on statefulness
rather than on a number (`pipeline/cache_key.py`).

v2 declared a `CostEstimate` here; it is cut for `block_signal.py`'s reason — it
fed machinery v3 has not built, and a declaration arrives with its consumer
(`adr/declared-means-verified.md`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

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
)
from sieve.core.tool_registry import register_tool
from sieve.core.types import Frame, FrameCount, FrameIndex, FrameSpan

#: What the accumulator can hold without losing the input's range. Same set as
#: `downsample`'s, so the two chain in either order — the ordinary graph is a
#: downsample in front of this one, because the model is the largest thing a
#: run holds and it is float32 whatever the input was.
SUPPORTED_DTYPES = ("uint8", "uint16", "float32", "float64")

#: The smallest weight the newest frame may carry. Sets the warmup bound below,
#: and is a bound rather than a preference: an `alpha` of 0.01 is a legitimate
#: thing to want and would need 459 frames of lead-in, which is a different tool
#: version's decision rather than a slider position.
MIN_ALPHA = 0.05

#: How much of the seed frame's weight is allowed to remain before the model
#: counts as settled. Stated as a constant because the module docstring's
#: arithmetic is unreadable without a name for it and because a reader checking
#: the 90 below should not have to find the number in prose.
SETTLED_EPSILON = 0.01

#: Any floating array. The accumulator is `float32` for every input dtype except
#: `float64`, where narrowing the model would throw away precision the caller
#: chose that dtype to keep — `np.promote_types` against `float32` says exactly
#: that in one call and with no branch to get backwards.
FloatArray = NDArray[np.floating[Any]]


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
    """Which of the two things this tool has computed leaves the node."""

    #: `|frame - background|`. What a detector downstream wants.
    FOREGROUND = "foreground"
    #: The model itself. What a user tuning `alpha` needs to look at, since the
    #: foreground only shows the model indirectly and a background that has
    #: absorbed the animals looks the same as one that never saw them.
    BACKGROUND = "background"


@dataclass(slots=True)
class _Buffers:
    """The three full-frame arrays one run reuses, allocated once.

    They exist as a group because they are allocated as a group: the shape check
    that guards the model guards all three, and three independently-optional
    fields would be three places for a `None` to survive.
    """

    #: The background itself.
    model: FloatArray
    #: This frame, widened to the accumulator dtype.
    widened: FloatArray
    #: Working space for the update term and then for the difference. Reused
    #: within a frame because the update is finished before the difference
    #: starts, and reused across frames because a 25 MB allocation per frame at
    #: 1080p is most of what this tool would otherwise cost.
    scratch: FloatArray


@dataclass(slots=True)
class BackgroundState:
    """One run's model and its working arrays. Minted per run by the executor.

    Mutable, unlike almost everything else in this codebase: the state is the
    one thing about a run that changes as the run proceeds. What keeps it safe
    is that nothing else can reach it — it is made from `ToolSpec.state_factory`
    per run rather than closed over, so two replicates previewing this node
    concurrently cannot mix their models (`adr/no-kernel-apparatus.md`).

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


def run(params: BackgroundEmaParams, window: FrameSpan, state: BackgroundState, /) -> Frame:
    """Update the model with this frame, then emit the requested half.

    Update first, unconditionally. Emitting the difference from the *previous*
    model would make the output depend on frame ordering in a second way beyond
    the state itself, and would make `alpha = 1.0` — where the model is the
    latest frame — emit a frame difference on one reading and zeros on the
    other. On the seed frame the update is arithmetically a no-op, because the
    model *is* the frame and the correction term is zero.

    **Every step writes into a buffer that already exists.** The readable form —
    `model += alpha * (current - model)` followed by `abs(current - model)` —
    allocates four full-frame float arrays per frame, and v2 measured it at
    40.6 ms on 1080p BGR against this version's 20.6 ms. Over a 3 s preview that
    is the difference between 74 frames and 145. The cost is that the arithmetic
    has to be read as a sequence of `out=` writes; the comment on each line says
    which half of the formula it is.

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
    frame = window.target
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


@register_tool(
    tool_id="background_ema",
    version="1.0.0",
    summary="Exponential moving-average background model, and the difference from it.",
    accepts=ArraySpec(dtypes=SUPPORTED_DTYPES),
    # Channels unstated on both sides: the model is per channel and the layout
    # carries through untouched, so constraining either side would reject frames
    # this handles.
    emits=ArraySpec(dtypes=SUPPORTED_DTYPES),
    # Two products of one model, and a session tuning `alpha` wants to keep both
    # — the foreground cannot show a background that absorbed the animals.
    emissions=(Emission(Emit.FOREGROUND, "emit"), Emission(Emit.BACKGROUND, "emit")),
    run=run,
    # The model is per element and so is the difference from it; the geometry
    # is untouched, exactly as the unstated channels above say.
    element=ElementRelation.PRESERVED,
    mode=Mode.STREAMING,
    settling_epsilon=SETTLED_EPSILON,
    stateful=True,
    state_factory=BackgroundState,
    primary_params=("alpha", "emit"),
    caption=(
        CaptionPart(label="alpha", param="alpha", format_spec=".2f"),
        CaptionPart(param="emit"),
    ),
    param_stereotypes={
        "alpha": ParamStereotype.SCALAR_RANGE,
        "emit": ParamStereotype.ENUM,
    },
)
class BackgroundEmaParams(ParamsBase):
    """How fast the background forgets, and which half of the result to emit."""

    #: Weight of the newest frame. Lower bound is `MIN_ALPHA` because it is what
    #: the warmup bound was computed at and a smaller value would make the
    #: declared lead-in a lie. Upper bound 1.0 is the degenerate case — the
    #: model is the previous frame and the output is a frame difference — which
    #: is a legitimate thing to ask for, is not worth a second tool, and costs
    #: the one frame of lead-in it needs rather than the bound's ninety.
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


def _narrow(values: FloatArray, dtype: np.dtype[Any]) -> NDArray[Any]:
    """Return `values` as `dtype`, rounding rather than truncating for integers.

    Both quantities this narrows — a model of in-range samples and an absolute
    difference of two of them — are already inside the input dtype's range, so
    there is no saturation to handle. What there is to get wrong is the
    rounding: a bare `astype` truncates toward zero, which biases every pixel of
    a background model downward by half a level on every frame it is read, and
    darkens the model against footage it should be tracking exactly.

    **Always a new array, never a view.** Its argument is always one of the
    state's three buffers — `model` on the background path, `scratch` on the
    foreground one — and both are written again on the very next frame. A view
    would hand the caller a frame that changes under it: a result the GUI is
    still painting, or a store entry that stops matching its key. `copy=False`
    here would be a one-line saving on one dtype and a use-after-free for
    everything else, which is why the float branch takes `astype`'s default.
    """
    if np.issubdtype(dtype, np.floating):
        return values.astype(dtype)
    return np.rint(values).astype(dtype)
