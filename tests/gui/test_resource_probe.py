"""The probe's three load-bearing claims.

One: a tick publishes a real sample — RSS from the sampler thread, the ledger
ceiling from `concurrency`, the mode from the callable, and one reading per
row in `concurrency.SENSED` — which is also what pins `SENSED` to what the
probe actually publishes rather than leaving it a free-floating declaration.
Two: utilisation is the busy-time *difference* over the interval, denominated
in the pool's width. Three: a refused memory reading is published as a refusal,
never dropped and never rendered as a number (rule 6, both by the probe and by
the HUD line that draws it).
"""

from __future__ import annotations

import pytest
from pytestqt.qtbot import QtBot

from sieve.core.machine import MemoryUnreadableError
from sieve.core.pool_meter import PoolMeter
from sieve.gui.concurrency import SENSED, WorkerSplit, ledger_ceiling
from sieve.gui.graph_hud import GraphHud
from sieve.gui.resource_probe import MODE_PLAYBACK, ResourceProbe, ResourceSample

pytestmark = pytest.mark.gui

SPLIT = WorkerSplit(player=1, preview=2, detector=2)


def _meters() -> dict[str, PoolMeter]:
    return {name: PoolMeter() for name in ("player", "preview", "detector")}


def _collector(probe: ResourceProbe) -> list[ResourceSample]:
    """Everything the probe publishes, typed on the way in.

    pytest-qt's `blocker.args` is untyped; a slot of our own is what lets the
    assertions below say `ResourceSample` and mean it.
    """
    samples: list[ResourceSample] = []

    def collect(sample: object) -> None:
        assert isinstance(sample, ResourceSample)
        samples.append(sample)

    probe.sample.connect(collect)
    return samples


def _one_sample(qtbot: QtBot, probe: ResourceProbe) -> ResourceSample:
    samples = _collector(probe)
    with qtbot.waitSignal(probe.sample, timeout=5000):
        pass
    assert samples
    return samples[-1]


def test_a_tick_publishes_the_whole_resource_side(qtbot: QtBot) -> None:
    probe = ResourceProbe(_meters(), lambda: MODE_PLAYBACK, interval_ms=20, split=SPLIT)
    try:
        sample = _one_sample(qtbot, probe)
    finally:
        probe.shutdown()

    assert sample.mode == MODE_PLAYBACK
    assert sample.rss_bytes is not None and sample.rss_bytes > 0
    assert sample.ledger_bytes == ledger_ceiling()
    # SENSED is pinned to what is actually published, not merely declared.
    assert {pool.name for pool in sample.pools} == set(SENSED)
    assert all(0.0 <= pool.utilisation <= 1.0 for pool in sample.pools)


def test_utilisation_is_the_interval_difference_over_the_pool_width(qtbot: QtBot) -> None:
    """A pool busy before the probe existed must not read as busy now, and a
    two-worker pool with roughly one worker's worth of busy time reads ~0.5."""
    meters = _meters()
    meters["player"].add_busy_ns(10**12)  # history from before the first tick
    probe = ResourceProbe(meters, lambda: MODE_PLAYBACK, interval_ms=50, split=SPLIT)
    try:
        samples = _collector(probe)
        first = _one_sample(qtbot, probe)
        # Half the two-worker preview pool's capacity for the next interval,
        # fed before the wait so the next tick's difference contains it.
        meters["preview"].add_busy_ns(50 * 10**6)
        with qtbot.waitSignal(probe.sample, timeout=5000):
            pass
        second = samples[-1]
    finally:
        probe.shutdown()

    by_name = {pool.name: pool for pool in first.pools}
    # The pre-existing 1000 s of busy time is history, not this interval.
    assert by_name["player"].utilisation == 0.0

    preview = {pool.name: pool for pool in second.pools}["preview"]
    # 50 ms of busy over a ~50 ms interval on a two-worker pool: about half.
    # The lower bound is loose because ticks skip while the sampler is out and
    # the interval is a floor, not an exact width — what is pinned is that the
    # denominator is `wall x workers` (so ≤ ~0.5 here, never ~1.0) and that
    # history before the interval does not count (the player assertion above).
    assert 0.05 <= preview.utilisation <= 0.75


def test_a_refused_reading_is_published_as_a_refusal(qtbot: QtBot) -> None:
    def refuse() -> int:
        raise MemoryUnreadableError("a worker exited mid-sample")

    probe = ResourceProbe(
        _meters(), lambda: MODE_PLAYBACK, interval_ms=20, read_memory=refuse, split=SPLIT
    )
    try:
        sample = _one_sample(qtbot, probe)
    finally:
        probe.shutdown()

    assert sample.rss_bytes is None
    assert sample.over_ledger is None

    # And the HUD line renders the refusal in words, flagged — never a zero.
    hud = GraphHud()
    qtbot.addWidget(hud)
    hud.show_resources(sample)
    line, flagged = hud.resource_line()
    assert "unreadable" in line
    assert "0.0/" not in line
    assert flagged
