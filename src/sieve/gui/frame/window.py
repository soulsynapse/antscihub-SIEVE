"""The window: three compartments and the boundaries between them.

Two of the three boundaries are different in kind and the frame is where that
difference is stated. Canvas against controls is a splitter — how much room the
footage gets against the chain is the user's, and it is the trade they make
most often. Timeline against both is a seam: the strip is a fixed height,
because what it draws is the whole asset at a size the layout does not get a
say in.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QSplitter, QVBoxLayout, QWidget

from sieve.gui.frame.chrome import stylesheet
from sieve.gui.frame.compartments import (
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

        # Even stretch, and an even split to start: neither surface is the
        # window's main one. The chain is tuned by reading a plot against the
        # footage, so a frame that gave either the remainder of a resize would
        # be answering a question the user answers by dragging.
        self.split = QSplitter(Qt.Orientation.Horizontal)
        self.split.addWidget(self.canvas)
        self.split.addWidget(self.controls)
        self.split.setStretchFactor(0, 1)
        self.split.setStretchFactor(1, 1)
        self.split.setSizes([_WINDOW_WIDTH // 2, _WINDOW_WIDTH // 2])
        self.split.setChildrenCollapsible(False)

        stacked = QWidget()
        column = QVBoxLayout(stacked)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        column.addWidget(self.split, 1)
        column.addWidget(build_seam())
        column.addWidget(self.timeline)
        self.setCentralWidget(stacked)

        self.resize(_WINDOW_WIDTH, _WINDOW_HEIGHT)
        self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)
