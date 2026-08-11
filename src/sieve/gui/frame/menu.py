"""The bar across the top, and what the window itself can be asked to do.

The menu is the frame's, not a pane's: everything on it acts on the
window or on the project the window is showing, and nothing on it belongs to
the footage, the chain or the timeline — those are acted on where they are
drawn. That line is what keeps the bar from becoming the place every view
hangs its overflow.

Not every title on the bar drops. One whose whole content is a single verb —
preferences is the first — is a plain action sitting on the bar: it is drawn by
the same rule as the titles beside it, so the bar reads as one row of the same
kind of thing, and clicking it does the verb instead of opening a list of one.
A one-entry menu would cost a second click to say nothing, and would claim more
is under it than ever will be.

Entries whose target does not exist yet are built and disabled rather than
left out. A bar that grows an item per commit tells the reader nothing about
what the application is; one that shows its shape from the start, greyed where
the wiring has not landed, is the same checkable claim the empty panes
make.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenuBar, QMessageBox

if TYPE_CHECKING:  # importing it for real would close the loop back to `window`
    from sieve.gui.frame.window import MainWindow

#: A line inside a drop: a label, the method name on the window that answers it,
#: and a shortcut — or `None` in place of the method for something the frame
#: cannot do yet. A separator is a bare `None` where an entry would be.
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


#: The bar, left to right. Preferences sits between the window's own views and
#: the help, where a File menu would otherwise have buried it: it is about the
#: application rather than about a project, and the bar is the only place that
#: distinction is already drawn.
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
    Button("&Preferences", "open_preferences", "Ctrl+,"),
    Drop(
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
    """One thing the bar offers, wherever on the bar it is offered.

    The same builder for a line in a drop and for a title that is one: what
    differs between them is where they are added, and nothing about what they
    are — which is what keeps a button on the bar from being a second kind of
    entry with its own rules for shortcuts and for being greyed out.
    """
    action = QAction(label, window)
    if shortcut:
        action.setShortcut(shortcut)
    if method is None:
        action.setEnabled(False)
    else:
        action.triggered.connect(getattr(window, method))
    return action


def show_about(window: MainWindow) -> None:
    """What the application is, for a user who has to name it in a method."""
    QMessageBox.about(
        window,
        "About SIEVE",
        "<b>SIEVE</b><br><br>"
        "Isolates ethological events from video: a chain of steps read against "
        "the footage, tuned by hand, and run over the whole asset.",
    )
