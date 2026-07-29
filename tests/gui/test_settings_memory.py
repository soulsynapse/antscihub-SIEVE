








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






    _two_arenas(document)

    tab.downsample_knob.setValue(0.5)
    document.select(1)
    assert tab.downsample_knob.value() == 0.5

    tab.downsample_knob.setValue(0.25)
    document.select(0)
    assert tab.downsample_knob.value() == 0.5
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






    _two_arenas(document)

    document.edit_detector({"window_frames": 45}, "Set Detection Window")
    document.select(1)
    assert tab.chain.detector.window_frames == 45

    document.edit_detector({"window_frames": 90}, "Set Detection Window")
    document.select(0)
    assert tab.chain.detector.window_frames == 45
    document.select(1)
    assert tab.chain.detector.window_frames == 90

    assert document.equivalence_groups() == (1, 2)


def test_saved_tuning_comes_back_per_arena_through_yaml(
    qtbot: QtBot,
    tab: FilterTab,
    document: ReplicateDocument,
    player: VideoPlayer,
    runner: PreviewRunner,
) -> None:






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

        assert second.downsample_knob.value() == 0.5
        reopened.select(1)
        assert second.downsample_knob.value() == 0.25
        assert second.chain.detector.count_frac == (0.1, 1.0)
    finally:
        second.shutdown()
