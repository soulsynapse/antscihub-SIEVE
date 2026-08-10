"""The bar across the top, and what the window itself can be asked to do.

The menu is the frame's, not a pane's: everything on it acts on the
window or on the project the window is showing, and nothing on it belongs to
the canvas, the chain or the timeline — those are acted on where they are
drawn. That line is what keeps the bar from becoming the place every surface
hangs its overflow.

Entries whose target does not exist yet are built and disabled rather than
left out. A bar that grows an item per commit tells the reader nothing about
what the application is; one that shows its shape from the start, greyed where
the wiring has not landed, is the same checkable claim the empty panes
make.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenuBar, QMessageBox

if TYPE_CHECKING:  # importing it for real would close the loop back to `window`
    from sieve.gui.frame.window import MainWindow

#: What each menu holds, as (title, entries), where an entry is a label, the
#: method name on the window that answers it, and a shortcut — or `None` in
#: place of the method for something the frame cannot do yet. A separator is a
#: bare `None` in the entry list.
_MENUS: tuple[tuple[str, tuple[tuple[str, str | None, str] | None, ...]], ...] = (
    (
        "&File",
        (
            ("&New project…", None, "Ctrl+N"),
            ("&Open project…", None, "Ctrl+O"),
            ("&Save project", None, "Ctrl+S"),
            None,
            ("Open &video…", None, "Ctrl+Shift+O"),
            None,
            ("&Preferences…", None, "Ctrl+,"),
            None,
            ("E&xit", "close", "Ctrl+Q"),
        ),
    ),
    (
        "&View",
        (
            ("&Even split", "even_split", "Ctrl+0"),
            ("&Full screen", "toggle_full_screen", "F11"),
        ),
    ),
    (
        "&Help",
        (("&About SIEVE", "about", ""),),
    ),
)


def build_menu_bar(window: MainWindow) -> QMenuBar:
    """The bar, with every action bound to the window that will carry it."""
    bar = QMenuBar(window)
    bar.setObjectName("menubar")
    # The bar is the window's own, never the platform's shared one: on a native
    # menu bar the entries leave the window they act on, and the dark chrome
    # below would then stop at a system-coloured strip.
    bar.setNativeMenuBar(False)
    for title, entries in _MENUS:
        menu = bar.addMenu(title)
        for entry in entries:
            if entry is None:
                menu.addSeparator()
                continue
            label, method, shortcut = entry
            action = QAction(label, window)
            if shortcut:
                action.setShortcut(shortcut)
            if method is None:
                action.setEnabled(False)
            else:
                action.triggered.connect(getattr(window, method))
            menu.addAction(action)
    return bar


def show_about(window: MainWindow) -> None:
    """What the application is, for a user who has to name it in a method."""
    QMessageBox.about(
        window,
        "About SIEVE",
        "<b>SIEVE</b><br><br>"
        "Isolates ethological events from video: a chain of steps read against "
        "the footage, tuned by hand, and run over the whole asset.",
    )
