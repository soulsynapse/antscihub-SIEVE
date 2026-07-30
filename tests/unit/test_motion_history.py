"""What this filter claims: a bounded bloom, a declared lag, and two operators.

The claims about *where* state lives — one accumulator per run, never shared,
never cached — belong to the executor and the registry and are tested in
`test_stateful_execution.py`. The claim that a refined warmup is charged instead
of a bound belongs to the contract and is tested in `test_filter_contract.py`.
What is left here is what only this filter can get wrong: that the coupling's
support stops growing, that `dilate` and `diffuse` differ in the way that made
shipping both worth it, that `tau_seconds` is a time and not a weight, and that
the group delay it declares is the one it has.
"""

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
#: Wide enough that a bounded bloom at `reach_blocks = 2` has room to stop
#: growing without reaching an edge — the assertion below is vacuous otherwise.
SIDE = 41
CENTRE = SIDE // 2


def run(series: npt.NDArray[np.floating], params: MotionHistoryParams) -> list[np.ndarray]:
    """Feed a `(frames, ny, nx)` series through one run and keep every output."""
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
    """One block held at `amplitude` for the whole run, every other block quiet."""
    series = np.zeros((frames, SIDE, SIDE))
    series[:, CENTRE, CENTRE] = amplitude
    return series


def support(field: np.ndarray, fraction: float = 1e-3) -> int:
    """Blocks above `fraction` of the field's peak — what a detector would see."""
    return int((field > fraction * field.max()).sum())


@pytest.mark.parametrize("couple", list(Couple))
def test_the_bloom_stops_growing(couple: Couple) -> None:
    """The stability bound, and the failure it catches is a beautiful demo.

    A morphological dilation propagates one block outward per frame. With the
    coupling unattenuated — `max(lambda * a, dilate(a))`, which is the obvious
    reading of "the active detections touch the ones around them" — a single
    driven block fills the arena and keeps it filled, and every frame of that
    looks like a wonderfully sensitive detector. Diffusion has the same failure
    with a slower front.

    What stops it is that the coupling attenuates with distance while the decay
    runs the whole time, so the profile has a length scale rather than a speed.
    The assertion is therefore about run length: the support after 2000 frames
    must be the support after 500, not larger. A test that only ran once would
    pass on an implementation whose bloom had simply not arrived yet.
    """
    params = MotionHistoryParams(tau_seconds=1.0, reach_blocks=2.0, couple=couple, fps=FPS)

    early = support(run(driven_block(500), params)[-1])
    late = support(run(driven_block(2000), params)[-1])

    assert early == late
    # The coupling did something — otherwise "stopped growing" is trivially true
    # of a filter with no coupling at all.
    assert late > 1
    # And it did not simply reach the walls, which is the failure above wearing
    # a steady state as a disguise.
    assert late < SIDE * SIDE // 3


def test_dilate_sustains_the_peak_and_diffuse_spreads_it_down() -> None:
    """Why two coupling modes ship rather than one.

    Diffusion is conservative: it moves activity around without creating any, so
    the peak falls as the support widens — which fights the threshold
    downstream, and is the reason `dilate` is expected to win. A morphological
    dilation is a gate rather than a smear: a block takes the *largest* of its
    own value and its neighbours' attenuated ones, so a block that is the
    largest thing around keeps exactly the value it would have had uncoupled.

    Both halves are asserted because either alone is satisfiable by an accident.
    "Dilate does not lower the peak" is true of no coupling at all, and "diffuse
    lowers the peak" is true of any lossy operator; together with the widths they
    pin the two operators apart.
    """
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
    """The parameter is in physical units, and this is what that has to mean.

    Drive a block to its steady state, cut the input, and the accumulator must
    fall to `1/e` after `tau_seconds` of footage — at *any* frame rate. A filter
    that stored a per-frame weight and called it seconds would pass at 30 fps
    and decay twice as fast at 60, which is exactly the failure that makes a
    parameter untransferable between two recordings of the same experiment.
    """
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
    """A declaration nothing checks is prose, and this is the check.

    The whole reason the delay is declared rather than removed is that a
    consumer aligning an onset against another data stream will subtract it. So
    the number has to be the lag rather than a plausible number near it: the
    test measures the centroid of the impulse response and compares, which is
    the same quantity the docstring's `lambda / (1 - lambda)` is derived as.

    Also asserted at two persistence times, because the failure worth catching
    is not an arithmetic slip but a declaration that stopped tracking the
    parameter it is about.
    """
    for tau in (0.5, 2.0):
        params = MotionHistoryParams(tau_seconds=tau, reach_blocks=0.0, fps=FPS)
        impulse = np.zeros((int(30 * tau * FPS), SIDE, SIDE))
        impulse[0, CENTRE, CENTRE] = 1.0

        response = np.array([frame[CENTRE, CENTRE] for frame in run(impulse, params)], np.float64)
        centroid = float((np.arange(response.size) * response).sum() / response.sum())

        assert centroid == pytest.approx(params.group_delay_frames(), rel=1e-3)
        assert params.group_delay_seconds() == pytest.approx(params.group_delay_frames() / FPS)
        # `tau - dt/2`, which is the guidance's "roughly tau" made exact — and
        # is the half-frame a naive `tau * fps` declaration would be wrong by.
        assert params.group_delay_seconds() == pytest.approx(tau - 0.5 / FPS, rel=1e-3)


