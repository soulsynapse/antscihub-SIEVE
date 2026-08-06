"""The graphs fill while the render runs, rather than all at once when it ends.

The behaviour this whole path exists for. Before it, `_on_render_finished` was
the only thing that ever produced a `DetectorUpdate`, so a user watching a long
window render saw an empty count plot for the duration and then everything.

Two claims here, each failing for a different reason:

* nothing is painted before the render finishes — the partial path is dead and
  the tab is back to its old all-at-once behaviour;
* the axis moves while it fills — the x span tracks the collected frames rather
  than the working window, so every curve slides leftward on each pass and a
  filling graph reads as a moving one.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

from sieve.bench.metrics import MetricBus
from sieve.gui.detector_worker import DetectorResult
from sieve.gui.document import ReplicateDocument
from sieve.gui.filter_tab import FilterTab
from sieve.gui.preview_runner import PreviewRunner
from sieve.gui.transport.player import VideoPlayer
from tests.conftest import FIXTURE_FRAMES, FIXTURE_HEIGHT, FIXTURE_RATE, FIXTURE_WIDTH

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
    """A partial pass reaches the plots while frames are still being rendered.

    Watched through the plot rather than through the tab's private state: what
    is being claimed is that the *user* sees a filling graph, and the count
    plot's filled extent is the observable form of that.

    The final `graphs_updated` is deliberately not awaited first — that would
    be asserting the old behaviour with extra steps.
    """
    document.bind_source(FIXTURE_WIDTH, FIXTURE_HEIGHT, FIXTURE_FRAMES, FIXTURE_RATE)
    # Every derivation the detector delivers, partial and final. Private
    # because the claim *is* about internal bookkeeping — that more than one
    # pass happens — and there is no public reading that distinguishes a graph
    # built in seventeen steps from one built in one.
    passes: list[tuple[bool, int]] = []

    def record(result: DetectorResult) -> None:
        passes.append((result.final, result.frames))

    tab._detector.ready.connect(record)  # pyright: ignore[reportPrivateUsage]

    runner.open(synthetic_video)
    qtbot.waitUntil(lambda: any(final for final, _ in passes), timeout=RENDER_TIMEOUT_MS)
    qtbot.wait(400)

    partials = [frames for final, frames in passes if not final]
    assert len(partials) > 1, (
        f"the graphs were built in {len(passes)} pass(es) — the partial path is dead "
        "and the tab is back to painting everything at the end"
    )
    # Monotone: each pass covers strictly more of the window than the last, so
    # the graph only ever grows rightward. A pass that went backwards would be
    # a stale snapshot overtaking a newer one.
    assert partials == sorted(partials), (
        f"a pass covered fewer frames than its predecessor: {partials}"
    )

    window = document.window
    assert window is not None
    assert passes[-1] == (True, window.frame_count)
    # A finished render has no moving frontier: nothing may stay provisional.
    assert tab.count_plot.filled_frames == tab.count_plot.settled_frames
    assert not tab.summary_text.endswith(" · filling")


def test_a_window_shorter_than_the_settling_distance_gates_nothing_until_it_finishes(
    qtbot: QtBot,
    tab: FilterTab,
    document: ReplicateDocument,
    runner: PreviewRunner,
    synthetic_video: Path,
) -> None:
    """Honest rather than eager: a short window settles nothing while filling.

    The fixture is 40 frames at 20 fps and the default band reaches down to
    0.5 Hz, whose settling distance is ~110 frames — longer than the whole
    window. So every partial pass here settles zero frames and the curve fills
    entirely provisionally, with detections appearing only when the render
    finishes and the frontier stops moving.

    This is the design working, not a gap in it, and it is worth pinning:
    someone tempted to make short windows "feel more responsive" by settling
    them early would be reintroducing exactly the retracting detections the
    frontier exists to prevent.
    """
    document.bind_source(FIXTURE_WIDTH, FIXTURE_HEIGHT, FIXTURE_FRAMES, FIXTURE_RATE)
    settled: list[tuple[bool, int]] = []

    def record(result: DetectorResult) -> None:
        settled.append((result.final, result.settled))

    tab._detector.ready.connect(record)  # pyright: ignore[reportPrivateUsage]

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
    """The span never moves while the data fills into it.

    A plot whose span grew with its data would re-scale on every partial pass,
    sliding every curve leftward — a graph that appears to be *moving* rather
    than filling, which is worse to read than the empty plot it replaced.

    The window is the document's, so the span is checked against that rather
    than against a number this test invents.
    """
    document.bind_source(FIXTURE_WIDTH, FIXTURE_HEIGHT, FIXTURE_FRAMES, FIXTURE_RATE)
    runner.open(synthetic_video)
    qtbot.waitUntil(lambda: tab.count_plot.filled_frames > 0, timeout=RENDER_TIMEOUT_MS)

    window = document.window
    assert window is not None
    for plot in (tab.count_plot, tab.scalogram, tab.density):
        # `x_of` is the geometry every curve is drawn through, so pinning the
        # span through it pins what the user actually sees.
        assert plot.x_of(window.start) == pytest.approx(plot.plot_rect().left())
        assert plot.filled_frames <= window.frame_count

    qtbot.waitUntil(
        lambda: tab.count_plot.filled_frames >= window.frame_count, timeout=RENDER_TIMEOUT_MS
    )
    assert tab.count_plot.x_of(window.start) == pytest.approx(tab.count_plot.plot_rect().left())
