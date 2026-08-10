"""The window: a menu bar, three panes, and the boundaries between them.

Two of the three boundaries are different in kind and the frame is where that
difference is stated. Canvas against controls is a splitter — how much room the
footage gets against the chain is the user's, and it is the trade they make
most often. Timeline against both is a seam: the strip is a fixed height,
because what it draws is the whole asset at a size the layout does not get a
say in. The menu bar sits above all three and is a boundary of neither kind —
it acts on the window, not on what any pane holds.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QSplitter, QVBoxLayout, QWidget

from sieve.gui.frame.chrome import stylesheet
from sieve.gui.frame.menu import build_menu_bar, show_about
from sieve.gui.frame.panes import (
    build_canvas,
    build_controls,
    build_seam,
    build_timeline,
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

        self.canvas = build_canvas()
        self.controls = build_controls()
        self.timeline = build_timeline()

        # Even stretch, and an even split to start: neither view is the
        # window's main one. The chain is tuned by reading a plot against the
        # footage, so a frame that gave either the remainder of a resize would
        # be answering a question the user answers by dragging.
        self.split = QSplitter(Qt.Orientation.Horizontal)
        self.split.addWidget(self.canvas)
        self.split.addWidget(self.controls)
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
        column.addWidget(self.timeline)
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
