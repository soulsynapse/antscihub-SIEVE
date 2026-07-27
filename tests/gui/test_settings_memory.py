"""Replicates remember their settings — the round trip the feature is.

Three claims, each a distinct lie the tab could tell. A knob that did not
follow the selection would show one arena's tuning over another's footage; an
undo that restored the baseline but not the pin (or vice versa) would leave a
state no sequence of edits can produce; a save that did not come back as the
same resolved values per arena would make "remember" mean "until you close".
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

from sieve.bench.metrics import MetricBus
from sieve.core.pipeline_model import Project
from sieve.core.types import ROI
from sieve.gui.document import ReplicateDocument
from sieve.gui.filter_tab import FilterTab
from sieve.gui.player import VideoPlayer
from sieve.gui.preview_runner import PreviewRunner

pytestmark = pytest.mark.gui


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
    # The conftest document was bound before the tab existed, so re-bind with
    # the tab listening — the app's own order — which seeds the fresh chain
    # into the document and gives the first knob edit a baseline to move.
    document.bind_source(1000, 800, 1000, 30.0)
    yield instance
    instance.shutdown()


def _two_arenas(document: ReplicateDocument) -> None:
    document.add_roi(ROI(0, 0, 100, 100))
    document.add_roi(ROI(200, 0, 100, 100))
    document.select(0)


def test_knobs_follow_until_touched_and_return_with_the_arena(
    tab: FilterTab, document: ReplicateDocument
) -> None:
    """Tune arena 1, and arena 2 follows; deviate arena 2, and each recalls its own.

    The undo at the end is the two-write claim: one Ctrl+Z after deviating
    must restore the moved baseline *and* drop the pin, or the document holds
    a state no sequence of edits can produce.
    """
    _two_arenas(document)

    tab.downsample_knob.setValue(0.5)
    document.select(1)
    assert tab.downsample_knob.value() == 0.5  # followed the moved baseline

    tab.downsample_knob.setValue(0.25)  # deviate arena 2
    document.select(0)
    assert tab.downsample_knob.value() == 0.5  # arena 1 recalls its own
    document.select(1)
    assert tab.downsample_knob.value() == 0.25
    assert document.equivalence_groups() == (1, 2)

    document.undo_stack.undo()
    assert tab.downsample_knob.value() == 0.5
    assert document.at(1).overrides == {}
    assert document.equivalence_groups() == (1, 1)


def test_detector_settings_pin_and_follow_per_arena(
    tab: FilterTab, document: ReplicateDocument
) -> None:
    """The detection window is remembered per arena exactly as a knob is.

    Driven through the document because that is the tab's own commit path —
    the assertion is that the chain the graphs derive from re-resolves on
    every selection change, detector included.
    """
    _two_arenas(document)

    document.edit_detector({"window_frames": 45}, "Set Detection Window")
    document.select(1)
    assert tab.chain.detector.window_frames == 45  # followed

    document.edit_detector({"window_frames": 90}, "Set Detection Window")
    document.select(0)
    assert tab.chain.detector.window_frames == 45
    document.select(1)
    assert tab.chain.detector.window_frames == 90
    # Groups split on detector pins too: same graph, different claims.
    assert document.equivalence_groups() == (1, 2)


def test_saved_tuning_comes_back_per_arena_through_yaml(
    qtbot: QtBot,
    tab: FilterTab,
    document: ReplicateDocument,
    player: VideoPlayer,
    runner: PreviewRunner,
) -> None:
    """Save, reopen in a fresh document and tab, and each arena resolves as tuned.

    The whole feature in one path: two-write edits, the artifact carrying
    graph + detector + pins through YAML, and the tab regrowing its chain
    around the loaded node ids rather than reminting them.
    """
    _two_arenas(document)
    tab.downsample_knob.setValue(0.5)
    document.select(1)
    tab.downsample_knob.setValue(0.25)
    document.edit_detector({"count_frac": (0.1, 1.0)}, "Set Count Threshold")

    project = Project.from_yaml(document.apply_to(Project.for_video(Path("video.mp4"))).to_yaml())

    reopened = ReplicateDocument()
    second = FilterTab(player, reopened, runner, metrics=MetricBus())
    qtbot.addWidget(second)
    try:
        reopened.bind_source(1000, 800, 1000, 30.0)
        reopened.load_project(project)

        assert [n.node_id for n in reopened.pipeline.nodes] == [
            n.node_id for n in project.pipeline.nodes
        ]
        # Selection opens on the first arena: its pinned scale, no pin noise.
        assert second.downsample_knob.value() == 0.5
        reopened.select(1)
        assert second.downsample_knob.value() == 0.25
        assert second.chain.detector.count_frac == (0.1, 1.0)
    finally:
        second.shutdown()