def test_the_declared_warmup_is_a_bound_that_every_run_refines() -> None:
    """The bound is reached only at the corner, and the refinement is enough.

    Two failures, one test, because they are the two directions the pair can be
    wrong in. A bound that stops being one — relaxing `TAU_SECONDS_MAX` is a
    one-line edit — lets a configuration ask for more lead-in than the spec
    admits, which `node_warmup_frames` refuses at run time and only for the user
    who found it. A refinement that is too small under-warms silently, so the
    kernel is actually run for that many frames and the accumulator has to have
    arrived.
    """
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
    """The source is half-wave rectified, and that is a decision with a victim.

    `temporal_baseline` emits signed deviations, so a quiet stretch after a bout
    is a run of *negative* numbers. Integrated with their sign they would cancel
    the bout that just happened, and the accumulator would report less history
    the longer the animal has been still — the exact inverse of what it is for.
    """
    params = MotionHistoryParams(tau_seconds=2.0, reach_blocks=0.0, fps=FPS)
    bout = driven_block(30, amplitude=4.0)
    lull = driven_block(15, amplitude=-4.0)

    with_lull = run(np.concatenate([bout, lull]), params)[-1]
    with_quiet = run(np.concatenate([bout, np.zeros_like(lull)]), params)[-1]

    assert float(with_lull[CENTRE, CENTRE]) == pytest.approx(float(with_quiet[CENTRE, CENTRE]))
    assert float(with_lull[CENTRE, CENTRE]) > 1.0


def test_diffusion_sub_steps_rather_than_going_unstable() -> None:
    """The explicit heat scheme diverges above a diffusion number of 1/4.

    A cost that rises with a parameter is easy to lose in a refactor, and what
    would be left is a five-point update that oscillates: the checkerboard grows
    without bound and the output is not a smeared detection but a garbage one.
    So the sub-step count is asserted against the coefficient it exists to
    bound, and the field it produces is asserted to stay inside its own source.
    """
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
    """A silent reallocation would restart the warmup with nobody told."""
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
    """The coupling is a two-dimensional neighbourhood, and says so.

    The stencil would otherwise read the channel axis as a third spatial one and
    diffuse blue into green — a plausible-looking frame with no defensible
    meaning, which is the failure `group_delay`'s declaration and this one both
    exist to keep out of the graph.
    """
    with pytest.raises(ValueError, match="GRAY grid"):
        motion_history_cpu(
            Frame(data=np.zeros((8, 8, 3), np.float32), index=0, channels=ChannelSpec.BGR),
            MotionHistoryParams(),
            MotionHistoryState(),
        )


def test_group_delay_tracks_the_decay_it_is_derived_from() -> None:
    """A longer persistence lags more, monotonically, in both units."""
    delays = [group_delay(tau, FPS) for tau in (0.2, 1.0, 5.0)]

    assert delays == sorted(delays)
    assert group_delay(1.0, 2 * FPS) == pytest.approx(2 * group_delay(1.0, FPS), rel=0.02)
