











from __future__ import annotations

import numpy as np
import numpy.typing as npt
import pytest

from sieve.core.types import ChannelSpec, Frame
from sieve.filters.temporal_baseline import (
    FPS_MAX,
    MAX_SAMPLES,
    WINDOW_SECONDS_MAX,
    BaselineState,
    Emit,
    TemporalBaselineParams,
    temporal_baseline_cpu,
    window_frames,
)

SPEC = TemporalBaselineParams.spec()

FPS = 30.0
NY, NX = 8, 8


def run(series: npt.NDArray[np.floating], params: TemporalBaselineParams) -> list[np.ndarray]:

    state = BaselineState()
    return [
        temporal_baseline_cpu(
            Frame(data=plane.astype(np.float32), index=index, channels=ChannelSpec.GRAY),
            params,
            state,
        ).data
        for index, plane in enumerate(series)
    ]


def quiet_with_event(
    frames: int, event_at: slice, amplitude: float, seed: int = 0
) -> npt.NDArray[np.float64]:

    rng = np.random.default_rng(seed)
    series = rng.normal(1.0, 0.1, size=(frames, NY, NX))
    series[event_at, 3, 4] += amplitude
    return series


def test_the_deviation_is_unchanged_by_a_gain_and_an_offset() -> None:
















    params = TemporalBaselineParams(window_seconds=4.0, fps=FPS)
    series = quiet_with_event(200, slice(150, 151), amplitude=3.0)

    series[:, 0, 0] = 5.0
    series[150, 0, 0] += 3.0

    plain = run(series, params)[150]
    relit = run(series * 7.0 + 2.0, params)[150]

    assert np.allclose(plain, relit, rtol=1e-3, atol=1e-3)


    assert plain[3, 4] > 10.0
    assert plain[0, 0] > 10.0


def test_events_do_not_inflate_the_spread_they_are_measured_against() -> None:










    params = TemporalBaselineParams(window_seconds=4.0, fps=FPS)
    span = window_frames(4.0, FPS)




    last = 3 * span
    series = quiet_with_event(4 * span, slice(last - span // 5 + 1, last + 1), amplitude=2.0)

    measured = float(run(series, params)[last][3, 4])

    window = series[last - span + 1 : last + 1, 3, 4]
    non_robust = (window[-1] - window.mean()) / window.std()

    assert measured > 15.0
    assert non_robust < 3.0


def test_a_bout_longer_than_the_window_disappears_into_its_own_baseline() -> None:













    bout = slice(600, 690)
    series = quiet_with_event(800, bout, amplitude=2.0)
    mid_bout = 660

    swallowed = run(series, TemporalBaselineParams(window_seconds=1.0, fps=FPS))[mid_bout]
    survives = run(series, TemporalBaselineParams(window_seconds=20.0, fps=FPS))[mid_bout]

    assert abs(float(swallowed[3, 4])) < 3.0
    assert float(survives[3, 4]) > 15.0


def test_the_declared_warmup_is_the_worst_case_over_the_legal_range() -> None:








    corner = TemporalBaselineParams(window_seconds=WINDOW_SECONDS_MAX, fps=FPS_MAX)
    assert corner.warmup_frames() == SPEC.warmup_frames

    default = TemporalBaselineParams()
    assert default.warmup_frames() == window_frames(default.window_seconds, default.fps) - 1
    assert default.warmup_frames() * 40 < SPEC.warmup_frames

    with pytest.raises(ValueError):
        TemporalBaselineParams(window_seconds=WINDOW_SECONDS_MAX * 2)
    with pytest.raises(ValueError):
        TemporalBaselineParams(fps=FPS_MAX * 2)


def test_a_strided_ring_still_spans_the_whole_window() -> None:














    params = TemporalBaselineParams(window_seconds=30.0, fps=FPS, emit=Emit.BASELINE)
    span = window_frames(30.0, FPS)
    frames = 1200
    ramp = np.arange(frames, dtype=np.float64)[:, None, None] * np.ones((1, NY, NX))

    baseline = float(run(ramp, params)[-1].mean())

    assert baseline == pytest.approx(frames - 1 - span / 2, abs=span / 30)

    assert abs(baseline - (frames - 1 - MAX_SAMPLES / 2)) > span / 4


def test_a_mid_run_shape_change_is_refused_rather_than_resized() -> None:

    params = TemporalBaselineParams()
    state = BaselineState()
    temporal_baseline_cpu(
        Frame(data=np.zeros((NY, NX), np.float32), index=0, channels=ChannelSpec.GRAY),
        params,
        state,
    )

    with pytest.raises(ValueError, match="one run is one geometry"):
        temporal_baseline_cpu(
            Frame(data=np.zeros((4, 4), np.float32), index=1, channels=ChannelSpec.GRAY),
            params,
            state,
        )
