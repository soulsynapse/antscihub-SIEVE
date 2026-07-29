








from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from sieve.gui.scrub_policy import SAMPLE_WINDOW, ScrubMode, ScrubPolicy

BUDGET_MS = 100.0


FPS = st.floats(min_value=0.1, max_value=1000.0, allow_nan=False, allow_infinity=False)



INTERVAL_SECONDS = st.floats(min_value=0.0, max_value=60.0, allow_nan=False, allow_infinity=False)


INDEX = st.integers(min_value=0, max_value=10_000_000)


def degraded_policy(fps: float, interval_seconds: float) -> ScrubPolicy:

    policy = ScrubPolicy(BUDGET_MS, coarse_interval_seconds=interval_seconds)
    policy.set_fps(fps)
    for _ in range(SAMPLE_WINDOW):
        policy.observe(BUDGET_MS * 10.0)
    assert policy.mode is ScrubMode.COARSE
    return policy


@given(fps=FPS, interval_seconds=INTERVAL_SECONDS, index=INDEX)
def test_snap_is_idempotent(fps: float, interval_seconds: float, index: int) -> None:







    policy = degraded_policy(fps, interval_seconds)
    snapped = policy.snap(index)

    assert policy.snap(snapped) == snapped


@given(fps=FPS, interval_seconds=INTERVAL_SECONDS, index=INDEX)
def test_snap_lands_on_the_grid_within_half_a_stride(
    fps: float, interval_seconds: float, index: int
) -> None:





    policy = degraded_policy(fps, interval_seconds)
    snapped = policy.snap(index)

    assert snapped >= 0
    assert snapped % policy.stride == 0
    assert abs(snapped - index) * 2 <= policy.stride


@given(fps=FPS, interval_seconds=INTERVAL_SECONDS, index=INDEX)
def test_snap_is_the_identity_until_the_policy_degrades(
    fps: float, interval_seconds: float, index: int
) -> None:

    policy = ScrubPolicy(BUDGET_MS, coarse_interval_seconds=interval_seconds)
    policy.set_fps(fps)

    assert policy.snap(index) == index


@given(
    fps=FPS,
    interval_seconds=INTERVAL_SECONDS,
    index=INDEX,
    latencies=st.lists(st.floats(min_value=0.0, max_value=10_000.0), max_size=SAMPLE_WINDOW * 4),
)
def test_snap_is_the_identity_whenever_degradation_is_forbidden(
    fps: float, interval_seconds: float, index: int, latencies: list[float]
) -> None:

    policy = ScrubPolicy(BUDGET_MS, coarse_interval_seconds=interval_seconds, allow_degrade=False)
    policy.set_fps(fps)
    for latency in latencies:
        assert policy.observe(latency) is False

    assert policy.snap(index) == index
