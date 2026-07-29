














from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

from sieve.bench.metrics import MetricBus
from sieve.gui.detector_worker import DetectorResult
from sieve.gui.document import ReplicateDocument
from sieve.gui.filter_tab import FilterTab
from sieve.gui.player import VideoPlayer
from sieve.gui.preview_runner import PreviewRunner
from tests.conftest import FIXTURE_FPS, FIXTURE_FRAMES, FIXTURE_HEIGHT, FIXTURE_WIDTH

pytestmark = pytest.mark.gui

RENDER_TIMEOUT_MS = 30_000


@pytest.fixture
def player(qapp: object) -> Iterator[VideoPlayer]:
    del qapp
    instance = VideoPlayer()
    yield instance
    instance.shutdown()


@pytest.fixture
def runner(qapp: object) -> Iterator[PreviewRunner]:
    del qapp
    instance = PreviewRunner(metrics=MetricBus())
    yield instance
    instance.shutdown()


@pytest.fixture
def tab(
    qtbot: QtBot, player: VideoPlayer, document: ReplicateDocument, runner: PreviewRunner
) -> Iterator[FilterTab]:
    instance = FilterTab(player, document, runner, metrics=MetricBus())
    qtbot.addWidget(instance)
    yield instance
    instance.shutdown()


def test_the_count_plot_holds_data_before_the_render_has_finished(
    qtbot: QtBot,
    tab: FilterTab,
    document: ReplicateDocument,
    runner: PreviewRunner,
    synthetic_video: Path,
) -> None:









    document.bind_source(FIXTURE_WIDTH, FIXTURE_HEIGHT, FIXTURE_FRAMES, FIXTURE_FPS)




    passes: list[tuple[bool, int]] = []

    def record(result: DetectorResult) -> None:
        passes.append((result.final, result.frames))

    tab._detector.ready.connect(record)

    runner.open(synthetic_video)
    qtbot.waitUntil(lambda: any(final for final, _ in passes), timeout=RENDER_TIMEOUT_MS)
    qtbot.wait(400)

    partials = [frames for final, frames in passes if not final]
    assert len(partials) > 1, (
        f"the graphs were built in {len(passes)} pass(es) — the partial path is dead "
        "and the tab is back to painting everything at the end"
    )



    assert partials == sorted(partials), (
        f"a pass covered fewer frames than its predecessor: {partials}"
    )

    window = document.window
    assert window is not None
    assert passes[-1] == (True, window.frame_count)

    assert tab.count_plot.filled_frames == tab.count_plot.settled_frames
    assert not tab.summary_text.endswith(" · filling")


def test_a_window_shorter_than_the_settling_distance_gates_nothing_until_it_finishes(
    qtbot: QtBot,
    tab: FilterTab,
    document: ReplicateDocument,
    runner: PreviewRunner,
    synthetic_video: Path,
) -> None:













    document.bind_source(FIXTURE_WIDTH, FIXTURE_HEIGHT, FIXTURE_FRAMES, FIXTURE_FPS)
    settled: list[tuple[bool, int]] = []

    def record(result: DetectorResult) -> None:
        settled.append((result.final, result.settled))

    tab._detector.ready.connect(record)

    runner.open(synthetic_video)
    qtbot.waitUntil(lambda: any(final for final, _ in settled), timeout=RENDER_TIMEOUT_MS)
    qtbot.wait(400)

    assert [s for final, s in settled if not final], "no partial pass ran — nothing is being tested"
    assert all(s == 0 for final, s in settled if not final), (
        "a window shorter than the settling distance claimed settled frames"
    )
    assert settled[-1][1] == FIXTURE_FRAMES, "the final pass must claim the whole record"


def test_the_axis_is_the_working_window_not_the_frames_collected_so_far(
    qtbot: QtBot,
    tab: FilterTab,
    document: ReplicateDocument,
    runner: PreviewRunner,
    synthetic_video: Path,
) -> None:









    document.bind_source(FIXTURE_WIDTH, FIXTURE_HEIGHT, FIXTURE_FRAMES, FIXTURE_FPS)
    runner.open(synthetic_video)
    qtbot.waitUntil(lambda: tab.count_plot.filled_frames > 0, timeout=RENDER_TIMEOUT_MS)

    window = document.window
    assert window is not None
    for plot in (tab.count_plot, tab.scalogram, tab.density):


        assert plot.x_of(window.start) == pytest.approx(plot.plot_rect().left())
        assert plot.filled_frames <= window.frame_count

    qtbot.waitUntil(
        lambda: tab.count_plot.filled_frames >= window.frame_count, timeout=RENDER_TIMEOUT_MS
    )
    assert tab.count_plot.x_of(window.start) == pytest.approx(tab.count_plot.plot_rect().left())
