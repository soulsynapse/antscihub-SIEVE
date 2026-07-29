













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



KEY = "slider_to_preview"
OVER_MS = 5000.0


class Landings:


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

    return MetricBus()


@pytest.fixture
def adapter(qapp: object, bus: MetricBus) -> Iterator[ExecutorAdapter]:
    del qapp
    instance = ExecutorAdapter(bus)
    yield instance
    instance.close()
    instance.deleteLater()


def gui_thread() -> QThread | None:

    application = QCoreApplication.instance()
    assert application is not None
    return application.thread()


class TestThreadHop:
    def test_a_sample_published_off_the_gui_thread_arrives_on_it(
        self, qtbot: QtBot, bus: MetricBus, adapter: ExecutorAdapter
    ) -> None:








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










        landings = Landings(adapter)

        bus.publish(KEY, 12.0)
        assert landings.samples == [], "delivery was synchronous"

        qtbot.waitUntil(lambda: bool(landings.samples), timeout=DELIVERY_TIMEOUT_MS)
        assert landings.threads == [gui_thread()]

    def test_an_over_budget_sample_is_announced_separately(
        self, qtbot: QtBot, bus: MetricBus, adapter: ExecutorAdapter
    ) -> None:

        landings = Landings(adapter)

        bus.publish(KEY, OVER_MS)
        qtbot.waitUntil(lambda: bool(landings.samples), timeout=DELIVERY_TIMEOUT_MS)

        assert len(landings.samples) == 1
        assert landings.missed == landings.samples


class TestClose:
    def test_closing_stops_delivery(
        self, qtbot: QtBot, bus: MetricBus, adapter: ExecutorAdapter
    ) -> None:







        landings = Landings(adapter)
        adapter.close()
        adapter.close()

        bus.publish(KEY, 12.0)
        qtbot.wait(100)
        assert landings.samples == []
