"""What the runner has to get right, which is ordering and one budget.

`pipeline/preview.py` already owns whether a render is correct, so nothing here
asserts on a frame. Three claims, each failing for a reason the others cannot:

**Frames arrive keyed by source index, and the first one is the tick.**
`filter_to_first_tick` has had a ceiling since before there was a preview and
has never had a producer. If this fails, the budget is still unmeasurable and
the live graph has no series to be drawn from.

**A superseded render stops computing.** The GUI side drops stale frames by
revision whatever the worker does, so a runner that never cancelled would look
identical in everything it emits and would spend a whole cold render — 1350 ms
on the reference source — before starting the one the user is waiting for. The
observable has to be work *not done*, which is why the second test counts kernel
calls rather than signals.

**An empty graph is refused.** With no nodes the executor still walks the span,
so running one is a second decode of footage the player already has, for a graph
with nothing to say. It is also what makes "first filter" an event at all: the
arm is exactly the moment this stops returning False.

The first test drives the real shelf over the synthetic fixture, because the
claim is end to end. The second uses a scratch shelf with a kernel that sleeps:
`downsample` over a 160x120 frame finishes faster than a test can supersede it,
so against the real shelf the abandon path would be pinned by a race rather than
by a rule.
"""

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
from sieve.core.types import Frame, WorkUnits
from sieve.gui.preview_runner import FIRST_TICK_BUDGET, PreviewRunner
from sieve.pipeline.executor import FrameResult

pytestmark = pytest.mark.gui

OPEN_TIMEOUT_MS = 10_000
RENDER_TIMEOUT_MS = 30_000

#: A window well inside the 40-frame fixture. Short, because every test here is
#: about which frames arrive rather than about how many.
WINDOW = ClipRange(start=0, end=12)

#: What the sleeping kernel costs per frame. Long enough that a supersede lands
#: within the first frames of a render and short enough that the whole test is
#: under a second.
SLOW_FRAME_SECONDS = 0.015


class Landings:
    """Frame costs and render boundaries, in arrival order."""

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
    """One real node, so the first test exercises the shelf the application uses."""
    node = Node(node_id="small", filter_id="downsample", version="1.0.0", params={"factor": 2})
    return Pipeline(nodes=(node,))


def opened_runner(
    qtbot: QtBot,
    video: Path,
    *,
    metrics: MetricBus | None = None,
    shelves: tuple[FilterRegistry, KernelRegistry] | None = None,
) -> PreviewRunner:
    """A runner with the fixture loaded and its render thread up."""
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
        """The series and the budget, from the real shelf over real footage.

        The indices are the assertion that matters: a graph the user tunes is
        drawn against *their* clip, so a series keyed by anything other than the
        source index — an offset into the span, a count of deliveries — would
        put the expensive frames under the wrong part of the timeline and no
        frame-level test would notice.
        """
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
            # Before the shutdown below, which unloads the source and re-arms
            # the tick — the flag is about a session and this one is still open.
            assert instance.has_ticked
        finally:
            instance.shutdown()

        # Exactly one, across a render of twelve frames: the budget is "first
        # filter to first tick", and a producer that published it per frame
        # would fill the series a gate reads with intervals that are not the
        # one the ceiling describes.
        assert len(recorder.samples(FIRST_TICK_BUDGET)) == 1

    def test_a_second_render_does_not_tick_again(
        self, qtbot: QtBot, qapp: object, synthetic_video: Path
    ) -> None:
        """The arm is per source, not per render.

        A second edit is what `slider_to_graph` will describe once there is a
        slider to drag. Re-publishing `filter_to_first_tick` for it would put a
        warm re-render — 3.3 ms — into the same series as the cold first one and
        make a 2 s ceiling look comfortable for the wrong reason.
        """
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
        """A one-filter world whose kernel sleeps and counts, on its own shelf.

        Registered per test so nothing here reaches the process-wide shelf the
        application scans — a slow filter left on it would be found by
        `sieve inspect` and by every other test in the run.
        """
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
            cost=CostEstimate(work_per_megapixel=WorkUnits(1.0)),
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
        """Work not done is the observable, because everything else looks the same.

        The GUI side already drops a stale revision's frames, so a runner with
        no cancellation at all would emit exactly what this one emits. What it
        would also do is finish the first render before beginning the second —
        and on the footage this is for, that is the whole 1350 ms the user is
        waiting through, spent on a graph they have already changed.

        The two renders carry different parameters, so the second cannot be
        served from the first's entries: every one of its twelve frames is a
        kernel call. Twelve is therefore the floor, and twenty-four the count a
        run-to-completion would reach.
        """
        del qapp
        filters, kernels, calls = slow_shelves
        instance = opened_runner(qtbot, synthetic_video, shelves=(filters, kernels))
        landings = Landings(instance)

        try:
            instance.request_render(_slow_graph(bias=1), WINDOW)
            # Superseded as soon as the first render has proved it is running.
            # Waiting for a wall-clock duration instead would make the test's
            # meaning depend on the machine it runs on.
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

        # And the frames that did reach a consumer are the newest render's,
        # whole: a partial series would draw a graph with a hole in it.
        assert landings.indices[-span:] == list(range(WINDOW.start, WINDOW.end))


