"""The selected replicate is the one being tuned.

Three claims, each a distinct way the tab could quietly show the wrong arena.
The render could keep taking row 0 whatever the user selected — the bug this
item exists for, and one that passes by accident on any single-replicate
project, which is why every test here holds two replicates with different
ROIs. A selection change could race the graphs' window render by going out as
frame requests instead of riding the runner's latest-wins window submission.
And the accept gesture could select without navigating, leaving the vision's
sentence — click a box, land on the filter tab with that arena under you —
half true.

Three more hold the other half of the same question: not *which* arena is on
screen but *when* what is on screen goes stale. The arena can be rewritten
under a standing selection — a crop edit, or the undo of one — and that has
to invalidate the render exactly as selecting a different arena does, while an
edit to a row nobody is tuning must not.
"""

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

#: Two arenas that fit both fixture geometries — the `document` fixture's
#: 1000x800 source and the 160x120 synthetic video — so neither test family
#: has its ROI silently clamped into agreement with the other's.
FIRST_BOX = ROI(x=5, y=5, width=60, height=50)
SECOND_BOX = ROI(x=80, y=60, width=40, height=30)


class _StubRunner(QObject):
    """A runner that records what it was handed instead of rendering.

    The tab only reads `revision` and calls the two request methods; what the
    tests assert is which *replicate* rode each submission and which path —
    window or single frame — the submission took.
    """

    frame_cost = Signal(int, float)
    render_started = Signal(int)
    render_finished = Signal(object)
    render_failed = Signal(str)
    opened = Signal()
    open_failed = Signal(str)

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
    instance = FilterTab(player, document, stub, metrics=MetricBus())  # type: ignore[arg-type]
    qtbot.addWidget(instance)
    yield instance
    # The tab owns the detector thread, so it carries the same
    # shutdown obligation the player and the runner do. Without
    # this every tab built here leaks a QThread and the suite
    # wedges a few modules later.
    instance.shutdown()


def test_the_render_carries_the_selected_replicate_not_row_zero(
    tab: FilterTab, stub: _StubRunner, document: ReplicateDocument
) -> None:
    """Selecting row N renders N's crop — the current bug, pinned.

    Two replicates with different ROIs, because on a single-replicate project
    row 0 and the selection are the same replicate and the old hard-coded read
    passes by accident.
    """
    del tab
    document.add_roi(FIRST_BOX)
    document.add_roi(SECOND_BOX)

    document.select(0)
    stub.opened.emit()  # the tab resubmits as the runner announces itself
    assert stub.window_replicates[-1] is not None
    assert stub.window_replicates[-1].roi == FIRST_BOX

    document.select(1)
    assert stub.window_replicates[-1] is not None
    assert stub.window_replicates[-1].roi == SECOND_BOX


def test_a_selection_change_rides_the_window_path_and_supersedes(
    tab: FilterTab, stub: _StubRunner, document: ReplicateDocument
) -> None:
    """A replicate change invalidates exactly as a window move does.

    It must go out as a *window* render through the runner's latest-wins slot
    — never as a single-frame refresh, which would displace the graphs'
    outstanding render from the one pending slot and leave the series stale
    until the next edit (the discipline the step composite established).
    """
    del tab
    document.add_roi(FIRST_BOX)
    document.add_roi(SECOND_BOX)
    stub.opened.emit()
    windows_before = len(stub.window_replicates)

    document.select(0)  # while the first window render is still outstanding

    assert stub.frame_replicates == [], "a selection change took the single-frame path"
    assert len(stub.window_replicates) == windows_before + 1


def test_undoing_a_crop_edit_resubmits_the_selected_arena(
    tab: FilterTab, stub: _StubRunner, document: ReplicateDocument
) -> None:
    """Ctrl+Z on a crop must put the *pre-edit* geometry back on screen.

    `SetReplicateROI`'s undo writes through `apply_replace`, which emits only
    `replicate_changed` — no selection change, no tuning change. A tab that
    does not listen for it renders the geometry the undo just discarded, and
    the aspect on screen is the old crop's.
    """
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
    """Only the selected arena is on screen, so only it can invalidate.

    The cheap half of the same wiring: without the index test, every row's
    geometry edit — and `set_all_to_size` writes every row — would throw a
    full window render for an arena nobody is looking at.
    """
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
    """`select` stays a no-op on the current row, and that is now harmless.

    The guard at `ReplicateDocument.select` is deliberate — selection is not a
    command, and re-emitting would make it a refresh primitive every caller
    inherits. It was only *load-bearing* while the tab had no other way to hear
    about a geometry edit: the gesture that papered over the missing
    subscription was clicking the row you were already on. With
    `replicate_changed` wired, what the tab last rendered already matches the
    document before the re-select, and the re-select still costs nothing.
    """
    del tab
    document.add_roi(FIRST_BOX)
    document.select(0)
    stub.opened.emit()
    document.set_roi(0, SECOND_BOX)
    windows_before = len(stub.window_replicates)

    document.select(0)

    assert len(stub.window_replicates) == windows_before, "a no-op select re-rendered"
    assert stub.window_replicates[-1] is not None
    assert stub.window_replicates[-1].roi == document.selected_replicate.roi  # type: ignore[union-attr]


@pytest.fixture
def window_with_replicates(
    qtbot: QtBot, tmp_path: Path, synthetic_video: Path
) -> Iterator[tuple[MainWindow, ReplicateDocument]]:
    """A real window over the synthetic fixture, with two arenas cut."""
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
    """The vision's sentence, end to end: left click on a replicate accepts
    it and moves the user over to the filter tab with that arena selected —
    while a plain selection (a table-row click lands as `select`) stays put."""
    window, document = window_with_replicates
    tabs = window.findChild(QTabWidget)
    view = window.findChild(VideoView)
    assert tabs is not None and view is not None

    document.select(0)
    assert tabs.currentIndex() == 0, "a plain selection navigated"

    view.selection_requested.emit(1)

    assert document.selected_index == 1
    assert tabs.currentIndex() == 1, "the accept did not land on the filter tab"
