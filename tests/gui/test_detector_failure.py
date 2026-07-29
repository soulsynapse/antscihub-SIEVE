





















from __future__ import annotations

from collections.abc import Iterator

import numpy as np
import pytest
from pytestqt.qtbot import QtBot

from sieve.bench.metrics import MetricBus
from sieve.gui.chain_model import DetectorState
from sieve.gui.detector_worker import DetectorFailure, DetectorRequest, DetectorRunner
from sieve.gui.document import ReplicateDocument
from sieve.gui.filter_tab import FilterTab
from sieve.gui.player import VideoPlayer
from sieve.gui.preview_runner import PreviewRunner

pytestmark = pytest.mark.gui

WAIT_MS = 5000


def request_over(series: np.ndarray, *, revision: int = 0) -> DetectorRequest:
    return DetectorRequest(
        revision=revision,
        series=series,
        start_index=0,
        fps=30.0,
        state=DetectorState(),
        final=True,
    )






EMPTY_SERIES = np.zeros((0, 2, 2), np.float32)


class TestAFailedPassIsReportedRatherThanSwallowed:
    @pytest.fixture
    def runner(self, qapp: object) -> Iterator[DetectorRunner]:
        del qapp
        instance = DetectorRunner()
        yield instance
        instance.shutdown()

    def test_a_raising_derivation_arrives_as_a_failure_with_something_to_say(
        self, qtbot: QtBot, runner: DetectorRunner
    ) -> None:



        caught: list[object] = []
        runner.failed.connect(caught.append)
        with qtbot.waitSignal(runner.failed, timeout=WAIT_MS):
            runner.submit(request_over(EMPTY_SERIES))
        failure = caught[0]
        assert isinstance(failure, DetectorFailure)
        assert failure.revision == 0


        assert failure.message.strip()

    def test_the_in_flight_slot_is_freed_by_a_failure(
        self, qtbot: QtBot, runner: DetectorRunner
    ) -> None:






        with qtbot.waitSignal(runner.failed, timeout=WAIT_MS):
            runner.submit(request_over(EMPTY_SERIES))
        assert not runner.busy

        good = np.random.default_rng(1).random((24, 2, 2)).astype(np.float32)
        with qtbot.waitSignal(runner.ready, timeout=WAIT_MS):
            runner.submit(request_over(good))


class TestTheTabSaysSoOnTheGraph:
    @pytest.fixture
    def player(self, qapp: object) -> Iterator[VideoPlayer]:
        del qapp
        instance = VideoPlayer()
        yield instance
        instance.shutdown()

    @pytest.fixture
    def preview(self, qapp: object) -> Iterator[PreviewRunner]:
        del qapp
        instance = PreviewRunner(metrics=MetricBus())
        yield instance
        instance.shutdown()

    @pytest.fixture
    def tab(
        self,
        qtbot: QtBot,
        player: VideoPlayer,
        document: ReplicateDocument,
        preview: PreviewRunner,
    ) -> Iterator[FilterTab]:
        instance = FilterTab(player, document, preview, metrics=MetricBus())
        qtbot.addWidget(instance)
        yield instance
        instance.shutdown()

    def test_the_notice_names_the_failure_and_survives_a_repaint(self, tab: FilterTab) -> None:







        failure = DetectorFailure(revision=0, message="MemoryError: nope")
        tab._on_detector_failed(failure)
        assert "MemoryError: nope" in tab._count.notice

        tab._apply()
        assert "MemoryError: nope" in tab._count.notice
