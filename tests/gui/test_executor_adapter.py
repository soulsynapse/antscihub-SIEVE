"""The bus-to-Qt bridge, which is a claim about threads and not about signals.

Re-emitting a `Sample` is one line and needs no test. What needs one is that the
sample arrives *somewhere it is legal to touch a widget from*, and that it does
so by the same route regardless of who published — because the two failures
either way are silent. A sample delivered on a publisher's thread crashes under
load and passes every assertion about its contents; a sample delivered directly
when the publisher happened to be the GUI thread reorders it against the queued
ones and shows up as a HUD that is occasionally one render ahead of itself.

The recorded `QThread` is the observable in both. There is no other way to ask
the question — the payload is identical whichever thread carried it.
"""

from __future__ import annotations

from collections.abc import Iterator
from threading import Thread

import pytest
from PySide6.QtCore import QCoreApplication, QThread
from pytestqt.qtbot import QtBot

from sieve.bench.metrics import MetricBus, Sample
from sieve.gui.executor_adapter import ExecutorAdapter

pytestmark = pytest.mark.gui

DELIVERY_TIMEOUT_MS = 5000

#: A key whose ceiling is high enough that an ordinary number is within it, and
#: whose limit a test can go over deliberately. 100 ms.
KEY = "slider_to_preview"
OVER_MS = 5000.0


class Landings:
    """Every sample the adapter emitted, with the thread it emitted on."""

    def __init__(self, adapter: ExecutorAdapter) -> None:
        self.samples: list[Sample] = []
        self.threads: list[QThread | None] = []
        self.missed: list[Sample] = []
        adapter.sample.connect(self._on_sample)
        adapter.missed.connect(self.missed.append)

    def _on_sample(self, sample: Sample) -> None:
        self.samples.append(sample)
        self.threads.append(QThread.currentThread())


@pytest.fixture
def bus() -> MetricBus:
    """A bus of this test's own, so nothing else in the process is heard."""
    return MetricBus()


@pytest.fixture
def adapter(qapp: object, bus: MetricBus) -> Iterator[ExecutorAdapter]:
    del qapp
    instance = ExecutorAdapter(bus)
    yield instance
    instance.close()
    instance.deleteLater()


def gui_thread() -> QThread | None:
    """The thread Qt considers the GUI one, which is the application's own."""
    application = QCoreApplication.instance()
    assert application is not None
    return application.thread()


class TestThreadHop:
    def test_a_sample_published_off_the_gui_thread_arrives_on_it(
        self, qtbot: QtBot, bus: MetricBus, adapter: ExecutorAdapter
    ) -> None:
        """The reason this module exists.

        `preview_runner.py` publishes from its render thread and the decode
        thread will publish too. Without the relay the subscriber's emit runs
        there, every slot connected to it runs there, and the first one that
        touches a widget is undefined behaviour that no assertion about the
        sample's contents would notice.
        """
        landings = Landings(adapter)

        publisher = Thread(target=lambda: bus.publish(KEY, 12.0), name="test-publisher")
        publisher.start()
        publisher.join()

        qtbot.waitUntil(lambda: bool(landings.samples), timeout=DELIVERY_TIMEOUT_MS)
        assert landings.threads == [gui_thread()]
        assert landings.samples[0].key == KEY
        assert landings.samples[0].elapsed_ms == 12.0
        assert landings.missed == [], "a sample inside its ceiling is not a miss"

    def test_a_sample_published_on_the_gui_thread_is_still_queued(
        self, qtbot: QtBot, bus: MetricBus, adapter: ExecutorAdapter
    ) -> None:
        """One delivery rule, not one per publishing thread.

        `AutoConnection` would deliver this one synchronously and the one above
        by queue, so the order two samples arrive in would depend on which
        thread produced each — and `gui/transport/player.py` publishing
        `scrub_to_repaint` from a GUI-thread slot makes that a real mixture
        rather than a hypothetical one. The explicit `QueuedConnection` is what
        this pins, and the observable is that nothing has arrived yet on the
        line after the publish.
        """
        landings = Landings(adapter)

        bus.publish(KEY, 12.0)
        assert landings.samples == [], "delivery was synchronous"

        qtbot.waitUntil(lambda: bool(landings.samples), timeout=DELIVERY_TIMEOUT_MS)
        assert landings.threads == [gui_thread()]

    def test_an_over_budget_sample_is_announced_separately(
        self, qtbot: QtBot, bus: MetricBus, adapter: ExecutorAdapter
    ) -> None:
        """Both signals, once each — not a miss that skips the ordinary series."""
        landings = Landings(adapter)

        bus.publish(KEY, OVER_MS)
        qtbot.waitUntil(lambda: bool(landings.samples), timeout=DELIVERY_TIMEOUT_MS)

        assert len(landings.samples) == 1
        assert landings.missed == landings.samples


class TestClose:
    def test_closing_stops_delivery(
        self, qtbot: QtBot, bus: MetricBus, adapter: ExecutorAdapter
    ) -> None:
        """The subscription outlives the QObject unless something drops it.

        The bus holds `_receive` — a bound method of a widget's child — so an
        adapter that is merely dropped leaves the bus emitting into an object
        Qt may already have deleted. `close` is what a window's teardown calls,
        and a second call from a `finally` must not be an error.
        """
        landings = Landings(adapter)
        adapter.close()
        adapter.close()

        bus.publish(KEY, 12.0)
        qtbot.wait(100)
        assert landings.samples == []
