"""`ScrubPolicy` decides when scrubbing stops being exact. Fed numbers, not a GUI.

The point of the policy being Qt-free is that its whole contract can be
exercised by handing it latencies, which is why these are unit tests and not
pytest-qt ones.
"""

from __future__ import annotations

import pytest

from sieve.gui.transport.scrub_policy import (
    FALLBACK_FPS,
    SAMPLE_WINDOW,
    ScrubMode,
    ScrubPolicy,
)

BUDGET_MS = 100.0


@pytest.fixture
def policy() -> ScrubPolicy:
    policy = ScrubPolicy(BUDGET_MS, coarse_interval_seconds=1.0)
    policy.set_fps(60.0)
    return policy


def degrade(policy: ScrubPolicy, latency_ms: float = 300.0) -> list[bool]:
    """Feed a full window of `latency_ms`, returning what each call reported."""
    return [policy.observe(latency_ms) for _ in range(SAMPLE_WINDOW)]


class TestStartsExact:
    def test_mode_is_exact_before_any_evidence(self, policy: ScrubPolicy) -> None:
        assert policy.mode is ScrubMode.EXACT
        assert not policy.is_degraded

    def test_exact_mode_returns_the_index_untouched(self, policy: ScrubPolicy) -> None:
        assert policy.snap(1234) == 1234


class TestDegradation:
    def test_a_full_window_over_budget_degrades(self, policy: ScrubPolicy) -> None:
        degrade(policy)
        assert policy.is_degraded

    def test_it_reports_the_transition_exactly_once(self, policy: ScrubPolicy) -> None:
        assert degrade(policy) == [False] * (SAMPLE_WINDOW - 1) + [True]
        assert policy.observe(300.0) is False

    def test_a_partial_window_is_not_enough(self, policy: ScrubPolicy) -> None:
        for _ in range(SAMPLE_WINDOW - 1):
            assert policy.observe(300.0) is False
        assert not policy.is_degraded

    def test_one_slow_seek_among_fast_ones_is_outvoted(self, policy: ScrubPolicy) -> None:
        # The measured tail on the reference source: a single 226 ms outlier in
        # an otherwise healthy window must not change what a drag means.
        for latency in (40.0, 45.0, 226.0, 38.0, 44.0):
            policy.observe(latency)
        assert not policy.is_degraded

    def test_latency_exactly_at_budget_does_not_degrade(self, policy: ScrubPolicy) -> None:
        degrade(policy, BUDGET_MS)
        assert not policy.is_degraded

    def test_the_window_slides(self, policy: ScrubPolicy) -> None:
        for _ in range(20):
            policy.observe(10.0)
        assert not policy.is_degraded
        degrade(policy)
        assert policy.is_degraded


class TestSnapping:
    def test_coarse_mode_snaps_to_the_nearest_grid_point(self, policy: ScrubPolicy) -> None:
        degrade(policy)
        assert policy.stride == 60
        assert policy.snap(1210) == 1200  # nearer the grid point below
        assert policy.snap(1234) == 1260  # nearer the one above

    def test_snapping_never_returns_a_negative_index(self, policy: ScrubPolicy) -> None:
        degrade(policy)
        assert policy.snap(0) == 0
        assert policy.snap(5) == 0

    def test_the_interval_sets_the_stride(self, policy: ScrubPolicy) -> None:
        policy.set_coarse_interval_seconds(0.5)
        assert policy.stride == 30

    def test_stride_is_at_least_one_frame(self, policy: ScrubPolicy) -> None:
        policy.set_coarse_interval_seconds(0.0)
        degrade(policy)
        # A zero-frame grid would make snapping undefined; it collapses to exact.
        assert policy.stride == 1
        assert policy.snap(777) == 777

    def test_unusable_fps_falls_back(self, policy: ScrubPolicy) -> None:
        policy.set_fps(0.0)
        assert policy.stride == round(FALLBACK_FPS)


class TestUserOverride:
    def test_forbidding_degradation_prevents_it(self, policy: ScrubPolicy) -> None:
        policy.set_allow_degrade(False)
        degrade(policy)
        assert not policy.is_degraded

    def test_forbidding_it_afterwards_restores_exact_immediately(self, policy: ScrubPolicy) -> None:
        degrade(policy)
        policy.set_allow_degrade(False)
        assert policy.mode is ScrubMode.EXACT
        assert policy.snap(1234) == 1234

    def test_re_allowing_it_needs_fresh_evidence(self, policy: ScrubPolicy) -> None:
        degrade(policy)
        policy.set_allow_degrade(False)
        policy.set_allow_degrade(True)
        assert not policy.is_degraded
        assert policy.observe(300.0) is False  # window was cleared


class TestReset:
    def test_reset_returns_to_exact(self, policy: ScrubPolicy) -> None:
        degrade(policy)
        policy.reset()
        assert policy.mode is ScrubMode.EXACT

    def test_reset_clears_the_evidence(self, policy: ScrubPolicy) -> None:
        for _ in range(SAMPLE_WINDOW - 1):
            policy.observe(300.0)
        policy.reset()
        assert policy.observe(300.0) is False
