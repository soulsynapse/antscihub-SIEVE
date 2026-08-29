"""The window: a menu bar, three panes, and the boundaries between them.

Left/right boundary is a splitter (user-adjustable); bottom boundary is a seam
(fixed height). The left pane holds the canvas; the right holds a swipe of three
positions. Preferences and dev bench share one overlay over the panes.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QSplitter, QVBoxLayout, QWidget

from sieve.gui import palette
from sieve.gui.frame.chrome import dress_title_bar, stylesheet
from sieve.gui.frame.hotkeys import answer_key, bind_hotkeys, suspend_hotkeys
from sieve.gui.frame.menu import build_menu_bar, preferences_anchor, show_about
from sieve.gui.frame.overlay import Overlay
from sieve.gui.frame.panes import (
    build_bottom,
    build_left,
    build_right,
    build_seam,
)
from sieve.gui.frame.swipe import POSITIONS, Arrows, build_swipe
from sieve.relaunch import relaunch
from sieve.gui.view.canvas import Canvas
from sieve.gui.view.dev import Dev
from sieve.gui.view.pipeline import Pipeline
from sieve.gui.view.preferences import Preferences
from sieve.gui.view.project_list import ProjectList
from sieve.gui.view.step import Step

#: Restore-down size (window opens maximized but needs a grabable restored state).
_WINDOW_WIDTH = 960
_WINDOW_HEIGHT = 540


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SIEVE")
        self._restyle()
        palette.CHANGED.connect(self._restyle)

        self.left = build_left()
        self.right = build_right()
        self.bottom = build_bottom()

        self.canvas = Canvas()
        self.left.body.addWidget(self.canvas)

        self.swipe = build_swipe("right")
        self.right.body.addWidget(self.swipe)

        self.projects = ProjectList()
        self.swipe.position(POSITIONS.index("project")).body.addWidget(self.projects)
        self.projects.set_arrows(Arrows(self.swipe))
        self.projects.opened.connect(lambda _project: self.swipe_forward())

        self.pipeline = Pipeline()
        self.swipe.position(POSITIONS.index("pipeline")).body.addWidget(self.pipeline)
        self.pipeline.set_arrows(Arrows(self.swipe))

        self.step = Step()
        self.swipe.position(POSITIONS.index("step")).body.addWidget(self.step)
        self.step.set_arrows(Arrows(self.swipe))

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
        self.bar = build_menu_bar(self)
        self.setMenuBar(self.bar)
        self.hotkeys = bind_hotkeys(self)

        self.overlay = Overlay(stacked)
        self.preferences = Preferences()
        self.dev = Dev()
        for view in (self.preferences, self.dev):
            self.overlay.body.addWidget(view)
            view.closed.connect(self.close_overlay)
        self.overlay.dismissed.connect(lambda: suspend_hotkeys(self.hotkeys, False))

        self.resize(_WINDOW_WIDTH, _WINDOW_HEIGHT)
        self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)

    def keyPressEvent(self, event) -> None:
        if answer_key(self.hotkeys, event):
            event.accept()
            return
        super().keyPressEvent(event)

    def _restyle(self) -> None:
        """Reapply stylesheet and repaint all children (paintEvent widgets need an explicit update)."""
        self.setStyleSheet(stylesheet())
        for child in self.findChildren(QWidget):
            child.update()
        self.update()
        dress_title_bar(self)

    def even_split(self) -> None:
        half = max(self.split.width(), _WINDOW_WIDTH) // 2
        self.split.setSizes([half, half])

    def swipe_back(self) -> None:
        self.swipe.step(-1)

    def swipe_forward(self) -> None:
        self.swipe.step(+1)

    def reload(self) -> None:
        """Close and relaunch — process is replaced, nothing after this runs."""
        self.close()
        relaunch()

    def toggle_full_screen(self) -> None:
        """Toggle fullscreen via flags (showNormal would lose the maximized state)."""
        if self.isFullScreen():
            self.setWindowState(self.windowState() & ~Qt.WindowState.WindowFullScreen)
        else:
            self.setWindowState(self.windowState() | Qt.WindowState.WindowFullScreen)

    def toggle_preferences(self) -> None:
        """Toggle preferences overlay, anchored under the bar title."""
        if self.overlay.showing(self.preferences):
            self.close_overlay()
            return
        self._raise(self.preferences, preferences_anchor(self.bar))

    def open_dev(self) -> None:
        """Show the dev bench centred (no bar title to anchor to)."""
        self._raise(self.dev, None)

    def _raise(self, view: QWidget, left: int | None) -> None:
        """Suspend hotkeys and raise `view` on the overlay."""
        suspend_hotkeys(self.hotkeys, True)
        self.overlay.stand(view)
        self.overlay.raise_over(left)

    def close_overlay(self) -> None:
        self.overlay.dismiss()

    def about(self) -> None:
        show_about(self)
