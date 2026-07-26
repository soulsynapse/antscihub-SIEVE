"""Invariants of `ScrubPolicy.snap` across every grid the policy can build.

The grid spacing is a product of source frame rate and a user preference, so
the example tests can only ever pin a few of the strides that ship. What has
to hold for all of them is that snapping settles: a drag target that has
already been snapped must not move again, or the cache the whole degradation
strategy depends on never gets a second hit.
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from sieve.gui.scrub_policy import SAMPLE_WINDOW, ScrubMode, ScrubPolicy

BUDGET_MS = 100.0

#: Real footage frame rates, plus the extremes a container can misreport.
FPS = st.floats(min_value=0.1, max_value=1000.0, allow_nan=False, allow_infinity=False)

#: `set_coarse_interval_seconds` floors at 0.0, and `stride` floors at 1 frame,
#: so sub-frame intervals are a case the policy claims to handle.
INTERVAL_SECONDS = st.floats(min_value=0.0, max_value=60.0, allow_nan=False, allow_infinity=False)

#: Frame indices. Bounded by a decade of footage rather than by `int`.
INDEX = st.integers(min_value=0, max_value=10_000_000)


def degraded_policy(fps: float, interval_seconds: float) -> ScrubPolicy:
    """A policy already in coarse mode, by the only route that gets it there."""
    policy = ScrubPolicy(BUDGET_MS, coarse_interval_seconds=interval_seconds)
    policy.set_fps(fps)
    for _ in range(SAMPLE_WINDOW):
        policy.observe(BUDGET_MS * 10.0)
    assert policy.mode is ScrubMode.COARSE
    return policy


@given(fps=FPS, interval_seconds=INTERVAL_SECONDS, index=INDEX)
def test_snap_is_idempotent(fps: float, interval_seconds: float, index: int) -> None:
    """Snapping a snapped target is a no-op — the property the cache rests on.

    A drag that revisits a grid point must ask for the identical frame index
    it asked for last time. If snapping drifted by even one frame per pass the
    coarse grid would miss the cache exactly as often as exact scrubbing does,
    and degrading would buy nothing.
    """
    policy = degraded_policy(fps, interval_seconds)
    snapped = policy.snap(index)

    assert policy.snap(snapped) == snapped


@given(fps=FPS, interval_seconds=INTERVAL_SECONDS, index=INDEX)
def test_snap_lands_on_the_grid_within_half_a_stride(
    fps: float, interval_seconds: float, index: int
) -> None:
    """The grid is real, and the frame shown is the nearest point on it.

    Half a stride is the error bound the module docstring promises the user
    ("never more than half a second from the cursor" at the default interval).
    """
    policy = degraded_policy(fps, interval_seconds)
    snapped = policy.snap(index)

    assert snapped >= 0
    assert snapped % policy.stride == 0
    assert abs(snapped - index) * 2 <= policy.stride


@given(fps=FPS, interval_seconds=INTERVAL_SECONDS, index=INDEX)
def test_snap_is_the_identity_until_the_policy_degrades(
    fps: float, interval_seconds: float, index: int
) -> None:
    """A machine that keeps up never has a target moved out from under it."""
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
    """No sequence of observed latencies can degrade a policy the user pinned."""
    policy = ScrubPolicy(BUDGET_MS, coarse_interval_seconds=interval_seconds, allow_degrade=False)
    policy.set_fps(fps)
    for latency in latencies:
        assert policy.observe(latency) is False

    assert policy.snap(index) == index
