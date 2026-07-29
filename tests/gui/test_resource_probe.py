











from __future__ import annotations

import pytest
from pytestqt.qtbot import QtBot

from sieve.core.machine import MemoryUnreadableError
from sieve.core.pool_meter import PoolMeter
from sieve.core.shares import SENSED, WorkerSplit, ledger_ceiling
from sieve.gui.graph_hud import GraphHud
from sieve.gui.resource_probe import MODE_PLAYBACK, ResourceProbe, ResourceSample

pytestmark = pytest.mark.gui

SPLIT = WorkerSplit(player=1, preview=2, detector=2)


def _meters() -> dict[str, PoolMeter]:
    return {name: PoolMeter() for name in ("player", "preview", "detector")}


def _collector(probe: ResourceProbe) -> list[ResourceSample]:





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

    assert {pool.name for pool in sample.pools} == set(SENSED)
    assert all(0.0 <= pool.utilisation <= 1.0 for pool in sample.pools)


def test_utilisation_is_the_interval_difference_over_the_pool_width(qtbot: QtBot) -> None:


    meters = _meters()
    meters["player"].add_busy_ns(10**12)
    probe = ResourceProbe(meters, lambda: MODE_PLAYBACK, interval_ms=50, split=SPLIT)
    try:
        samples = _collector(probe)
        first = _one_sample(qtbot, probe)


        meters["preview"].add_busy_ns(50 * 10**6)
        with qtbot.waitSignal(probe.sample, timeout=5000):
            pass
        second = samples[-1]
    finally:
        probe.shutdown()

    by_name = {pool.name: pool for pool in first.pools}

    assert by_name["player"].utilisation == 0.0

    preview = {pool.name: pool for pool in second.pools}["preview"]





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


    hud = GraphHud()
    qtbot.addWidget(hud)
    hud.show_resources(sample)
    line, flagged = hud.resource_line()
    assert "unreadable" in line
    assert "0.0/" not in line
    assert flagged
