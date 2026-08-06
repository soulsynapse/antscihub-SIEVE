"""The meter's three load-bearing claims, each falsifiable a distinct way.

The counter is what `gui/resource_probe.py` differences into a utilisation
number, so what matters is that it accumulates exactly what the clock says the
blocks took, that a block which raises is still accounted (occupancy, not
achievement — the deliberate opposite of `MetricBus.measure`), and that the
depth gauge is a gauge rather than a total.
"""

from __future__ import annotations

import pytest

from sieve.mutual.pool_meter import PoolMeter


class FakeClock:
    """A clock a test advances by hand, in nanoseconds."""

    def __init__(self) -> None:
        self.now = 0

    def __call__(self) -> int:
        return self.now

    def advance(self, ns: int) -> None:
        self.now += ns


def test_working_accumulates_what_the_clock_says() -> None:
    clock = FakeClock()
    meter = PoolMeter(clock=clock)
    with meter.working():
        clock.advance(7_000)
    with meter.working():
        clock.advance(5_000)
    assert meter.busy_ns == 12_000


def test_a_block_that_raises_is_still_busy_time() -> None:
    """Occupancy, not achievement: a failed decode still held a worker."""
    clock = FakeClock()
    meter = PoolMeter(clock=clock)
    with pytest.raises(RuntimeError), meter.working():
        clock.advance(9_000)
        raise RuntimeError("decode failed")
    assert meter.busy_ns == 9_000


def test_depth_is_a_gauge_not_a_total() -> None:
    meter = PoolMeter()
    meter.set_depth(3)
    meter.set_depth(1)
    assert meter.depth == 1
