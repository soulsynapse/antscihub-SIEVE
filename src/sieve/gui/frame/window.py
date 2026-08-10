"""The window: a menu bar, three panes, and the boundaries between them.

The panes are named for where they sit, not for what they will hold; the reason
is `panes.py`'s, and the same word doing both jobs is why this file says "the
left pane" and "the left side" and never just "left".

Two of the three boundaries are different in kind and the frame is where that
difference is stated. Left against right is a splitter — how much room the
footage gets against the chain is the user's, and it is the trade they make
most often. The bottom against both is a seam: the strip is a fixed height,
because what it will draw is the whole asset at a size the layout does not get
a say in. The menu bar sits above all three and is a boundary of neither kind —
it acts on the window, not on what any pane holds.

A subpane adds a boundary of the seam's kind one level in, and on the axis its
pane's outer boundary left alone — the top and bottom sides in the left and
right panes, the left and right sides in the bottom one. Which sides those are
is the pane's own and stated there; the window opens none of them, and the
resting frame is the three panes and the two boundaries between them.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QSplitter, QVBoxLayout, QWidget

from sieve.gui.frame.chrome import stylesheet
from sieve.gui.frame.menu import build_menu_bar, show_about
from sieve.gui.frame.panes import (
    build_bottom,
    build_left,
    build_right,
    build_seam,
)

#: What the window restores down *to*. Kept even though it opens maximized:
#: without it the restored size — and with it whether the title bar can be
#: grabbed at all — is whatever Qt picks from the layout's size hint.
_WINDOW_WIDTH = 960
_WINDOW_HEIGHT = 540


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SIEVE")
        self.setStyleSheet(stylesheet())

        self.left = build_left()
        self.right = build_right()
        self.bottom = build_bottom()

        # No subpane is opened on the way up. Which sides each pane offers is
        # still the pane's claim and still checkable by asking it, but a strip
        # standing blank in every pane costs room in all three and shows a
        # boundary where the resting frame has none. They are attached where a
        # view asks for one — the resting frame is three panes, not nine.

        # Even stretch, and an even split to start: neither view is the
        # window's main one. The chain is tuned by reading a plot against the
        # footage, so a frame that gave either the remainder of a resize would
        # be answering a question the user answers by dragging.
        self.split = QSplitter(Qt.Orientation.Horizontal)
        self.split.addWidget(self.left)
        self.split.addWidget(self.right)
        self.split.setStretchFactor(0, 1)
        self.split.setStretchFactor(1, 1)
        self.split.setChildrenCollapsible(False)
        self.even_split()

        stacked = QWidget()
        column = QVBoxLayout(stacked)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        column.addWidget(self.split, 1)
        column.addWidget(build_seam())
        column.addWidget(self.bottom)
        self.setCentralWidget(stacked)
        self.setMenuBar(build_menu_bar(self))

        self.resize(_WINDOW_WIDTH, _WINDOW_HEIGHT)
        self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)

    def even_split(self) -> None:
        """Hand the panes the same width, whatever the window is now.

        Halving the splitter's own width rather than the window's: by the time
        a user asks for this the window has been resized and the two numbers
        have parted, and the sizes are read back against the splitter.
        """
        half = max(self.split.width(), _WINDOW_WIDTH) // 2
        self.split.setSizes([half, half])

    def toggle_full_screen(self) -> None:
        """Full screen and back, without deciding what 'back' is.

        `showNormal` would restore *down*, losing a maximized window's state;
        the frame opens maximized, so leaving full screen has to put back the
        state the window was actually in.
        """
        if self.isFullScreen():
            self.setWindowState(self.windowState() & ~Qt.WindowState.WindowFullScreen)
        else:
            self.setWindowState(self.windowState() | Qt.WindowState.WindowFullScreen)

    def about(self) -> None:
        show_about(self)
