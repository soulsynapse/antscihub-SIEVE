"""The window: what the parts are, and what the four navigation verbs mean.

The central widget is built exactly once — a canvas slot on the left, the
control track on the right (`layout.compose`). The track is never rebuilt
either, so which of its three positions is current survives every navigation;
only its contents are replaced.

**Where the walk is, is here.** The session layer holds the open project and
nothing about being looked at; the track holds which position is showing and
nothing about the graph. The index into `walk.node_order` belongs to neither
and would be duplicated into both if it lived in one of them, so the window
keeps it and hands it down on every redraw.

The canvas is `canvas.VideoCanvas`, fed frames by `transport/player.py`; the
scrubber under both halves is `timeline/bar.py`, which owns the working window
and is the only thing that tells the transport what it may reach.

Nothing here computes: opening a project reads a document, and the order the
graph walks in is `walk.py`'s, which is a question about the document's shape.
The `gui-computes-nothing` exception list is empty and stays empty.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMainWindow

from sieve.core.pipeline_model import Node
from sieve.gui.canvas import VideoCanvas
from sieve.gui.control import Control
from sieve.gui.hotkeys import bind_navigation_hotkeys
from sieve.gui.layout import CanvasSlot, compose, size_window
from sieve.gui.project_select import projects_in
from sieve.gui.timeline.bar import TimelineBar
from sieve.gui.transport.player import VideoPlayer
from sieve.gui.walk import node_order
from sieve.session.session import Session


class MainWindow(QMainWindow):
    def __init__(self, projects: Sequence[Path]) -> None:
        super().__init__()
        self.setWindowTitle("SIEVE")

        self._projects = tuple(projects)
        self._session: Session | None = None
        self._order: tuple[Node, ...] = ()
        self._at = 0

        self._player = VideoPlayer(self)
        self._viewport = VideoCanvas()
        self._player.frame_changed.connect(self._viewport.set_frame)
        self._timeline = TimelineBar(self._player)

        self._canvas = CanvasSlot(self._viewport)
        self._control = Control(self._projects)
        self._control.project_chosen.connect(self.open_project)
        self.setCentralWidget(compose(self._canvas, self._control, self._timeline))

        bind_navigation_hotkeys(self)

    @property
    def player(self) -> VideoPlayer:
        """The transport. Exposed for the timeline's tests and for shutdown."""
        return self._player

    @property
    def timeline(self) -> TimelineBar:
        """The scrubber across the bottom."""
        return self._timeline

    @property
    def session(self) -> Session | None:
        """The open project, or `None` before one is chosen.

        There is no `Session` for "nothing open" by decision — which screen a
        front end shows before a project exists is view state (`session.py`), so
        the absence is spelt here, where the view state lives.
        """
        return self._session

    @property
    def control(self) -> Control:
        return self._control

    @property
    def current_node(self) -> Node | None:
        """The node Up and Down are on, or `None` if the graph is empty."""
        if not self._order:
            return None
        return self._order[self._at]

    def open_project(self, path: Path) -> None:
        """Open the document at `path` and land on the pipeline position.

        The walk restarts at the first node rather than resuming: where the
        previous project's walk had reached is a position in a different graph,
        and carrying the index across would land on whichever node happened to
        share its ordinal.

        Raises:
            OSError: if `path` cannot be read.
            ValidationError: if the document is structurally invalid.
        """
        self._session = Session.open(path)
        self._order = node_order(self._session.project.pipeline)
        self._at = 0
        # The path is resolved against the project's own directory and handed
        # over as a string: whether the file is there is the decode thread's
        # answer to give, and a check here would be a second one that could
        # disagree with it.
        self._player.open(str(self._session.project.source.resolve(path.parent)))
        self._control.show_graph(self._order, self._at)
        self._control.show_pipeline()

    def closeEvent(self, event: object) -> None:
        """Stop the decode thread before the window goes.

        A `QThread` still running when its `QObject` is finalised takes the
        process down, which turns closing the app into a crash report.
        """
        self._player.shutdown()
        super().closeEvent(event)  # type: ignore[arg-type]

    def go_back(self) -> None:
        """Left: step to pipeline, pipeline to project select.

        A no-op at the project position — there is nothing further back, and the
        session underneath it is left open so that Right returns to exactly the
        node the walk was on.
        """
        position = self._control.current_position()
        if position == "step":
            self._control.show_pipeline()
        elif position == "pipeline":
            self._control.show_project_select(self._projects)

    def go_forward(self) -> None:
        """Right: project select to pipeline, pipeline to step.

        A no-op at the project position with nothing open — there is no
        workspace to move into until a project has been chosen.
        """
        position = self._control.current_position()
        if position == "project":
            if self._session is not None:
                self._control.show_pipeline()
        elif position == "pipeline":
            self._control.show_step()

    def go_up(self) -> None:
        """Up: the previous node in the walk, or stay on the first."""
        self._walk_to(self._at - 1)

    def go_down(self) -> None:
        """Down: the next node in the walk, or stay on the last."""
        self._walk_to(self._at + 1)

    def _walk_to(self, index: int) -> None:
        # Clamped rather than wrapped, and silent at either end: a held key
        # reaching the last node is ordinary use, and wrapping would move the
        # canvas and the step pane to the far end of the graph for a keystroke
        # the user meant as "no further".
        if not self._order:
            return
        self._at = max(0, min(index, len(self._order) - 1))
        self._control.show_graph(self._order, self._at)


def main() -> None:
    application = QApplication(sys.argv)
    window = MainWindow(projects_in(Path.cwd()))
    size_window(window)
    sys.exit(application.exec())
