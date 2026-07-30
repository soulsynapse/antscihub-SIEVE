"""The guard that stops window shortcuts eating a keystroke meant for a field.

Qt dispatches window shortcuts before the focused widget sees the key, so
without this guard typing a space into a replicate name starts playback and
pressing Delete removes the row being renamed. The delegate and the crop-tools
fields announce themselves *by name*, the tab keeps the set of them, and the
window disables the colliding actions while that set is non-empty. Each link is
tested on its own, then the whole chain through a real window with a real video
open — the failure this prevents only exists once all three are wired together.

Two things this file is written against, both of them defects the earlier
one-boolean version had:

- **A close from one source must not clear another's live claim.** Two editors
  open, the second closing first, still leaves the keys with the first.
- **Focus is not an edit.** Clicking into a number field and clicking away
  again — or having it hidden mid-type — must leave playback exactly where it
  found it. The old latch suppressed on focus, and any focus-out that never
  arrived stranded playback for the rest of the session.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QModelIndex, QPointF, QSettings, Qt
from PySide6.QtGui import QAction, QFocusEvent, QKeyEvent
from PySide6.QtWidgets import QSpinBox, QTableView, QWidget
from pytestqt.qtbot import QtBot

from sieve.core.types import ROI
from sieve.gui.document import ReplicateDocument
from sieve.gui.editing_sources import EditingSources
from sieve.gui.main_window import MainWindow
from sieve.gui.player import VideoPlayer
from sieve.gui.preferences import Preferences
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


def _field(parent: QWidget, name: str) -> QSpinBox:
    field = parent.findChild(QSpinBox, name)
    assert isinstance(field, QSpinBox)
    return field


def _type(field: QSpinBox, digits: str) -> None:
    """Type `digits` into the field the way a keyboard would.

    Handed to the line edit rather than posted through `QTest`, matching
    `tests/gui/qt_input.py`: the offscreen platform has no real keyboard focus
    to route through, and what is under test is the field's reaction to
    `textEdited`, which this produces exactly as a keypress does.
    """
    editor = field.lineEdit()
    # Focusing a spin box selects its contents, so the first digit replaces
    # rather than appends. Doing it here keeps every test typing a whole number.
    editor.selectAll()
    for digit in digits:
        editor.keyPressEvent(
            QKeyEvent(
                QEvent.Type.KeyPress,
                Qt.Key(int(Qt.Key.Key_0) + int(digit)),
                Qt.KeyboardModifier.NoModifier,
                digit,
            )
        )


def _key(widget: QWidget, key: Qt.Key) -> None:
    widget.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier))


def _focus_out(widget: QWidget) -> None:
    """Leave the widget, which is what clicking somewhere else does to it."""
    widget.focusOutEvent(QFocusEvent(QEvent.Type.FocusOut))


def _action(window: MainWindow, text: str) -> QAction:
    matches = [action for action in window.findChildren(QAction) if action.text() == text]
    assert len(matches) == 1, f"no unique action titled {text!r}"
    return matches[0]


class TestEditingSources:
    """The arithmetic on its own, where the interleavings are cheap to state."""

    def test_a_close_from_one_source_leaves_another_live(self) -> None:
        sources = EditingSources()
        sources.mark("a", True)
        sources.mark("b", True)

        sources.mark("b", False)

        assert sources.active
        assert sources.sources == frozenset({"a"})

    def test_an_unbalanced_close_is_ignored_rather_than_going_negative(self) -> None:
        """The case a counter gets wrong: two closes for one open.

        A counter would sit at -1 and then swallow the *next* real open. The
        set has nothing to subtract from, so it simply stays empty.
        """
        sources = EditingSources()
        sources.mark("a", True)
        sources.mark("a", False)
        sources.mark("a", False)

        sources.mark("b", True)

        assert sources.active


class TestEditingAwareDelegate:
    @pytest.fixture
    def table(self, qtbot: QtBot, document: ReplicateDocument) -> QTableView:
        document.add_roi(BOX)
        document.add_roi(BOX)
        view = QTableView()
        qtbot.addWidget(view)
        view.setModel(ReplicateTableModel(document, view))
        view.setItemDelegate(EditingAwareDelegate(view))
        return view

    @staticmethod
    def _delegate(table: QTableView) -> EditingAwareDelegate:
        delegate = table.itemDelegate()
        assert isinstance(delegate, EditingAwareDelegate)
        return delegate

    def test_an_editor_is_announced_when_it_opens_and_closes(self, table: QTableView) -> None:
        started: list[str] = []
        finished: list[str] = []
        delegate = self._delegate(table)
        delegate.editing_started.connect(started.append)
        delegate.editing_finished.connect(finished.append)

        index = _name_cell(table)
        table.openPersistentEditor(index)
        assert (len(started), len(finished)) == (1, 0)

        table.closePersistentEditor(index)
        assert finished == started

    def test_two_open_editors_are_named_apart(self, table: QTableView) -> None:
        """Two identical keys would make either close look like both."""
        started: list[str] = []
        self._delegate(table).editing_started.connect(started.append)

        model = table.model()
        assert model is not None
        table.openPersistentEditor(model.index(0, int(Column.NAME)))
        table.openPersistentEditor(model.index(1, int(Column.NAME)))

        assert len(set(started)) == 2


class TestTabRelay:
    @pytest.fixture
    def tab(self, qtbot: QtBot, document: ReplicateDocument) -> Iterator[ReplicateTab]:
        player = VideoPlayer()
        widget = ReplicateTab(player, document)
        qtbot.addWidget(widget)
        document.add_roi(BOX)
        yield widget
        player.shutdown()

    def test_the_tab_reports_the_editor_state(self, tab: ReplicateTab) -> None:
        table = _table_of(tab)

        states: list[bool] = []
        tab.editing_changed.connect(states.append)

        index = _name_cell(table)
        table.openPersistentEditor(index)
        table.closePersistentEditor(index)

        assert states == [True, False]

    def test_the_second_editor_closing_first_does_not_hand_the_keys_back(
        self, tab: ReplicateTab
    ) -> None:
        """The defect this item was filed for, in its smallest form.

        A cell editor and a crop-tools field are independent sources. Close
        them out of order and the boolean latch this replaced would report
        "nothing is being edited" while the field still held a half-typed
        number — or, with the two swapped, would never report it at all.
        """
        table = _table_of(tab)
        field = _field(tab.tools_panel, "roi-width")

        states: list[bool] = []
        tab.editing_changed.connect(states.append)

        index = _name_cell(table)
        table.openPersistentEditor(index)
        _type(field, "1")
        table.closePersistentEditor(index)

        assert states == [True]

        _key(field, Qt.Key.Key_Escape)
        assert states == [True, False]


class TestCommitBoundary:
    """A number field's value, and its claim on the keys, move together.

    The decision this implements is in
    An edit begins
    at a keystroke and ends at a commit, and there are exactly three commits —
    Enter, Esc, and leaving the field.
    """

    @pytest.fixture
    def tab(self, qtbot: QtBot, document: ReplicateDocument) -> Iterator[ReplicateTab]:
        player = VideoPlayer()
        widget = ReplicateTab(player, document)
        qtbot.addWidget(widget)
        document.add_roi(BOX)
        yield widget
        player.shutdown()

    @pytest.fixture
    def states(self, tab: ReplicateTab) -> list[bool]:
        recorded: list[bool] = []
        tab.editing_changed.connect(recorded.append)
        return recorded

    @pytest.fixture
    def width(self, tab: ReplicateTab) -> QSpinBox:
        return _field(tab.tools_panel, "roi-width")

    def test_holding_focus_without_typing_claims_nothing(
        self, width: QSpinBox, states: list[bool]
    ) -> None:
        """Clicking into a field and out again is not an edit.

        This is the whole point of the change: focus arriving and leaving used
        to be the signal, so any focus-out Qt did not deliver — a hidden
        widget, a collapsed panel — left playback disabled with nothing on
        screen to explain it.
        """
        width.focusInEvent(QFocusEvent(QEvent.Type.FocusIn))
        _focus_out(width)

        assert states == []

    def test_a_keystroke_claims_the_keys_and_enter_gives_them_back(
        self, width: QSpinBox, states: list[bool], document: ReplicateDocument
    ) -> None:
        _type(width, "15")
        assert states == [True]

        _key(width, Qt.Key.Key_Return)
        assert states == [True, False]
        assert document.at(0).roi.width == 15

    def test_a_partly_typed_number_never_reaches_the_document(
        self, width: QSpinBox, document: ReplicateDocument
    ) -> None:
        """`15` typed into a field showing `100` must not pass through `1`.

        A region one pixel wide is a legal `ROI`, so nothing downstream would
        refuse it: it would simply be rendered, cached under its own key, and
        left on the undo stack as a step the user never took.
        """
        _type(width, "15")

        assert document.at(0).roi.width == BOX.width

        _key(width, Qt.Key.Key_Return)
        assert document.at(0).roi.width == 15

    def test_escape_abandons_the_edit_and_writes_nothing(
        self, width: QSpinBox, states: list[bool], document: ReplicateDocument
    ) -> None:
        _type(width, "15")
        _key(width, Qt.Key.Key_Escape)

        assert states == [True, False]
        assert document.at(0).roi.width == BOX.width
        assert width.lineEdit().text() == str(BOX.width)

    def test_leaving_the_field_commits_it(
        self, width: QSpinBox, states: list[bool], document: ReplicateDocument
    ) -> None:
        """Clicking away is the third exit, and it is the one that agrees."""
        _type(width, "15")
        _focus_out(width)

        assert states == [True, False]
        assert document.at(0).roi.width == 15

    def test_a_field_hidden_mid_edit_hands_the_keys_back(
        self, tab: ReplicateTab, width: QSpinBox, states: list[bool]
    ) -> None:
        """No focus-out is delivered here, and the keys still come back.

        Collapsing the tool pane with a half-typed number in it is the reachable
        version of the stranded state — the widget is gone, so nothing is left
        to commit or cancel it.
        """
        tab.show()
        _type(width, "15")
        assert states == [True]

        tab.tools_panel.hide()

        assert states == [True, False]


class TestWindowShortcutGuard:
    @pytest.fixture
    def window(self, qtbot: QtBot, tmp_path: Path, synthetic_video: Path) -> Iterator[MainWindow]:
        """A shown window with the synthetic video open and one replicate drawn.

        Preferences on a temporary INI file: opening a video now records the
        path, and a test has no business writing that to the real store.
        """
        settings = QSettings(str(tmp_path / "sieve.ini"), QSettings.Format.IniFormat)
        main = MainWindow(Preferences(settings))
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

    def test_a_focused_number_field_does_not_stop_playback(self, window: MainWindow) -> None:
        """Clicking around the tool pane must leave the spacebar alone.

        The reported symptom: touch a field, and playback never comes back. It
        came back only when some *other* editor closed cleanly, which is why it
        read as permanent.
        """
        play = _action(window, PLAY_ACTION)
        field = _field(window, "roi-width")

        field.focusInEvent(QFocusEvent(QEvent.Type.FocusIn))
        assert play.isEnabled()

        _focus_out(field)
        assert play.isEnabled()

    def test_typing_a_number_still_yields_the_spacebar(self, window: MainWindow) -> None:
        """The behaviour worth keeping: a space typed at a number is not play."""
        play = _action(window, PLAY_ACTION)
        field = _field(window, "roi-width")

        _type(field, "50")
        assert not play.isEnabled()

        _key(field, Qt.Key.Key_Return)
        assert play.isEnabled()

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
