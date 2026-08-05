"""What this filter claims: a unit that transfers, and a window that means it.

The claims about *where* state lives — one ring per run, never shared, never
cached — belong to the executor and the registry and are tested in
`test_stateful_execution.py`. The claim that a refined warmup is charged instead
of a bound belongs to the contract and is tested in `test_filter_contract.py`.
What is left here is what only this filter can get wrong: that the deviation is
a number about the block rather than about the lighting, that the robust
statistics are actually robust, and that `window_seconds` is the parameter its
guidance says it is.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt
import pytest

from sieve.core.types import ChannelSpec, Frame, FrameCount
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
    """Feed a `(frames, ny, nx)` series through one run and keep every output."""
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
    """A noisy null with `amplitude` added to one cell over `event_at`."""
    rng = np.random.default_rng(seed)
    series = rng.normal(1.0, 0.1, size=(frames, NY, NX))
    series[event_at, 3, 4] += amplitude
    return series


def test_the_deviation_is_unchanged_by_a_gain_and_an_offset() -> None:
    """The load-bearing claim, and the reason the filter exists.

    Two replicates under two backlights differ, to first order, by a gain and an
    offset on every pixel — a brighter lamp and a different substrate. If a
    threshold is to transfer between them, the number being thresholded must not
    move under that transform. Raw `change_energy` moves by the gain squared;
    this asserts the standardized signal does not move at all.

    Median and MAD are both affine-equivariant, so the invariance is exact up to
    float32 — including for the degenerate cell this fixture carries, which is
    constant across its whole window and therefore has a MAD of exactly zero.
    That cell is the point: the obvious repair for a zero denominator is a
    constant floor, and a constant does not scale with the gain, so a floored
    implementation reads the same event seven times larger under a brighter
    lamp. `_floored` borrows the frame's own spread instead, which does scale.
    """
    params = TemporalBaselineParams(window_seconds=4.0, fps=FPS)
    series = quiet_with_event(200, slice(150, 151), amplitude=3.0)
    # A cell with no variation at all, and an event on it at the same frame.
    series[:, 0, 0] = 5.0
    series[150, 0, 0] += 3.0

    plain = run(series, params)[150]
    relit = run(series * 7.0 + 2.0, params)[150]

    assert np.allclose(plain, relit, rtol=1e-3, atol=1e-3)
    # And it is not invariant because it is uniformly zero: both the ordinary
    # cell and the degenerate one report their event.
    assert plain[3, 4] > 10.0
    assert plain[0, 0] > 10.0


def test_events_do_not_inflate_the_spread_they_are_measured_against() -> None:
    """Robust statistics are the choice, not an implementation detail.

    A fifth of the window is event, which is the regime the filter is built for:
    an animal that grooms in bouts is *in* its own baseline sample. The mean and
    standard deviation move with those events, so each one is measured against a
    spread it created — a detector that gets less sensitive exactly where there
    is more to detect. The test computes what the non-robust denominator would
    have said and asserts the gap, rather than asserting a number, because the
    number is a fact about this fixture and the gap is the claim.
    """
    params = TemporalBaselineParams(window_seconds=4.0, fps=FPS)
    span = window_frames(4.0, FPS)
    # The bout ends at `last`, so the window behind it is a fifth event and
    # four fifths null — the mixture whose spread the two estimators disagree
    # about. Placed well past the first full window so nothing here is about
    # warmup.
    last = 3 * span
    series = quiet_with_event(4 * span, slice(last - span // 5 + 1, last + 1), amplitude=2.0)

    measured = float(run(series, params)[last][3, 4])

    window = series[last - span + 1 : last + 1, 3, 4]
    non_robust = (window[-1] - window.mean()) / window.std()

    assert measured > 15.0
    assert non_robust < 3.0


def test_a_bout_longer_than_the_window_disappears_into_its_own_baseline() -> None:
    """`window_seconds` has no correct value, and this is why.

    The guidance tells a user to set the window to several times the longest
    bout they want to detect, and this is the failure that rule avoids: once the
    window holds nothing but the behaviour, the behaviour *is* the median and
    the deviation falls back to zero while it is still happening. The detector
    goes quiet in the middle of the event it was built for, which looks exactly
    like nothing happening — and is why `emit=baseline` exists.

    A test that only checked "an event produces a large deviation" would pass
    with the window parameter ignored entirely. This one fails unless the window
    is both read and applied as a span.
    """
    bout = slice(600, 690)
    series = quiet_with_event(800, bout, amplitude=2.0)
    mid_bout = 660

    swallowed = run(series, TemporalBaselineParams(window_seconds=1.0, fps=FPS))[mid_bout]
    survives = run(series, TemporalBaselineParams(window_seconds=20.0, fps=FPS))[mid_bout]

    assert abs(float(swallowed[3, 4])) < 3.0
    assert float(survives[3, 4]) > 15.0


def test_the_declared_warmup_is_the_worst_case_over_the_legal_range() -> None:
    """The bound is reached only at the corner, and every run pays less.

    The failure this closes is a bound that stops being one: relaxing
    `WINDOW_SECONDS_MAX` or `FPS_MAX` is a one-line edit, and a spec still
    declaring the old product would let a configuration ask for more lead-in
    than it admits — which `node_warmup_frames` refuses at run time, turning a
    silent under-warm into a crash but only for the user who found it.
    """
    corner = TemporalBaselineParams(window_seconds=WINDOW_SECONDS_MAX, fps=FPS_MAX)
    assert corner.warmup_frames() == SPEC.warmup_frames

    default = TemporalBaselineParams()
    assert default.warmup_frames() == FrameCount(
        window_frames(default.window_seconds, default.fps) - 1
    )
    assert default.warmup_frames() * 40 < SPEC.warmup_frames

    with pytest.raises(ValueError):
        TemporalBaselineParams(window_seconds=WINDOW_SECONDS_MAX * 2)
    with pytest.raises(ValueError):
        TemporalBaselineParams(fps=FPS_MAX * 2)


def test_a_strided_ring_still_spans_the_whole_window() -> None:
    """Sampling the window is not the same as shortening it, and this says so.

    A 30 s window at 30 fps is 900 frames held in 225 samples at a stride of 4.
    The temptation — and what a ring without a stride would do — is to keep the
    most recent `MAX_SAMPLES` frames instead, which silently turns a 30 s window
    into a 7.5 s one: the parameter the user set, the lead-in the planner
    decoded, and the span actually measured over would all be three different
    numbers, and nothing downstream would look wrong.

    A ramp is the fixture that can tell them apart, because on a ramp the median
    *is* the midpoint of whatever span was used. This also covers the memory
    bound: the assertion below is only reachable if the stride kept the ring
    under the cap.
    """
    params = TemporalBaselineParams(window_seconds=30.0, fps=FPS, emit=Emit.BASELINE)
    span = window_frames(30.0, FPS)
    frames = 1200
    ramp = np.arange(frames, dtype=np.float64)[:, None, None] * np.ones((1, NY, NX))

    baseline = float(run(ramp, params)[-1].mean())

    assert baseline == pytest.approx(frames - 1 - span / 2, abs=span / 30)
    # What keeping only the newest `MAX_SAMPLES` frames would have said.
    assert abs(baseline - (frames - 1 - MAX_SAMPLES / 2)) > span / 4


def test_a_mid_run_shape_change_is_refused_rather_than_resized() -> None:
    """A silent resize would restart the window with nobody told."""
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
