




























from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from threading import get_ident
from time import sleep

import numpy as np
import pytest
from pytestqt.qtbot import QtBot

from sieve.backend.dispatch import Backend, KernelRegistry, kernel
from sieve.bench.metrics import MetricBus, Recorder
from sieve.core.filter_base import ArraySpec, CostEstimate, ElementRelation, ParamsBase
from sieve.core.filter_registry import FilterRegistry, register_filter
from sieve.core.pipeline_model import ClipRange, Node, Pipeline
from sieve.core.types import Frame
from sieve.gui.preview_runner import FIRST_TICK_BUDGET, PreviewRunner
from sieve.pipeline.executor import FrameResult

pytestmark = pytest.mark.gui

OPEN_TIMEOUT_MS = 10_000
RENDER_TIMEOUT_MS = 30_000



WINDOW = ClipRange(start=0, end=12)




SLOW_FRAME_SECONDS = 0.015


class Landings:


    def __init__(self, runner: PreviewRunner) -> None:
        self.costs: list[tuple[int, float]] = []
        self.starts: list[int] = []
        self.finished: list[object] = []
        self.failures: list[str] = []
        runner.frame_cost.connect(self._on_cost)
        runner.render_started.connect(self.starts.append)
        runner.render_finished.connect(self.finished.append)
        runner.render_failed.connect(self.failures.append)

    def _on_cost(self, index: int, elapsed_ms: float) -> None:
        self.costs.append((index, elapsed_ms))

    @property
    def indices(self) -> list[int]:
        return [index for index, _ in self.costs]


def downsampling() -> Pipeline:

    node = Node(node_id="small", filter_id="downsample", version="1.0.0", params={"factor": 2})
    return Pipeline(nodes=(node,))


def opened_runner(
    qtbot: QtBot,
    video: Path,
    *,
    metrics: MetricBus | None = None,
    shelves: tuple[FilterRegistry, KernelRegistry] | None = None,
) -> PreviewRunner:

    filters, kernels = shelves if shelves is not None else (None, None)
    runner = PreviewRunner(metrics=metrics, registry=filters, kernels=kernels)
    runner.open(video)
    qtbot.waitUntil(lambda: runner.is_open, timeout=OPEN_TIMEOUT_MS)
    return runner


@pytest.fixture
def runner(qtbot: QtBot, qapp: object, synthetic_video: Path) -> Iterator[PreviewRunner]:
    del qapp
    instance = opened_runner(qtbot, synthetic_video)
    yield instance
    instance.shutdown()


class TestTheFirstTick:
    def test_a_render_reports_every_frame_and_publishes_the_first_tick(
        self, qtbot: QtBot, qapp: object, synthetic_video: Path
    ) -> None:








        del qapp
        bus = MetricBus()
        recorder = Recorder()
        bus.subscribe(recorder.record)
        instance = opened_runner(qtbot, synthetic_video, metrics=bus)
        landings = Landings(instance)

        try:
            assert instance.request_render(downsampling(), WINDOW)
            qtbot.waitUntil(lambda: bool(landings.finished), timeout=RENDER_TIMEOUT_MS)

            assert landings.failures == []
            assert landings.indices == list(range(WINDOW.start, WINDOW.end))
            assert all(ms > 0.0 for _, ms in landings.costs)


            assert instance.has_ticked
        finally:
            instance.shutdown()





        assert len(recorder.samples(FIRST_TICK_BUDGET)) == 1

    def test_a_second_render_does_not_tick_again(
        self, qtbot: QtBot, qapp: object, synthetic_video: Path
    ) -> None:







        del qapp
        bus = MetricBus()
        recorder = Recorder()
        bus.subscribe(recorder.record)
        instance = opened_runner(qtbot, synthetic_video, metrics=bus)
        landings = Landings(instance)

        try:
            instance.request_render(downsampling(), WINDOW)
            qtbot.waitUntil(lambda: len(landings.finished) == 1, timeout=RENDER_TIMEOUT_MS)
            instance.request_render(downsampling(), WINDOW)
            qtbot.waitUntil(lambda: len(landings.finished) == 2, timeout=RENDER_TIMEOUT_MS)
        finally:
            instance.shutdown()

        assert len(recorder.samples(FIRST_TICK_BUDGET)) == 1


