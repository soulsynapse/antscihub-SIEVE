


















from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QObject, QSettings, Signal
from PySide6.QtWidgets import QTabWidget
from pytestqt.qtbot import QtBot

from sieve.bench.metrics import MetricBus
from sieve.core.replicates import Replicate
from sieve.core.types import ROI
from sieve.gui.document import ReplicateDocument
from sieve.gui.filter_tab import FilterTab
from sieve.gui.main_window import MainWindow
from sieve.gui.player import VideoPlayer
from sieve.gui.preferences import Preferences
from sieve.gui.video_view import VideoView

pytestmark = pytest.mark.gui

OPEN_TIMEOUT_MS = 15_000




FIRST_BOX = ROI(x=5, y=5, width=60, height=50)
SECOND_BOX = ROI(x=80, y=60, width=40, height=30)


class _StubRunner(QObject):







    frame_cost = Signal(int, float)
    render_started = Signal(int)
    render_finished = Signal(object)
    render_failed = Signal(str)
    opened = Signal()
    open_failed = Signal(str)
    window_render_changed = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self.revision = 0
        self.window_replicates: list[Replicate | None] = []
        self.frame_replicates: list[Replicate | None] = []

    def request_render(
        self,
        pipeline: object,
        window: object,
        replicate: Replicate | None,
        consumer: object = None,
    ) -> bool:
        self.revision += 1
        self.window_replicates.append(replicate)
        return True

    def request_frame(
        self,
        pipeline: object,
        index: int,
        replicate: Replicate | None,
        consumer: object = None,
    ) -> bool:
        self.revision += 1
        self.frame_replicates.append(replicate)
        return True


@pytest.fixture
def player(qapp: object) -> Iterator[VideoPlayer]:
    del qapp
    instance = VideoPlayer()
    yield instance
    instance.shutdown()


@pytest.fixture
def stub() -> _StubRunner:
    return _StubRunner()


@pytest.fixture
def tab(
    qtbot: QtBot, player: VideoPlayer, document: ReplicateDocument, stub: _StubRunner
) -> Iterator[FilterTab]:
    instance = FilterTab(player, document, stub, metrics=MetricBus())
    qtbot.addWidget(instance)
    yield instance




    instance.shutdown()


def test_the_render_carries_the_selected_replicate_not_row_zero(
    tab: FilterTab, stub: _StubRunner, document: ReplicateDocument
) -> None:






    del tab
    document.add_roi(FIRST_BOX)
    document.add_roi(SECOND_BOX)

    document.select(0)
    stub.opened.emit()
    assert stub.window_replicates[-1] is not None
    assert stub.window_replicates[-1].roi == FIRST_BOX

    document.select(1)
    assert stub.window_replicates[-1] is not None
    assert stub.window_replicates[-1].roi == SECOND_BOX


def test_a_selection_change_rides_the_window_path_and_supersedes(
    tab: FilterTab, stub: _StubRunner, document: ReplicateDocument
) -> None:







    del tab
    document.add_roi(FIRST_BOX)
    document.add_roi(SECOND_BOX)
    stub.opened.emit()
    windows_before = len(stub.window_replicates)

    document.select(0)

    assert stub.frame_replicates == [], "a selection change took the single-frame path"
    assert len(stub.window_replicates) == windows_before + 1


def test_undoing_a_crop_edit_resubmits_the_selected_arena(
    tab: FilterTab, stub: _StubRunner, document: ReplicateDocument
) -> None:







    del tab
    document.add_roi(FIRST_BOX)
    document.select(0)
    stub.opened.emit()

    document.set_roi(0, SECOND_BOX)
    assert stub.window_replicates[-1] is not None
    assert stub.window_replicates[-1].roi == SECOND_BOX

    document.undo_stack.undo()

    assert stub.window_replicates[-1] is not None
    assert stub.window_replicates[-1].roi == FIRST_BOX


def test_an_edit_to_an_unselected_arena_does_not_resubmit(
    tab: FilterTab, stub: _StubRunner, document: ReplicateDocument
) -> None:






    del tab
    document.add_roi(FIRST_BOX)
    document.add_roi(SECOND_BOX)
    document.select(0)
    stub.opened.emit()
    windows_before = len(stub.window_replicates)

    document.set_roi(1, ROI(x=90, y=70, width=20, height=20))

    assert len(stub.window_replicates) == windows_before


def test_selecting_the_already_selected_row_leaves_the_tab_consistent(
    tab: FilterTab, stub: _StubRunner, document: ReplicateDocument
) -> None:










    del tab
    document.add_roi(FIRST_BOX)
    document.select(0)
    stub.opened.emit()
    document.set_roi(0, SECOND_BOX)
    windows_before = len(stub.window_replicates)

    document.select(0)

    assert len(stub.window_replicates) == windows_before, "a no-op select re-rendered"
    assert stub.window_replicates[-1] is not None
    assert stub.window_replicates[-1].roi == document.selected_replicate.roi


@pytest.fixture
def window_with_replicates(
    qtbot: QtBot, tmp_path: Path, synthetic_video: Path
) -> Iterator[tuple[MainWindow, ReplicateDocument]]:

    preferences = Preferences(QSettings(str(tmp_path / "sieve.ini"), QSettings.Format.IniFormat))
    window = MainWindow(preferences)
    qtbot.addWidget(window)
    window.open_video(synthetic_video)
    qtbot.waitUntil(lambda: window.windowTitle() != "SIEVE", timeout=OPEN_TIMEOUT_MS)
    document = window.findChild(ReplicateDocument)
    assert document is not None
    document.add_roi(FIRST_BOX)
    document.add_roi(SECOND_BOX)
    yield window, document
    window.close()


def test_clicking_a_box_on_the_video_accepts_and_navigates(
    window_with_replicates: tuple[MainWindow, ReplicateDocument],
) -> None:



    window, document = window_with_replicates
    tabs = window.findChild(QTabWidget)
    view = window.findChild(VideoView)
    assert tabs is not None and view is not None

    document.select(0)
    assert tabs.currentIndex() == 0, "a plain selection navigated"

    view.selection_requested.emit(1)

    assert document.selected_index == 1
    assert tabs.currentIndex() == 1, "the accept did not land on the filter tab"
