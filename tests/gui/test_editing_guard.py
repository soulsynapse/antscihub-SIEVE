"""The guard that stops window shortcuts eating a cell editor's keystrokes.

Qt dispatches window shortcuts before the focused widget sees the key, so
without this guard typing a space into a replicate name starts playback and
pressing Delete removes the row being renamed. The delegate announces the
editor, the tab relays it, and the window disables the two colliding actions.
Each link is tested on its own, then the whole chain through a real window with
a real video open — the failure this prevents only exists once all three are
wired together.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QModelIndex, QPointF
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QTableView, QWidget
from pytestqt.qtbot import QtBot

from sieve.core.types import ROI
from sieve.gui.document import ReplicateDocument
from sieve.gui.main_window import MainWindow
from sieve.gui.player import VideoPlayer
from sieve.gui.replicate_tab import ReplicateTab
from sieve.gui.replicate_table import Column, EditingAwareDelegate, ReplicateTableModel
from sieve.gui.video_view import VideoView
from tests.gui.qt_input import drag

pytestmark = pytest.mark.gui

BOX = ROI(x=10, y=20, width=100, height=80)
OPEN_TIMEOUT_MS = 15_000

PLAY_ACTION = "&Play / Pause"
DELETE_ACTION = "&Delete Replicate"


def _name_cell(table: QTableView) -> QModelIndex:
    model = table.model()
    assert model is not None
    return model.index(0, int(Column.NAME))


def _table_of(parent: QWidget) -> QTableView:
    table = parent.findChild(QTableView)
    assert isinstance(table, QTableView)
    return table


def _action(window: MainWindow, text: str) -> QAction:
    matches = [action for action in window.findChildren(QAction) if action.text() == text]
    assert len(matches) == 1, f"no unique action titled {text!r}"
    return matches[0]


class TestEditingAwareDelegate:
    def test_an_editor_is_announced_when_it_opens_and_closes(
        self, qtbot: QtBot, document: ReplicateDocument
    ) -> None:
        document.add_roi(BOX)
        table = QTableView()
        qtbot.addWidget(table)
        table.setModel(ReplicateTableModel(document, table))
        delegate = EditingAwareDelegate(table)
        table.setItemDelegate(delegate)

        started: list[None] = []
        finished: list[None] = []
        delegate.editing_started.connect(lambda: started.append(None))
        delegate.editing_finished.connect(lambda: finished.append(None))

        index = _name_cell(table)
        table.openPersistentEditor(index)
        assert (len(started), len(finished)) == (1, 0)

        table.closePersistentEditor(index)
        assert (len(started), len(finished)) == (1, 1)


class TestTabRelay:
    @pytest.fixture
    def tab(self, qtbot: QtBot, document: ReplicateDocument) -> Iterator[ReplicateTab]:
        player = VideoPlayer()
        widget = ReplicateTab(player, document)
        qtbot.addWidget(widget)
        yield widget
        player.shutdown()

    def test_the_tab_reports_the_editor_state(
        self, tab: ReplicateTab, document: ReplicateDocument
    ) -> None:
        document.add_roi(BOX)
        table = _table_of(tab)

        states: list[bool] = []
        tab.editor_open_changed.connect(states.append)

        index = _name_cell(table)
        table.openPersistentEditor(index)
        table.closePersistentEditor(index)

        assert states == [True, False]


class TestWindowShortcutGuard:
    @pytest.fixture
    def window(self, qtbot: QtBot, synthetic_video: Path) -> Iterator[MainWindow]:
        """A shown window with the synthetic video open and one replicate drawn."""
        main = MainWindow()
        qtbot.addWidget(main)
        main.show()
        main.open_video(synthetic_video)

        # The title is set from the same `opened` signal the tab listens to, so
        # once it changes the viewport knows the source size a drag needs.
        qtbot.waitUntil(lambda: main.windowTitle() != "SIEVE", timeout=OPEN_TIMEOUT_MS)

        view = main.findChild(VideoView)
        assert isinstance(view, VideoView)
        drag(
            view,
            QPointF(view.width() * 0.25, view.height() * 0.25),
            QPointF(view.width() * 0.75, view.height() * 0.75),
        )
        yield main
        main.close()

    def test_a_replicate_was_drawn(self, window: MainWindow) -> None:
        """Guards the fixture itself: the tests below are vacuous without a row."""
        model = _table_of(window).model()
        assert model is not None
        assert model.rowCount() == 1

    def test_space_and_delete_yield_to_an_open_editor(self, window: MainWindow) -> None:
        play, delete = _action(window, PLAY_ACTION), _action(window, DELETE_ACTION)
        assert play.isEnabled()
        assert delete.isEnabled()

        table = _table_of(window)
        index = _name_cell(table)
        table.openPersistentEditor(index)
        assert not play.isEnabled()
        assert not delete.isEnabled()

        table.closePersistentEditor(index)
        assert play.isEnabled()
        assert delete.isEnabled()

    def test_closing_the_video_under_an_editor_leaves_playback_disabled(
        self, window: MainWindow
    ) -> None:
        """Re-enabling on editor close must still respect "no video, no play"."""
        table = _table_of(window)
        index = _name_cell(table)
        table.openPersistentEditor(index)
        window.close_video()
        table.closePersistentEditor(index)

        assert not _action(window, PLAY_ACTION).isEnabled()
        assert _action(window, DELETE_ACTION).isEnabled()