class TestSuperseding:
    @pytest.fixture
    def slow_shelves(self) -> Iterator[tuple[FilterRegistry, KernelRegistry, list[int]]]:






        filters = FilterRegistry()
        kernels = KernelRegistry()
        calls: list[int] = []

        @register_filter(
            filter_id="slow",
            version="1.0.0",
            summary="Sleeps, then adds a constant to every pixel.",
            accepts=ArraySpec(),
            emits=ArraySpec(),
            element=ElementRelation.PRESERVED,
            cost=CostEstimate(seconds_per_megapixel=0.001),
            registry=filters,
        )
        class SlowParams(ParamsBase):
            bias: int = 0

        @kernel(SlowParams, Backend.CPU, registry=kernels)
        def slow_cpu(frame: Frame, params: SlowParams) -> Frame:
            sleep(SLOW_FRAME_SECONDS)
            calls.append(frame.index)
            return Frame(
                data=(frame.data + np.uint8(params.bias)),
                index=frame.index,
                channels=frame.channels,
            )

        assert callable(slow_cpu)
        yield filters, kernels, calls

    def test_an_edit_mid_render_stops_the_render_it_replaced(
        self,
        qtbot: QtBot,
        qapp: object,
        synthetic_video: Path,
        slow_shelves: tuple[FilterRegistry, KernelRegistry, list[int]],
    ) -> None:













        del qapp
        filters, kernels, calls = slow_shelves
        instance = opened_runner(qtbot, synthetic_video, shelves=(filters, kernels))
        landings = Landings(instance)

        try:
            instance.request_render(_slow_graph(bias=1), WINDOW)



            qtbot.waitUntil(lambda: bool(landings.costs), timeout=RENDER_TIMEOUT_MS)
            instance.request_render(_slow_graph(bias=2), WINDOW)

            qtbot.waitUntil(lambda: len(landings.starts) == 2, timeout=RENDER_TIMEOUT_MS)
            qtbot.waitUntil(lambda: bool(landings.finished), timeout=RENDER_TIMEOUT_MS)
        finally:
            instance.shutdown()

        assert landings.failures == []
        span = WINDOW.end - WINDOW.start
        assert len(calls) >= span, "the render the user is waiting for did not complete"
        assert len(calls) < 2 * span, "the superseded render ran to the end anyway"



        assert landings.indices[-span:] == list(range(WINDOW.start, WINDOW.end))


class TestRefusals:
    def test_an_empty_graph_is_not_rendered(self, runner: PreviewRunner) -> None:






        landings = Landings(runner)

        assert not runner.request_render(Pipeline(), WINDOW)
        assert landings.starts == []
        assert not runner.has_ticked

    def test_a_graph_naming_no_such_filter_is_reported(
        self, qtbot: QtBot, runner: PreviewRunner
    ) -> None:







        landings = Landings(runner)
        absent = Pipeline(nodes=(Node(node_id="ghost", filter_id="not_a_filter", version="1.0.0"),))

        assert runner.request_render(absent, WINDOW)
        qtbot.waitUntil(lambda: bool(landings.failures), timeout=RENDER_TIMEOUT_MS)
        assert "not_a_filter" in landings.failures[0]


        assert runner.request_render(downsampling(), WINDOW)
        qtbot.waitUntil(lambda: bool(landings.finished), timeout=RENDER_TIMEOUT_MS)


class TestPerFrameDelivery:
    def test_a_consumer_receives_every_node_output_off_the_gui_thread(
        self, qtbot: QtBot, runner: PreviewRunner
    ) -> None:








        landings = Landings(runner)
        seen: list[tuple[int, int]] = []

        def consumer(result: FrameResult) -> None:
            assert "small" in result.outputs
            seen.append((result.index, get_ident()))

        assert runner.request_render(downsampling(), WINDOW, consumer=consumer)
        qtbot.waitUntil(lambda: bool(landings.finished), timeout=RENDER_TIMEOUT_MS)

        assert [index for index, _ in seen] == list(range(WINDOW.start, WINDOW.end))
        assert all(thread != get_ident() for _, thread in seen)

    def test_request_frame_renders_exactly_the_asked_frame(
        self, qtbot: QtBot, runner: PreviewRunner
    ) -> None:


        landings = Landings(runner)
        seen: list[int] = []

        assert runner.request_frame(downsampling(), 7, consumer=lambda r: seen.append(r.index))
        qtbot.waitUntil(lambda: bool(landings.finished), timeout=RENDER_TIMEOUT_MS)

        assert seen == [7]
        assert landings.failures == []


class TestWindowRenderFlag:








    def test_a_window_render_raises_the_flag_and_its_end_lowers_it(
        self, qtbot: QtBot, runner: PreviewRunner
    ) -> None:
        landings = Landings(runner)
        flags: list[bool] = []
        runner.window_render_changed.connect(flags.append)

        assert not runner.window_render_active
        assert runner.request_render(downsampling(), WINDOW)
        assert runner.window_render_active, "the flag must rise with the submission"
        qtbot.waitUntil(lambda: bool(landings.finished), timeout=RENDER_TIMEOUT_MS)

        assert flags == [True, False]

    def test_a_single_frame_render_is_not_a_window_render(
        self, qtbot: QtBot, runner: PreviewRunner
    ) -> None:
        landings = Landings(runner)
        flags: list[bool] = []
        runner.window_render_changed.connect(flags.append)

        assert runner.request_frame(downsampling(), 7)
        assert not runner.window_render_active
        qtbot.waitUntil(lambda: bool(landings.finished), timeout=RENDER_TIMEOUT_MS)

        assert flags == []


def _slow_graph(*, bias: int) -> Pipeline:
    return Pipeline(
        nodes=(Node(node_id="slow", filter_id="slow", version="1.0.0", params={"bias": bias}),)
    )
