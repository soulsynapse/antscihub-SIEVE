"""The bar across the top, and what the window itself can be asked to do.

A title whose whole content is a single verb (Preferences) is a plain action on
the bar rather than a one-entry drop. Entries whose wiring has not landed are
built disabled, not left out.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenuBar, QMessageBox

if TYPE_CHECKING:  # importing it for real would close the loop back to `window`
    from sieve.gui.frame.window import MainWindow

#: (label, method-or-None, shortcut). A bare None in a drop's entries is a separator.
Entry = tuple[str, str | None, str]


class Drop(NamedTuple):
    """A title on the bar that opens a list under it."""

    title: str
    entries: tuple[Entry | None, ...]


class Button(NamedTuple):
    """A title on the bar that carries out its one verb when clicked."""

    label: str
    method: str | None
    shortcut: str


#: Named apart so `preferences_anchor` can find its geometry.
_PREFERENCES = Button("&Preferences", "toggle_preferences", "Ctrl+,")

_BAR: tuple[Drop | Button, ...] = (
    Drop(
        "&File",
        (
            ("&New project…", None, "Ctrl+N"),
            ("&Open project…", None, "Ctrl+O"),
            ("&Save project", None, "Ctrl+S"),
            None,
            ("Open &video…", None, "Ctrl+Shift+O"),
            None,
            ("E&xit", "close", "Ctrl+Q"),
        ),
    ),
    Drop(
        "&View",
        (
            ("&Even split", "even_split", "Ctrl+0"),
            ("&Full screen", "toggle_full_screen", "F11"),
        ),
    ),
    _PREFERENCES,
    #: Ctrl+D lives on the QAction, not in hotkeys.py — duplicating it is ambiguous.
    Drop(
        "&Help",
        (
            ("&Dev view", "open_dev", "Ctrl+D"),
            None,
            ("&About SIEVE", "about", ""),
        ),
    ),
)


def build_menu_bar(window: MainWindow) -> QMenuBar:
    """The bar, with every action bound to the window that will carry it."""
    bar = QMenuBar(window)
    bar.setObjectName("menubar")
    bar.setNativeMenuBar(False)  # native bar leaves the window's chrome
    for item in _BAR:
        if isinstance(item, Button):
            bar.addAction(_action(window, item.label, item.method, item.shortcut))
            continue
        menu = bar.addMenu(item.title)
        for entry in item.entries:
            if entry is None:
                menu.addSeparator()
                continue
            menu.addAction(_action(window, *entry))
    return bar


def _action(
    window: MainWindow, label: str, method: str | None, shortcut: str
) -> QAction:
    """Build one action — same shape for drops and bar-level buttons."""
    action = QAction(label, window)
    if shortcut:
        action.setShortcut(shortcut)
    if method is None:
        action.setEnabled(False)
    else:
        action.triggered.connect(getattr(window, method))
    return action


def preferences_anchor(bar: QMenuBar) -> int:
    """X offset of the Preferences title, read from the laid-out bar."""
    for action in bar.actions():
        if action.text() == _PREFERENCES.label:
            return bar.actionGeometry(action).left()
    return 0


def show_about(window: MainWindow) -> None:
    QMessageBox.about(
        window,
        "About SIEVE",
        "<b>SIEVE</b><br><br>"
        "Isolates ethological events from video: a chain of steps read against "
        "the footage, tuned by hand, and run over the whole asset.",
    )