class TestRefusals:
    def test_an_empty_graph_is_not_rendered(self, runner: PreviewRunner) -> None:
        """Nothing submitted, nothing armed, nothing decoded.

        `has_ticked` staying False is the second half and the more important
        one: it is what keeps the `filter_to_first_tick` clock from starting
        before there is a filter to start it.
        """
        landings = Landings(runner)

        assert not runner.request_render(Pipeline(), WINDOW)
        assert landings.starts == []
        assert not runner.has_ticked

    def test_a_graph_naming_no_such_filter_is_reported(
        self, qtbot: QtBot, runner: PreviewRunner
    ) -> None:
        """A refusal reaches the GUI thread as a sentence rather than a traceback.

        The five exceptions the worker catches are the five `sieve preview`
        catches, and on a worker thread an uncaught one reaches nobody at all —
        the render simply never reports back and the slot it holds is never
        freed, which wedges every render after it.
        """
        landings = Landings(runner)
        absent = Pipeline(nodes=(Node(node_id="ghost", filter_id="not_a_filter", version="1.0.0"),))

        assert runner.request_render(absent, WINDOW)
        qtbot.waitUntil(lambda: bool(landings.failures), timeout=RENDER_TIMEOUT_MS)
        assert "not_a_filter" in landings.failures[0]

        # The slot was freed: a real graph submitted afterwards still runs.
        assert runner.request_render(downsampling(), WINDOW)
        qtbot.waitUntil(lambda: bool(landings.finished), timeout=RENDER_TIMEOUT_MS)


class TestPerFrameDelivery:
    def test_a_consumer_receives_every_node_output_off_the_gui_thread(
        self, qtbot: QtBot, runner: PreviewRunner
    ) -> None:
        """Item 4's delivery claim: the consumer sees `FrameResult`s — node
        outputs included — on the render thread, in span order.

        The thread assertion is the load-bearing half: a consumer marshalled
        through a queued signal per frame would be six hundred GUI-thread
        events per render, which is the cost the direct callback exists to
        avoid.
        """
        landings = Landings(runner)
        seen: list[tuple[int, int]] = []  # (index, thread id)

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
        """The single-frame path: one result, carrying the asked index — the
        wizard's video preview and nothing more."""
        landings = Landings(runner)
        seen: list[int] = []

        assert runner.request_frame(downsampling(), 7, consumer=lambda r: seen.append(r.index))
        qtbot.waitUntil(lambda: bool(landings.finished), timeout=RENDER_TIMEOUT_MS)

        assert seen == [7]
        assert landings.failures == []


class TestWindowRenderFlag:
    """What the viewport's auto-gray policy listens to, and what it must not hear.

    The distinction is the whole signal: a *window* render is seconds of
    contention worth going gray for, while a single-frame refresh arrives once
    per playhead move and treating it as "rendering" would flap the viewport's
    format at playback rate.
    """

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
