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

from sieve.chunks import ChunkStore
from sieve.contract.edges import FRAME, Access
from sieve.contract.forms import Form
from sieve.fill import Readers, WindowFill, WriteBehind, window_for
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
from sieve.serve import Ordinals, Route, Served, Serving
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

#: Positions a landing claims. The session explorer's ten-second tuning window,
#: in listed positions rather than seconds — a folder of stills has no seconds
#: and the transport already refuses to invent any.
WINDOW = 300

#: What the held frames may weigh, rather than how many there may be. The
#: explorer counted frames because it had one form and it was 1 MB; here the
#: same count is 300 MB of gray crop or 14 GB of source-form colour, so the
#: count is the wrong knob. A ceiling in bytes says the same thing about the
#: machine and survives the form changing under it.
_CACHE_BYTES = 600_000_000

#: A crop below this on either axis is a slip, not a gesture.
_MIN_CROP = 64


class MainWindow(QMainWindow):
    #: An open runs on a worker and reports back through these. A widget
    #: touched from a worker thread is the crash, not a style point, so
    #: nothing crosses back except through a queued signal.
    source_opened = Signal(object)
    source_failed = Signal(str, str)
    #: a fill finished, reported from the fill thread. Same rule as the open:
    #: nothing touches a widget except on the other side of a queued signal.
    window_covered = Signal(object)

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
        self.frames.drawn.connect(self.crop_drawn)
        self.canvas.show_content(self.frames)
        self.transport = Transport()
        self.bottom.body.addWidget(self.transport)
        self.transport.dragged.connect(self.guess_at)
        self.transport.released.connect(self.land_at)
        self.transport.stepped.connect(self.commit_at)
        #: the recording that is open, if one is — closed before the next
        self.store: Store | None = None
        self._opening: str | None = None
        self.source_opened.connect(self._source_landed)
        self.source_failed.connect(self._source_broke)
        self.window_covered.connect(self._covered)

        #: The crop the storage tiers hold, once one is drawn. `None` is the
        #: whole frame at source sampling, which is a form nothing can hold
        #: three hundred of — so until a crop exists a landing fills a dozen.
        self.crop: Form | None = None
        #: What the canvas shows. The crop is the working view once there is
        #: one; the whole frame is the marked exception, summoned to see
        #: context or to draw a different crop.
        self.whole = True
        #: The tiers of the open recording, and which one answered. It owns
        #: the ordinal snapshot, the chunks and the filled span, so the two
        #: questions this window used to ask apart — is there a crop, is the
        #: whole frame showing — become one question about a form.
        self.serving: Serving | None = None
        self.fill: WindowFill | None = None
        self.readers: Readers | None = None
        self.writer: WriteBehind | None = None
        self._at: int | None = None

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
        self.serving = Serving(store, Ordinals(store.positions))
        self.crop = None
        self.whole = True
        self.frames.drawable = True
        self._rebudget()
        tool = self._source_for(store.address)
        if tool is not None:
            self.serving.chunks = ChunkStore()
            self.writer = WriteBehind(self.serving.chunks)
            self.readers = Readers(tool, store.address)
        self.canvas.set_aspect(store.aspect)
        self.frames.show_frame(frame)
        self.transport.show_source(
            self.serving.ordinals.listed, store.starts(),
            store.output.edge.at.access,
        )
        if position is not None:
            self._at = position
            self.transport.show_playhead(position)

    # -- the form the tiers hold -------------------------------------------

    def _form(self) -> Form:
        """What a fill holds and a chunk is written from."""
        if self.store is None:
            raise RuntimeError("no source is open")
        return self.crop if self.crop is not None else self.store.form

    def _shown(self) -> Form:
        """What the canvas is asking for, which is not always what is held."""
        if self.whole or self.crop is None:
            return self.store.form
        return self.crop

    def _rebudget(self) -> None:
        """Frames the cache may hold, from the ceiling and the current form."""
        if self.store is None:
            return
        self.store.frames.set_budget(_CACHE_BYTES // max(1, self._form().nbytes))

    # -- where the work is standing ----------------------------------------

    def guess_at(self, position: int) -> None:
        """A drag. Serve it from what is held, or leave the picture alone.

        Which tier that is belongs to `serve.py`; what belongs here is the one
        rule about this thread — a drag may not block — and what a route means
        for the canvas. `HOLD` leaves the picture where it is, and outside a
        filled window that is every drag step, because the tier that would
        serve one is the display proxy and it does not exist.
        """
        if self.serving is None:
            return
        self._at = position
        self._show(self.serving.guess(position, self._shown()))

    def commit_at(self, position: int) -> None:
        """A release or a playback step. This one is paid for.

        Both come here because both are exact — a step names its position as
        squarely as a release does — and the difference is only that a step
        will be along again, so a slow one delays the next rather than
        skipping it.
        """
        if self.serving is None:
            return
        self._at = position
        self._show(self.serving.commit(position, self._shown()))

    def _show(self, served: Served) -> None:
        """Draw what a route produced, or decline to.

        Two routes carry no frame and they are opposite instructions: `GONE`
        says the position holds nothing and the canvas is cleared, `HOLD` says
        nothing presentable arrived and the picture already on screen is still
        the best answer. Collapsing them is how a forward-only source's whole
        past gets reported as empty.
        """
        if served.route is Route.HOLD:
            return
        self.frames.show_frame(served.frame)

    # -- landing a window --------------------------------------------------

    def land_at(self, position: int) -> None:
        """A release on the strip: serve it, and commit attention there.

        Releasing inside the filled window is a scrub and moves nothing —
        the window is already about this. Releasing outside it says the work
        is somewhere else now, and the frontier goes there.
        """
        self.commit_at(position)
        if self.serving is None:
            return
        ordinal = self.serving.ordinals.rank(position)
        if ordinal is None:
            return
        active = self.serving.active
        if active is not None and active[0] <= ordinal < active[1]:
            return
        self._set_window(ordinal)

    def _set_window(self, anchor: int) -> None:
        """Fill the span starting at *anchor*, dropping whatever was filling.

        The click is the *start* of the window and not its centre: somebody
        clicks where something begins and wants what follows it, not five
        seconds of lead-up. The filled range is the chunk-grid superset of
        that span, because chunks live on the store's own ordinals and a
        window must not bend the grid to itself.
        """
        if self.serving is None or self.readers is None or self.writer is None:
            return
        chunks = self.serving.chunks
        if chunks is None:
            return
        listed = self.serving.ordinals.listed
        low, high = window_for(anchor, WINDOW, len(listed))
        if self.serving.active == (low, high):
            return
        if self.fill is not None:
            # Not waited on: the dying frontier's last frames land in the same
            # cache at the same form, which is harmless. A landing that waited
            # would be a landing that stalls, which is the whole complaint.
            self.fill.stop(wait=False)
        self.serving.active = (low, high)
        # What the chunk tier may answer for, set from the form the fill is
        # launched with rather than re-derived when it is read back: the two
        # would be the same fact in two places, and a form change moves one.
        self.serving.held_form = self._form()
        self.fill = WindowFill(
            listed, low, high, anchor, self._form(),
            self.store.frames, chunks, self.writer, self.readers,
            on_covered=lambda *landed: self.window_covered.emit(landed),
            holes=self.store.missing,
        )
        self.fill.launch()

    def _covered(self, landed: tuple) -> None:
        """A fill finished, back on the GUI thread.

        Re-serving the playhead is the point: what is on screen may be a
        *nearby* frame the drag tier put there while the frontier was still
        coming, and the exact one exists now. Without this the picture stays
        a few positions off until the user moves again.
        """
        del landed
        if self._at is not None:
            self.commit_at(self._at)

    # -- the drawn crop ----------------------------------------------------

    def crop_drawn(self, left: int, top: int, width: int, height: int) -> None:
        """A rectangle dragged on the canvas, in the view's own coordinates.

        Mapping it back is this class's job because only it knows what the
        view is showing — the whole frame, scaled to whatever room the canvas
        gave it. Drawing is refused on the crop view for the same reason: a
        rectangle drawn on a crop would be in the crop's coordinates, and a
        form's rect is in the source's (`forms.py`).
        """
        if self.store is None or not self.whole:
            return
        source_w, source_h = self.store.form.out
        across = source_w / max(1, self.frames.width())
        down = source_h / max(1, self.frames.height())
        x, y = round(left * across), round(top * down)
        w, h = round(width * across), round(height * down)
        x = max(0, min(x, source_w - _MIN_CROP))
        y = max(0, min(y, source_h - _MIN_CROP))
        w = max(_MIN_CROP, min(w, source_w - x))
        h = max(_MIN_CROP, min(h, source_h - y))
        # Even on every axis: a chunk is encoded through yuv420p, which halves
        # both chroma dimensions and cannot describe an odd one.
        x, y, w, h = (value - value % 2 for value in (x, y, w, h))
        self._apply_crop(Form((x, y, w, h), (w, h), "gray"))

    def _apply_crop(self, crop: Form) -> None:
        """A new crop is a form change, and everything derived from the old one
        goes: held frames, chunks, the window they were filled into.

        **This stop waits, where a landing's does not.** A frontier still
        running would put frames of the old form into a cache that has been
        rebuilt for the new one — the same key meaning different pixels, which
        is worse than a slow landing because nothing goes wrong until somebody
        reads it. Draining the writer comes next, and only then does the rect
        move.
        """
        self.transport.stop()
        if self.fill is not None:
            self.fill.stop()
            self.fill = None
        if self.writer is not None:
            self.writer.drain()
        self.serving.active = None
        self.serving.held_form = None
        self.store.frames.wipe()
        if self.serving.chunks is not None:
            self.serving.chunks.wipe()
        self.crop = crop
        self.whole = False
        self.frames.drawable = False
        self._rebudget()
        self.canvas.set_aspect(crop.out[0] / crop.out[1])
        if self._at is not None:
            self.land_at(self._at)   # the app never stops: new form, same place

    def show_whole_frame(self) -> None:
        """Swap between the crop and the frame it was cut out of.

        The whole frame is the marked exception once a crop exists, and it is
        expensive on purpose: nothing holds one, so every position on this view
        is a decode at source sampling. It is what a crop is drawn on, and what
        context is checked on, and not what the loop runs in.
        """
        if self.store is None or self.crop is None:
            return
        self.whole = not self.whole
        self.frames.drawable = self.whole
        shown = self._shown()
        self.canvas.set_aspect(shown.out[0] / shown.out[1])
        if self._at is not None:
            self.commit_at(self._at)

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
        """Everything the recording brought, in the order that makes it safe.

        The fill goes first and is waited for, because it holds a borrowed
        reader and puts frames into a cache that is about to go. Then the
        readers it might have given back, then the chunks — which are this
        session's alone and are not left behind.
        """
        if self.fill is not None:
            self.fill.stop()
            self.fill = None
        if self.writer is not None:
            self.writer.drain()
            self.writer = None
        if self.readers is not None:
            self.readers.close()
            self.readers = None
        if self.serving is not None and self.serving.chunks is not None:
            self.serving.chunks.destroy()
        self.serving = None
        self.crop = None
        self.whole = True
        self._at = None
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
