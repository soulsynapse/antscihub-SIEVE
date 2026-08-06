"""Enter and Esc give the spacebar back.

The editing guard (`tests/gui/test_editing_guard.py`) pins that the Play action
is *enabled* again at a commit. That is not the same as the spacebar working:
a focused spin box accepts the `ShortcutOverride` for Space, so the shortcut
never fires while the field holds the keyboard. The first test here states that
mechanism directly, because everything else in this file only matters if it is
true — and if Qt ever changes it, this file should say so rather than quietly
testing a filter nobody needs.

The other load-bearing claim is *order*: the handback is deferred by a turn of
the event loop so that Esc still abandons. Clearing focus in place would
deliver a focus-out, which is a commit, and Esc would write the number it was
pressed to discard.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from pytestqt.qtbot import QtBot

from sieve.core.types import ROI
from sieve.gui.document import ReplicateDocument
from sieve.gui.keyboard_handback import KeyboardHandback
from sieve.gui.replicate_tab import ReplicateTab
from sieve.gui.transport.player import VideoPlayer

pytestmark = pytest.mark.gui

BOX = ROI(x=10, y=20, width=100, height=80)
PLAY = "play"


class _Window(QMainWindow):
    """A spin box and a Play/Pause on the spacebar — the collision, minimally."""

    def __init__(self) -> None:
        super().__init__()
        central = QWidget()
        layout = QVBoxLayout(central)
        self.spin = QSpinBox()
        self.spin.setRange(0, 999)
        self.spin.setValue(100)
        self.spin.setKeyboardTracking(False)
        layout.addWidget(self.spin)
        self.setCentralWidget(central)

        self.fired = 0
        self.play = QAction(PLAY, self)
        self.play.setShortcut(QKeySequence(" "))
        self.play.triggered.connect(self._on_play)
        self.addAction(self.play)

    def _on_play(self) -> None:
        self.fired += 1


@pytest.fixture
def handback(qapp: QApplication) -> Iterator[KeyboardHandback]:
    """Installed on the application, as `gui/app.py` installs it."""
    instance = KeyboardHandback()
    qapp.installEventFilter(instance)
    yield instance
    qapp.removeEventFilter(instance)


@pytest.fixture
def window(qtbot: QtBot) -> _Window:
    """Shown and activated — without activation nothing can hold focus."""
    main = _Window()
    qtbot.addWidget(main)
    main.show()
    handle = main.windowHandle()
    assert handle is not None
    handle.requestActivate()
    qtbot.waitUntil(lambda: main.isActiveWindow(), timeout=5_000)
    return main


def _type(window: _Window, digits: str) -> None:
    window.spin.setFocus()
    window.spin.lineEdit().selectAll()
    QTest.keyClicks(window.spin, digits)


def test_a_focused_spin_box_swallows_the_spacebar(window: _Window) -> None:
    """No filter installed: this is the defect, and the reason for the rest.

    The action is enabled the whole time. Qt hands the key to the field
    regardless, so "Play is available" and "Space plays" are two different
    claims — which is what makes the enabled menu item a control that looks
    more live than it is.
    """
    window.spin.setFocus()
    assert window.play.isEnabled()

    QTest.keyClick(window.spin, Qt.Key.Key_Space)

    assert window.fired == 0


@pytest.mark.parametrize("key", [Qt.Key.Key_Return, Qt.Key.Key_Escape])
def test_the_spacebar_works_again_after_an_exit(
    window: _Window, handback: KeyboardHandback, qtbot: QtBot, key: Qt.Key
) -> None:
    del handback
    _type(window, "15")
    QTest.keyClick(window.spin, key)

    qtbot.waitUntil(lambda: QApplication.focusWidget() is None, timeout=5_000)
    QTest.keyClick(window, Qt.Key.Key_Space)

    assert window.fired == 1


def test_enter_still_commits_what_was_typed(
    window: _Window, handback: KeyboardHandback, qtbot: QtBot
) -> None:
    """The handback must not undo the exit it follows."""
    del handback
    _type(window, "15")
    QTest.keyClick(window.spin, Qt.Key.Key_Return)

    qtbot.waitUntil(lambda: QApplication.focusWidget() is None, timeout=5_000)

    assert window.spin.value() == 15


def test_a_field_destroyed_before_the_turn_of_the_loop_is_not_touched(
    window: _Window, handback: KeyboardHandback, qtbot: QtBot
) -> None:
    """The pending call is the widget's, so it dies with the widget.

    Reachable in the application: a tool panel collapses or a tab changes on
    the same commit that ends the edit.
    """
    del handback
    _type(window, "15")
    QTest.keyClick(window.spin, Qt.Key.Key_Return)
    window.spin.deleteLater()

    qtbot.wait(50)


class TestEscapeStillAbandons:
    """The order claim, on the field that has something to abandon.

    A plain `QSpinBox` ignores Esc, so it cannot show this: only
    `crop_tools._NumberField` reverts, and only it would have the revert
    overwritten by a focus-out delivered too early.
    """

    @pytest.fixture
    def tab(self, qtbot: QtBot, document: ReplicateDocument) -> Iterator[ReplicateTab]:
        player = VideoPlayer()
        widget = ReplicateTab(player, document)
        qtbot.addWidget(widget)
        document.add_roi(BOX)
        widget.show()
        yield widget
        player.shutdown()

    def test_escape_writes_nothing_and_still_releases_the_keyboard(
        self,
        tab: ReplicateTab,
        document: ReplicateDocument,
        handback: KeyboardHandback,
        qtbot: QtBot,
    ) -> None:
        del handback
        field = tab.tools_panel.findChild(QSpinBox, "roi-width")
        assert isinstance(field, QSpinBox)

        field.setFocus()
        field.lineEdit().selectAll()
        QTest.keyClicks(field, "15")
        QTest.keyClick(field, Qt.Key.Key_Escape)

        qtbot.waitUntil(lambda: not field.hasFocus(), timeout=5_000)

        assert document.at(0).roi.width == BOX.width
