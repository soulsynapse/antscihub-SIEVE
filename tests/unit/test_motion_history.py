











from __future__ import annotations

import numpy as np
import numpy.typing as npt
import pytest

from sieve.core.types import ChannelSpec, Frame
from sieve.filters.motion_history import (
    FPS_MAX,
    MAX_DIFFUSION_NUMBER,
    REACH_BLOCKS_MAX,
    TAU_SECONDS_MAX,
    Couple,
    MotionHistoryParams,
    MotionHistoryState,
    decay_lambda,
    diffusion_number,
    diffusion_substeps,
    group_delay,
    motion_history_cpu,
    settle_frames,
)

SPEC = MotionHistoryParams.spec()

FPS = 30.0


SIDE = 41
CENTRE = SIDE // 2


def run(series: npt.NDArray[np.floating], params: MotionHistoryParams) -> list[np.ndarray]:

    state = MotionHistoryState()
    return [
        motion_history_cpu(
            Frame(data=plane.astype(np.float32), index=index, channels=ChannelSpec.GRAY),
            params,
            state,
        ).data
        for index, plane in enumerate(series)
    ]


def driven_block(frames: int, amplitude: float = 1.0) -> npt.NDArray[np.float64]:

    series = np.zeros((frames, SIDE, SIDE))
    series[:, CENTRE, CENTRE] = amplitude
    return series


def support(field: np.ndarray, fraction: float = 1e-3) -> int:

    return int((field > fraction * field.max()).sum())


@pytest.mark.parametrize("couple", list(Couple))
def test_the_bloom_stops_growing(couple: Couple) -> None:















    params = MotionHistoryParams(tau_seconds=1.0, reach_blocks=2.0, couple=couple, fps=FPS)

    early = support(run(driven_block(500), params)[-1])
    late = support(run(driven_block(2000), params)[-1])

    assert early == late


    assert late > 1


    assert late < SIDE * SIDE // 3


def test_dilate_sustains_the_peak_and_diffuse_spreads_it_down() -> None:














    frames = driven_block(600)
    uncoupled = run(frames, MotionHistoryParams(tau_seconds=1.0, reach_blocks=0.0, fps=FPS))[-1]
    dilated = run(
        frames,
        MotionHistoryParams(tau_seconds=1.0, reach_blocks=2.0, couple=Couple.DILATE, fps=FPS),
    )[-1]
    diffused = run(
        frames,
        MotionHistoryParams(tau_seconds=1.0, reach_blocks=2.0, couple=Couple.DIFFUSE, fps=FPS),
    )[-1]

    peak = float(uncoupled[CENTRE, CENTRE])
    assert float(dilated[CENTRE, CENTRE]) == pytest.approx(peak, rel=1e-5)
    assert float(diffused[CENTRE, CENTRE]) < peak / 3.0

    assert support(uncoupled) == 1
    assert support(dilated) > 1
    assert support(diffused) > 1


def test_tau_seconds_is_a_time_and_not_a_weight() -> None:








    for fps in (30.0, 60.0):
        tau = 1.0
        held = round(4.0 * tau * fps)
        series = np.concatenate([driven_block(held), np.zeros((held, SIDE, SIDE))])

        out = run(series, MotionHistoryParams(tau_seconds=tau, reach_blocks=0.0, fps=fps))
        after_one_tau = round(tau * fps)

        decayed = out[held - 1 + after_one_tau][CENTRE, CENTRE]
        ratio = float(decayed / out[held - 1][CENTRE, CENTRE])
        assert ratio == pytest.approx(1.0 / np.e, rel=0.01)


