"""The kernel's own claims: that it remembers, and that its warmup is honest.

The claims about *where* state lives — one per run, never shared, never cached —
are properties of the executor and the registry and are tested in
`test_stateful_execution.py` alongside the machinery that provides them. What is
left here is what only this filter can get wrong: the recursion, the declared
settle time, and the narrowing on the way back out.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import numpy.typing as npt
import pytest
from pydantic import ValidationError

from sieve.core.filter_base import node_warmup_frames
from sieve.core.types import ChannelSpec, Frame, FrameCount
from sieve.filters.background_ema import (
    MIN_ALPHA,
    SETTLED_EPSILON,
    BackgroundEmaParams,
    BackgroundState,
    Emit,
    background_ema_cpu,
    settle_frames,
)

#: The shipped spec. Read through a narrowing helper rather than asserted at
#: module scope, because `__filter_spec__` is `FilterSpec | None` and a bare
#: module-level assert does not narrow it inside a function body.
SPEC = BackgroundEmaParams.spec()

WIDTH, HEIGHT = 12, 9

DEFAULTS = BackgroundEmaParams()
SETTLED = BackgroundEmaParams(emit=Emit.BACKGROUND)


def flat(value: float, index: int = 0, dtype: npt.DTypeLike = np.uint8) -> Frame:
    """A frame of one intensity, so the model is a single number to reason about."""
    data: npt.NDArray[Any] = np.full((HEIGHT, WIDTH), value, dtype=dtype)
    return Frame(data=data, index=index, channels=ChannelSpec.GRAY)


def drive(state: BackgroundState, level: float, count: int, params: BackgroundEmaParams) -> Frame:
    """Feed `count` frames of one level and hand back the last output."""
    produced = background_ema_cpu(flat(level, 0), params, state)
    for index in range(1, count):
        produced = background_ema_cpu(flat(level, index), params, state)
    return produced


def test_the_state_is_what_makes_the_output_differ_for_one_frame() -> None:
    """The same frame through a cold state and a warm one is two answers.

    This is the whole point of the item, stated at the smallest scale that can
    state it. A stateless kernel — which is every other kernel in this repo —
    cannot produce two answers for one input, so if these two agree, nothing is
    being remembered and the 90 frames of lead-in the spec asks for are being
    decoded for nothing.
    """
    cold = BackgroundState()
    warm = BackgroundState()
    drive(warm, level=200, count=30, params=DEFAULTS)

    from_cold = background_ema_cpu(flat(100, index=30), DEFAULTS, cold)
    from_warm = background_ema_cpu(flat(100, index=30), DEFAULTS, warm)

    # Cold: the model is seeded to this very frame, so there is nothing to
    # differ from. Warm: the model is still near 200, so 100 is foreground.
    assert not from_cold.data.any()
    assert from_warm.data.mean() > 50


def test_the_model_converges_to_within_the_declared_epsilon_by_the_declared_frame() -> None:
    """`warmup_frames=90` is a claim about convergence, and this is that claim.

    An EMA's warmup is nominally infinite, so the spec declares a
    settled-to-within-epsilon number and the epsilon it is judged against.
    Nothing else in the repo checks that the number and the epsilon describe the
    same filter — `test_warmup.py` checks the arithmetic that *propagates* a
    warmup and would be equally happy with a declaration of 3 or 3000.

    Two seeds two hundred levels apart, then identical footage: after
    `warmup_frames` the two models must agree to within `epsilon` of the gap
    they started with, because that is what the residual weight on the seed
    means.
    """
    gap = 200.0
    epsilon = SPEC.settling_epsilon
    assert epsilon == SETTLED_EPSILON

    def divergence_after(frames: int) -> float:
        """How far apart two models seeded `gap` apart are after `frames` more."""
        low, high = BackgroundState(), BackgroundState()
        from_low = background_ema_cpu(flat(0), SETTLED, low)
        from_high = background_ema_cpu(flat(gap), SETTLED, high)
        for index in range(1, frames + 1):
            from_low = background_ema_cpu(flat(128, index), SETTLED, low)
            from_high = background_ema_cpu(flat(128, index), SETTLED, high)
        return abs(float(from_low.data.mean()) - float(from_high.data.mean()))

    assert epsilon is not None
    assert divergence_after(SPEC.warmup_frames.frames) <= gap * epsilon

    # And the declaration is not slack by an order of magnitude: a tenth of the
    # frames must *not* be enough, or `warmup_frames` would be paying for
    # lead-in nobody needs.
    assert divergence_after(SPEC.warmup_frames.frames // 10) > gap * epsilon


def test_the_declared_warmup_is_the_worst_case_over_the_legal_alpha_range() -> None:
    """90 is `settle_frames(MIN_ALPHA)`, and no legal `alpha` needs more.

    The failure this closes is a lower bound on `alpha` being relaxed later —
    which is a one-character edit to a `Field` — without `warmup_frames` moving
    with it. That would leave the spec declaring a lead-in shorter than the
    filter needs, which is the silent direction: the preview renders, the model
    has not settled, and the tuning done against it is wrong rather than absent.
    """
    lower_bound = MIN_ALPHA
    assert BackgroundEmaParams(alpha=lower_bound).alpha == lower_bound
    with pytest.raises(ValidationError):
        BackgroundEmaParams(alpha=lower_bound / 2)

    assert SPEC.warmup_frames == FrameCount(settle_frames(lower_bound))
    assert settle_frames(1.0) == 1
    # Monotone: a slower model needs more warmup, which is why the bound is the
    # worst case rather than the default.
    assert settle_frames(0.5) < settle_frames(0.1) < settle_frames(lower_bound)


def test_a_fast_model_is_charged_its_own_warmup_rather_than_the_bound() -> None:
    """The bound is the worst case; a run pays for the `alpha` it configured.

    Until `ParamsBase.warmup_frames` existed, `alpha = 0.5` decoded 90 frames of
    lead-in to settle a model that needs 7, and this filter's docstring argued
    the waste was the price of a true declaration. It is not the price any more,
    and this is the assertion that says so — it fails if the override is dropped
    and the spec's constant silently takes over again.
    """
    step = (SPEC, BackgroundEmaParams(alpha=0.5))

    assert node_warmup_frames(step) == FrameCount(settle_frames(0.5)) == FrameCount(7)
    assert node_warmup_frames((SPEC, BackgroundEmaParams())) == SPEC.warmup_frames


@pytest.mark.parametrize("dtype", [np.uint8, np.uint16, np.float32, np.float64])
def test_the_output_dtype_is_the_inputs_however_wide_the_accumulator(
    dtype: npt.DTypeLike,
) -> None:
    """The frame that comes out is the dtype the graph declared it would be.

    The model is float internally whatever arrived, so without the narrowing
    every downstream node would see float64 where the edge check promised
    uint8 — and `ArraySpec.admits` would have been satisfied by a declaration
    the kernel did not keep.
    """
    produced = drive(BackgroundState(), level=50, count=3, params=SETTLED)
    assert produced.data.dtype == np.dtype(np.uint8)

    widened = background_ema_cpu(flat(50, 3, dtype), DEFAULTS, BackgroundState())
    assert widened.data.dtype == np.dtype(dtype)


def test_an_emitted_frame_is_not_a_view_of_the_state() -> None:
    """The next frame must not rewrite the last one under its holder.

    Both emit paths hand back one of the state's three reused buffers, and both
    would be correct for exactly one frame if returned as a view. The symptom is
    remote from the cause: a `FrameResult` the GUI is still painting changes
    mid-paint, and a store entry stops matching the key it was written under.
    Float32 is the dtype where a careless `astype(copy=False)` is a no-op and so
    is the one that catches it.
    """
    for emit in Emit:
        state = BackgroundState()
        params = BackgroundEmaParams(alpha=0.5, emit=emit)
        first = background_ema_cpu(flat(10, 0, np.float32), params, state)
        held = first.data.copy()
        background_ema_cpu(flat(250, 1, np.float32), params, state)

        assert np.array_equal(first.data, held), f"{emit} handed back a view of the state"


def test_a_mid_run_shape_change_is_refused_rather_than_reseeded() -> None:
    """A silent reseed would restart the 90-frame warmup with nobody told."""
    state = BackgroundState()
    background_ema_cpu(flat(10), DEFAULTS, state)

    other = Frame(data=np.zeros((4, 4), np.uint8), index=1, channels=ChannelSpec.GRAY)
    with pytest.raises(ValueError, match="one run is one geometry"):
        background_ema_cpu(other, DEFAULTS, state)
