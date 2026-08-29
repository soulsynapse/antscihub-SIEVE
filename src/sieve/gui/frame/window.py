"""The window: a menu bar, three panes, and the boundaries between them.

Left/right boundary is a splitter (user-adjustable); bottom boundary is a seam
(fixed height). The left pane holds the canvas; the right holds a swipe of three
positions. Preferences and dev bench share one overlay over the panes.
"""

from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from sieve.contract.edges import FRAME, Access
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
from sieve.project import Library
from sieve.registry import load as load_tools
from sieve.relaunch import relaunch
from sieve.contract.nodes import Refusal
from sieve.store import Store, opened
from sieve.gui.view.canvas import Canvas
from sieve.gui.view.canvas.video_canvas import FrameView
from sieve.gui.view.dev import Dev
from sieve.gui.view.pipeline import Pipeline
from sieve.gui.view.preferences import Preferences
from sieve.gui.view.project_list import Project, ProjectList
from sieve.gui.view.step import Step
from sieve.gui.view.transport import Transport

#: Restore-down size (window opens maximized but needs a grabable restored state).
_WINDOW_WIDTH = 960
_WINDOW_HEIGHT = 540


class MainWindow(QMainWindow):
    #: An open runs on a worker and reports back through these. A widget
    #: touched from a worker thread is the crash, not a style point, so
    #: nothing crosses back except through a queued signal.
    source_opened = Signal(object)
    source_failed = Signal(str, str)

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
        self.frames = FrameView()
        self.canvas.show_content(self.frames)
        self.transport = Transport()
        self.bottom.body.addWidget(self.transport)
        self.transport.dragged.connect(self.guess_at)
        self.transport.released.connect(self.commit_at)
        self.transport.stepped.connect(self.commit_at)
        #: the recording that is open, if one is — closed before the next
        self.store: Store | None = None
        self._opening: str | None = None
        self.source_opened.connect(self._source_landed)
        self.source_failed.connect(self._source_broke)

        self.swipe = build_swipe("right")
        self.right.body.addWidget(self.swipe)

        self.library = Library()
        # Loaded once: which files can be opened is a question for the source
        # tools that are present, and SIEVE holds no list of its own.
        self.tools = load_tools()
        self.projects = ProjectList()
        self.swipe.position(POSITIONS.index("project")).body.addWidget(self.projects)
        self.projects.set_arrows(Arrows(self.swipe))
        self.projects.new.connect(self.new_project)
        self.projects.opened.connect(self.open_project)
        self.projects.removed.connect(self.remove_project)
        self.show_library()

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

    # -- the library -------------------------------------------------------

    def show_library(self, standing: str | None = None) -> None:
        """Redraw the list from the library, standing on *standing* if given.

        The library is the one copy: every verb writes there and then asks for
        this, rather than editing the cards and writing afterwards.
        """
        self.projects.show_projects(Project.of(entry) for entry in self.library.entries)
        if standing is None:
            return
        for index, project in enumerate(self.projects.projects()):
            if project.video == standing:
                self.projects.select(index)
                return

    def new_project(self) -> None:
        """The +: point at a recording, and that recording is the project.

        The picker is the mint. A project is a video file, so there is no name
        to ask for up front and nothing to create on disk — the file already
        exists, and what SIEVE gains is a row saying it has been shown one.

        Standing on the new row rather than opening it: opening slides to a
        chain the project does not have yet.

        A cancelled picker moves nothing, which is what makes the mint free to
        try: the selection stays where the user left it.

        Frames and not merely a source, at both the filter and the gate. A
        source is how *any* file enters — a crop document and a parameter
        document are sources too, and both are things a port gets bound to
        rather than things a project is about. Asking for the kind keeps this
        button meaning what it says once the second source tool lands.
        """
        chosen, _filter = QFileDialog.getOpenFileName(
            self,
            "Add a project — the recording it is about",
            "",
            self.tools.dialog_filter(FRAME),
        )
        if not chosen:
            return
        tool = self.tools.source_for(chosen, FRAME)
        if tool is None:
            # The filter is a hint and this is the gate, so a file picked
            # through "All files" is refused here rather than becoming a row
            # nothing can open.
            QMessageBox.warning(
                self,
                "No source tool takes that file",
                f"Nothing loaded reads frames out of {Path(chosen).name}.",
            )
            return
        entry = self.library.add(Path(chosen), source=tool.name)
        self.show_library(standing=entry.video)

    def open_project(self, project: Project) -> None:
        """A project's open: record that it was, slide to its chain, open it.

        The open itself is on a worker because it is not cheap and cannot be
        made cheap: ADR-0004 has the frame table built by demuxing the source
        at open, so a file's whole packet stream is read before it can say
        what it lists. Seconds of it, on the thread that draws, at the moment
        somebody clicked — which is the freeze the storage shelf exists to
        keep out of this loop.

        Which tool opens it is asked again rather than trusted from the row.
        The name recorded there says which one answered when the project was
        made; the search path may have changed since, and a tool that is no
        longer loaded has to fall back to whatever is.
        """
        self.library.touch(project.video)
        self.show_library(standing=project.video)
        self.swipe_forward()
        self._open_source(project.video)

    # -- the open recording ------------------------------------------------

    def _open_source(self, address: str) -> None:
        """Resolve a source for *address* and open it off the GUI thread."""
        if self.store is not None and self.store.address == address:
            return
        tool = self._source_for(address)
        if tool is None:
            self._source_broke(address, "nothing loaded reads frames out of it")
            return
        self._close_source()
        self._opening = address
        self.frames.show_frame(None)

        def work() -> None:
            # The walk to a first picture happens here too, not on the other
            # side of the signal: a file cut mid-GOP answers None for its
            # opening positions and charges a seek for each refusal, which is
            # seconds on the footage in `video-tests/`. Everything expensive
            # is on this side and the GUI thread is handed a frame.
            try:
                store = opened(tool, address)
                position = store.first_start()
                frame = None if position is None else store.frame(position)
            except Exception as trouble:  # noqa: BLE001 — a tool's failure is a fact
                self.source_failed.emit(address, str(trouble))
                return
            self.source_opened.emit((store, frame, position))

        threading.Thread(target=work, daemon=True).start()

    def _source_for(self, address: str):
        """The tool the library row named, or whatever answers now.

        Preferring the recorded name keeps a project on the producer it was
        made with when both are loaded — which is what a key over its output
        will have been folded under (ADR-0010).
        """
        entry = self.library.find(address)
        named = entry.source if entry is not None else ""
        if named:
            for tool in self.tools.offering(FRAME):
                if tool.name == named and tool.role.handles(address):
                    return tool
        return self.tools.source_for(address, FRAME)

    def _source_landed(self, landed: tuple) -> None:
        """An opened source and its first frame, back on the GUI thread."""
        store, frame, position = landed
        if store.address != self._opening:
            store.close()   # the user moved on while it was opening
            return
        self._opening = None
        self.store = store
        self.canvas.set_aspect(store.aspect)
        self.frames.show_frame(frame)
        self.transport.show_source(
            store.positions, store.starts(), store.output.edge.at.access
        )
        if position is not None:
            self.transport.show_playhead(position)

    # -- where the work is standing ----------------------------------------

    def guess_at(self, position: int) -> None:
        """A drag. Serve it from what is held, or leave the picture alone.

        The one rule the freeze hunt left with teeth: the GUI thread may block
        only for an exact request the user just released. Everything else
        serves a placeholder from a cheaper tier — and with one tier built, the
        cheapest thing available is the frame already on screen. A stale
        picture with a moving position under the cursor is the honest version
        of that; a 350 ms decode per drag step is the version that reads as
        frozen.
        """
        if self.store is None:
            return
        held = self.store.frames.get(position, self.store.form)
        if held is not None:
            self.frames.show_frame(held)

    def commit_at(self, position: int) -> None:
        """A release or a playback step. This one is paid for.

        Both go through here because both are exact — a step names the position
        it wants as squarely as a release does. What separates them is that a
        step is on a timer and will be along again, so a slow one delays the
        next rather than skipping it; nothing here computes anything, so
        nothing is lost by the picture arriving late.

        Only `GONE` blanks the canvas, and that is what `Refusal` is for. A
        forward-only source asked behind its head refuses `LATER` — the frame
        exists and this consumer cannot have it — and clearing the picture
        there would report a live source's whole past as empty. Stepping back
        with `,` on one is exactly that case, and it is reachable: the strip
        declines the gesture, the key does not.
        """
        if self.store is None:
            return
        answered = self.store.answer(position)
        if answered.delivered or answered.refusal is Refusal.GONE:
            self.frames.show_frame(answered.frame)

    def play_pause(self) -> None:
        self.transport.toggle_play()

    def step_back(self) -> None:
        self.transport.step(-1)

    def step_forward(self) -> None:
        self.transport.step(+1)

    def _source_broke(self, address: str, trouble: str) -> None:
        if address != self._opening and self._opening is not None:
            return
        self._opening = None
        self.frames.show_frame(None)
        QMessageBox.warning(
            self,
            "That recording could not be opened",
            f"{Path(address).name}: {trouble}",
        )

    def _close_source(self) -> None:
        if self.store is not None:
            self.store.close()
            self.store = None
        self.transport.show_source((), (), Access.RANDOM)

    def remove_project(self, project: Project) -> None:
        """A project's ✕: out of the library. The recording is not touched."""
        if self.store is not None and self.store.address == project.video:
            self._close_source()
            self.frames.show_frame(None)
        self.library.forget(project.video)
        self.show_library()

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