def test_the_declared_group_delay_is_the_lag_the_filter_has() -> None:












    for tau in (0.5, 2.0):
        params = MotionHistoryParams(tau_seconds=tau, reach_blocks=0.0, fps=FPS)
        impulse = np.zeros((int(30 * tau * FPS), SIDE, SIDE))
        impulse[0, CENTRE, CENTRE] = 1.0

        response = np.array([frame[CENTRE, CENTRE] for frame in run(impulse, params)], np.float64)
        centroid = float((np.arange(response.size) * response).sum() / response.sum())

        assert centroid == pytest.approx(params.group_delay_frames(), rel=1e-3)
        assert params.group_delay_seconds() == pytest.approx(params.group_delay_frames() / FPS)


        assert params.group_delay_seconds() == pytest.approx(tau - 0.5 / FPS, rel=1e-3)


def test_the_declared_warmup_is_a_bound_that_every_run_refines() -> None:










    corner = MotionHistoryParams(tau_seconds=TAU_SECONDS_MAX, fps=FPS_MAX)
    assert corner.warmup_frames() == SPEC.warmup_frames

    params = MotionHistoryParams(tau_seconds=1.0, reach_blocks=0.0, fps=FPS)
    warmup = params.warmup_frames()
    assert warmup == settle_frames(1.0, FPS)
    assert warmup * 70 < SPEC.warmup_frames

    settled = run(driven_block(warmup + 1), params)[warmup]
    assert float(settled[CENTRE, CENTRE]) > 1.0 - 2.0 * (1.0 - decay_lambda(1.0, FPS))
    assert float(settled[CENTRE, CENTRE]) == pytest.approx(1.0, abs=0.01)


def test_a_lull_below_baseline_does_not_erase_the_history() -> None:







    params = MotionHistoryParams(tau_seconds=2.0, reach_blocks=0.0, fps=FPS)
    bout = driven_block(30, amplitude=4.0)
    lull = driven_block(15, amplitude=-4.0)

    with_lull = run(np.concatenate([bout, lull]), params)[-1]
    with_quiet = run(np.concatenate([bout, np.zeros_like(lull)]), params)[-1]

    assert float(with_lull[CENTRE, CENTRE]) == pytest.approx(float(with_quiet[CENTRE, CENTRE]))
    assert float(with_lull[CENTRE, CENTRE]) > 1.0


def test_diffusion_sub_steps_rather_than_going_unstable() -> None:








    reach, tau = REACH_BLOCKS_MAX, 0.1
    assert diffusion_number(reach, tau, FPS) > MAX_DIFFUSION_NUMBER
    steps = diffusion_substeps(reach, tau, FPS)
    assert diffusion_number(reach, tau, FPS) / steps <= MAX_DIFFUSION_NUMBER

    params = MotionHistoryParams(
        tau_seconds=tau, reach_blocks=reach, couple=Couple.DIFFUSE, fps=FPS
    )
    field = run(driven_block(200), params)[-1]

    assert np.all(field >= 0.0)
    assert float(field.max()) <= 1.0


def test_a_mid_run_shape_change_is_refused_rather_than_resized() -> None:

    params = MotionHistoryParams()
    state = MotionHistoryState()
    motion_history_cpu(
        Frame(data=np.zeros((8, 8), np.float32), index=0, channels=ChannelSpec.GRAY), params, state
    )

    with pytest.raises(ValueError, match="one run is one geometry"):
        motion_history_cpu(
            Frame(data=np.zeros((4, 4), np.float32), index=1, channels=ChannelSpec.GRAY),
            params,
            state,
        )


def test_a_frame_with_a_channel_axis_is_refused() -> None:







    with pytest.raises(ValueError, match="GRAY grid"):
        motion_history_cpu(
            Frame(data=np.zeros((8, 8, 3), np.float32), index=0, channels=ChannelSpec.BGR),
            MotionHistoryParams(),
            MotionHistoryState(),
        )


def test_group_delay_tracks_the_decay_it_is_derived_from() -> None:

    delays = [group_delay(tau, FPS) for tau in (0.2, 1.0, 5.0)]

    assert delays == sorted(delays)
    assert group_delay(1.0, 2 * FPS) == pytest.approx(2 * group_delay(1.0, FPS), rel=0.02)
