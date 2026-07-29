








from __future__ import annotations

from typing import Any

import numpy as np
import numpy.typing as npt
import pytest
from pydantic import ValidationError

from sieve.core.filter_base import node_warmup_frames
from sieve.core.types import ChannelSpec, Frame
from sieve.filters.background_ema import (
    MIN_ALPHA,
    SETTLED_EPSILON,
    BackgroundEmaParams,
    BackgroundState,
    Emit,
    background_ema_cpu,
    settle_frames,
)




SPEC = BackgroundEmaParams.spec()

WIDTH, HEIGHT = 12, 9

DEFAULTS = BackgroundEmaParams()
SETTLED = BackgroundEmaParams(emit=Emit.BACKGROUND)


def flat(value: float, index: int = 0, dtype: npt.DTypeLike = np.uint8) -> Frame:

    data: npt.NDArray[Any] = np.full((HEIGHT, WIDTH), value, dtype=dtype)
    return Frame(data=data, index=index, channels=ChannelSpec.GRAY)


def drive(state: BackgroundState, level: float, count: int, params: BackgroundEmaParams) -> Frame:

    produced = background_ema_cpu(flat(level, 0), params, state)
    for index in range(1, count):
        produced = background_ema_cpu(flat(level, index), params, state)
    return produced


def test_the_state_is_what_makes_the_output_differ_for_one_frame() -> None:








    cold = BackgroundState()
    warm = BackgroundState()
    drive(warm, level=200, count=30, params=DEFAULTS)

    from_cold = background_ema_cpu(flat(100, index=30), DEFAULTS, cold)
    from_warm = background_ema_cpu(flat(100, index=30), DEFAULTS, warm)



    assert not from_cold.data.any()
    assert from_warm.data.mean() > 50


def test_the_model_converges_to_within_the_declared_epsilon_by_the_declared_frame() -> None:













    gap = 200.0

    def divergence_after(frames: int) -> float:

        low, high = BackgroundState(), BackgroundState()
        from_low = background_ema_cpu(flat(0), SETTLED, low)
        from_high = background_ema_cpu(flat(gap), SETTLED, high)
        for index in range(1, frames + 1):
            from_low = background_ema_cpu(flat(128, index), SETTLED, low)
            from_high = background_ema_cpu(flat(128, index), SETTLED, high)
        return abs(float(from_low.data.mean()) - float(from_high.data.mean()))

    assert divergence_after(SPEC.warmup_frames) <= gap * SETTLED_EPSILON




    assert divergence_after(SPEC.warmup_frames // 10) > gap * SETTLED_EPSILON


def test_the_declared_warmup_is_the_worst_case_over_the_legal_alpha_range() -> None:








    lower_bound = MIN_ALPHA
    assert BackgroundEmaParams(alpha=lower_bound).alpha == lower_bound
    with pytest.raises(ValidationError):
        BackgroundEmaParams(alpha=lower_bound / 2)

    assert SPEC.warmup_frames == settle_frames(lower_bound)
    assert settle_frames(1.0) == 1


    assert settle_frames(0.5) < settle_frames(0.1) < settle_frames(lower_bound)


def test_a_fast_model_is_charged_its_own_warmup_rather_than_the_bound() -> None:








    step = (SPEC, BackgroundEmaParams(alpha=0.5))

    assert node_warmup_frames(step) == settle_frames(0.5) == 7
    assert node_warmup_frames((SPEC, BackgroundEmaParams())) == SPEC.warmup_frames


@pytest.mark.parametrize("dtype", [np.uint8, np.uint16, np.float32, np.float64])
def test_the_output_dtype_is_the_inputs_however_wide_the_accumulator(
    dtype: npt.DTypeLike,
) -> None:







    produced = drive(BackgroundState(), level=50, count=3, params=SETTLED)
    assert produced.data.dtype == np.dtype(np.uint8)

    widened = background_ema_cpu(flat(50, 3, dtype), DEFAULTS, BackgroundState())
    assert widened.data.dtype == np.dtype(dtype)


def test_an_emitted_frame_is_not_a_view_of_the_state() -> None:









    for emit in Emit:
        state = BackgroundState()
        params = BackgroundEmaParams(alpha=0.5, emit=emit)
        first = background_ema_cpu(flat(10, 0, np.float32), params, state)
        held = first.data.copy()
        background_ema_cpu(flat(250, 1, np.float32), params, state)

        assert np.array_equal(first.data, held), f"{emit} handed back a view of the state"


def test_a_mid_run_shape_change_is_refused_rather_than_reseeded() -> None:

    state = BackgroundState()
    background_ema_cpu(flat(10), DEFAULTS, state)

    other = Frame(data=np.zeros((4, 4), np.uint8), index=1, channels=ChannelSpec.GRAY)
    with pytest.raises(ValueError, match="one run is one geometry"):
        background_ema_cpu(other, DEFAULTS, state)
