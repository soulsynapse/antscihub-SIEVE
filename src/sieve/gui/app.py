"""The window: what the parts are, and what the four navigation verbs mean.

The central widget is built exactly once — the viewing half on the left (canvas
over graph), the control track on the right (`layout.compose`). The track is
never rebuilt either, so which of its four positions is current survives every
navigation; only its contents are replaced.

**Where the walk is, is here.** The session layer holds the open project and
nothing about being looked at; the track holds which position is showing and
nothing about the graph. The index into `walk.node_order` belongs to neither
and would be duplicated into both if it lived in one of them, so the window
keeps it and hands it down on every redraw.

The canvas is `canvas.VideoCanvas`; the scrubber under both halves is
`timeline/bar.py`, which owns the working window and is the only thing that
tells the transport what it may reach. The graph under the canvas is
`graph_panel.py`, filled by `tuning.py` — which is where an edit becomes a
render and a render becomes a series.

**Both halves of the left column answer to the same edit, and this is where
that is arranged.** The canvas shows the watched node's output for the frame
under the playhead, not the footage: a viewport fed by `transport/player.py`
while the graph under it is fed by the preview means moving a parameter changes
one of the two, and the ceiling named for a repaint is then measured on a render
nobody sees. The transport still decides *which index* is current and still
supplies the frame shown where the pipeline cannot; `_paint_viewport` is the one
place the two are put together, because it needs the playhead, the walk, and the
session at once and none of the three may hold a copy of another.

**This module is where the Phase 7 surfaces meet, and it is the only place that
can decide what they could not.** Which position the save screen is (`control.py`
carries the argument), where the graph hangs (`layout.py`), how the step is
stacked (`step_pane.py`), and what space a drawn region is denominated in
(`kind_editors.RegionEditor`) are four questions about the assembly, answered in
the module each is a fact about and referred to from here.

**Two edges have to be redrawn on every move of the walk**, and neither is
incremental. The step pane is rebuilt because `param_form.py` reads the document
once and never reads it back, and the composite-kind editors are rebuilt because
they hang on the canvas and the band rather than on the pane — a walk that left
the previous node's overlay on the viewport would be editing a parameter the user
has moved off.

Nothing here computes: opening a project reads a document, the order the graph
walks in is `walk.py`'s, and every array in the window came out of
`pipeline/preview.py`. The `gui-computes-nothing` exception list is empty and
stays empty; `tests/gui/test_gui_cli_parity.py` is where that is cashed.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QWidget

from sieve.core.pipeline_model import Node, Pipeline
from sieve.core.tool_base import ElementKind, ParamStereotype, ToolSpec
from sieve.core.tool_registry import ToolRegistry, UnknownToolError
from sieve.core.types import VideoMetadata
from sieve.gui.canvas import VideoCanvas
from sieve.gui.control import Control
from sieve.gui.graph_panel import GraphPanel
from sieve.gui.hotkeys import bind_navigation_hotkeys
from sieve.gui.kind_editors import bind_editors
from sieve.gui.layout import CanvasSlot, compose, size_window
from sieve.gui.project_select import projects_in
from sieve.gui.save_screen import SaveScreen
from sieve.gui.step_pane import StepPane
from sieve.gui.timeline.bar import TimelineBar
from sieve.gui.transport.player import VideoPlayer
from sieve.gui.tuning import TuningLoop
from sieve.gui.walk import node_order
from sieve.pipeline.shelf import loaded_shelf
from sieve.session.session import Session


def resolved_specs(pipeline: Pipeline, registry: ToolRegistry) -> dict[str, ToolSpec]:
    """The spec behind each node, skipping the ones the shelf does not hold.

    Leniently, and not through `Dag.build`: a window has to draw whatever
    document was opened, including one naming a tool this install does not have,
    and `Dag` refuses such a graph outright because its caller is about to run
    it. Same reason `walk.py` is not `dag.linear_order`.
    """
    resolved: dict[str, ToolSpec] = {}
    for node in pipeline.nodes:
        try:
            resolved[node.node_id] = registry.get(node.tool_id, node.version)
        except UnknownToolError:
            continue
    return resolved


def source_fed_nodes(pipeline: Pipeline) -> frozenset[str]:
    """Nodes handed a source frame — the ones nothing upstream has reshaped.

    What a `region` parameter needs to be offered an editor at all: its value is
    denominated in the frame its own node reads, and the only frame the window
    knows the size of is the footage's own (`kind_editors.RegionEditor`).
    """
    fed = {edge.downstream for edge in pipeline.edges}
    return frozenset(node.node_id for node in pipeline.nodes if node.node_id not in fed)


def frame_bearing(pipeline: Pipeline, specs: Mapping[str, ToolSpec], node_id: str) -> str | None:
    """The nearest node at or above `node_id` whose output is a picture.

    `node_id` itself, ordinarily. `detect` declares `ElementKind.FRAME` — one
    value describing the whole frame — so its output is a 1x1 gate with no image
    in it, and the viewport climbs to what that gate was derived *from* rather
    than back to the footage: a user tuning a detection band is deciding about
    the signal it is drawn over, and the source frame is the one picture that
    cannot say whether the band is in the right place.

    `None` when nothing on that path has an image either, and when the walk
    stands on a tool this install does not have — the source is what is shown
    for both, being the one frame the window can produce without a spec.

    Schema v1 refuses two edges into one node (`walk.py`), so the path upward is
    a chain and there is no parent to choose between.
    """
    upstream = {edge.downstream: edge.upstream for edge in pipeline.edges}
    current: str | None = node_id
    while current is not None:
        spec = specs.get(current)
        if spec is None:
            return None
        if spec.element is not ElementKind.FRAME:
            return current
        current = upstream.get(current)
    return None


class MainWindow(QMainWindow):
    def __init__(self, projects: Sequence[Path], registry: ToolRegistry | None = None) -> None:
        super().__init__()
        self.setWindowTitle("SIEVE")

        self._projects = tuple(projects)
        self._registry = loaded_shelf() if registry is None else registry
        self._session: Session | None = None
        self._specs: Mapping[str, ToolSpec] = {}
        self._order: tuple[Node, ...] = ()
        self._at = 0
        # The overlays are `kind_editors`' own private type, held here only to
        # be torn down and reconnected; nothing in this module reads one.
        self._editors: dict[str, Any] = {}
        self._source_extent: tuple[int, int] | None = None
        # The last frame the transport delivered, held so a refill or a walk can
        # repaint the viewport without asking the decode thread for a frame it
        # has already sent.
        self._source_frame: tuple[int, QImage] | None = None

        self._player = VideoPlayer(self)
        self._viewport = VideoCanvas()
        self._player.frame_changed.connect(self._on_frame_changed)
        self._timeline = TimelineBar(self._player)
        # Connected after the bar, because Qt delivers to subscribers in
        # subscription order and the preview is opened over the bar's working
        # window — which the bar sets from this very signal. Ahead of it, the
        # window would still be the previous source's, or none at all.
        self._player.opened.connect(self._on_opened)
        self._player.failed.connect(self._on_failed)

        self._graph = GraphPanel()
        self._tuning = TuningLoop(self._graph, self, registry=self._registry)
        self._tuning.refilled.connect(self._paint_viewport)

        self._canvas = CanvasSlot(self._viewport)
        self._control = Control(self._projects)
        self._control.project_chosen.connect(self.open_project)
        self.setCentralWidget(compose(self._canvas, self._graph, self._control, self._timeline))

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
    def viewport(self) -> VideoCanvas:
        """The picture over the trace."""
        return self._viewport

    @property
    def viewport_node(self) -> str | None:
        """The node whose output the viewport paints, or `None` for the source.

        `None` in two cases, and they are one rule: the viewport shows a frame
        the window can say what space it is in. A region parameter is denominated
        in the frame its own node is handed, and `bind_editors` is offered an
        extent only where that frame is the source — so while such an editor is
        on the canvas the canvas has to be showing the source, or the box is
        drawn over a rectangle the value does not index (`kind_editors`,
        `RegionEditor`). Otherwise it is whatever `frame_bearing` finds, which is
        `None` when the walk stands somewhere with no picture above it at all.
        """
        node = self.current_node
        session = self._session
        if node is None or session is None:
            return None
        pipeline = session.project.pipeline
        spec = self._specs.get(node.node_id)
        if (
            spec is not None
            and ParamStereotype.REGION in spec.param_stereotypes.values()
            and node.node_id in source_fed_nodes(pipeline)
        ):
            return None
        return frame_bearing(pipeline, self._specs, node.node_id)

    @property
    def graph(self) -> GraphPanel:
        """The trace under the canvas."""
        return self._graph

    @property
    def tuning(self) -> TuningLoop:
        """The preview an edit refills the graph from."""
        return self._tuning

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

        The preview is not opened here. It is opened when the transport reports
        metadata, which is the one thing in the window that has actually read the
        container — a second check here of whether the footage is there could
        disagree with it.

        Raises:
            OSError: if `path` cannot be read.
            ValidationError: if the document is structurally invalid.
        """
        self._tuning.close()
        self._source_extent = None
        self._source_frame = None
        self._session = Session.open(path)
        self._specs = resolved_specs(self._session.project.pipeline, self._registry)
        self._order = node_order(self._session.project.pipeline)
        self._at = 0
        self._control.set_save_screen(self._build_save_screen(self._session))
        # The path is resolved against the project's own directory and handed
        # over as a string: whether the file is there is the decode thread's
        # answer to give, and a check here would be a second one that could
        # disagree with it.
        self._player.open(str(self._session.project.source.resolve(path.parent)))
        self._redraw()
        self._control.show_pipeline()

    def closeEvent(self, event: object) -> None:
        """Stop the decode thread before the window goes.

        A `QThread` still running when its `QObject` is finalised takes the
        process down, which turns closing the app into a crash report. The
        preview's own readers are closed first, for the ordinary reason: they
        hold one open container per worker.
        """
        self._tuning.close()
        self._player.shutdown()
        super().closeEvent(event)  # type: ignore[arg-type]

    def go_back(self) -> None:
        """Left: save to step, step to pipeline, pipeline to project select.

        A no-op at the project position — there is nothing further back, and the
        session underneath it is left open so that Right returns to exactly the
        node the walk was on.
        """
        position = self._control.current_position()
        if position == "save":
            self._control.show_step()
        elif position == "step":
            self._control.show_pipeline()
        elif position == "pipeline":
            self._control.show_project_select(self._projects)

    def go_forward(self) -> None:
        """Right: project select to pipeline, pipeline to step, step to save.

        A no-op at the project position with nothing open — there is no
        workspace to move into until a project has been chosen — and at the save
        position, which is the end of the line.
        """
        position = self._control.current_position()
        if position == "project":
            if self._session is not None:
                self._control.show_pipeline()
        elif position == "pipeline":
            self._control.show_step()
        elif position == "step":
            self._control.show_save()

    def go_up(self) -> None:
        """Up: the previous node in the walk, or stay on the first."""
        self._walk_to(self._at - 1)

    def go_down(self) -> None:
        """Down: the next node in the walk, or stay on the last."""
        self._walk_to(self._at + 1)

    def refill_graph(self) -> None:
        """Redraw the trace for the document as it now stands.

        The working window is read off the bar on the way past rather than
        pushed at the preview when it moves: the bar is the one owner of the
        window (`timeline/bar.py`), and a copy of it in the preview would be the
        one that went stale.
        """
        if self._session is None:
            return
        window = self._timeline.window
        if window is None:
            return
        self._tuning.set_window(window)
        self._tuning.request_refill(self._session.project.pipeline)

    # ---- internals -------------------------------------------------------

    def _on_frame_changed(self, index: int, image: QImage) -> None:
        """The transport has reached a frame. Hold it, and decide what to show."""
        self._source_frame = (index, image)
        self._paint_viewport()

    def _paint_viewport(self) -> None:
        """The watched node's output for the frame under the playhead.

        The source frame is the fallback and not the subject: it is what the
        window shows before a pipeline can answer for that index, for a node
        with no picture, and for a render that failed — which the tuning loop
        reports through `last_error` rather than by handing over a blank.
        """
        held = self._source_frame
        if held is None:
            return
        index, image = held
        node = self.viewport_node
        session = self._session
        values = (
            None
            if node is None or session is None
            else self._tuning.render_at(session.project.pipeline, node, index)
        )
        if values is None or not self._viewport.set_values(index, values):
            self._viewport.set_frame(index, image)

    def _walk_to(self, index: int) -> None:
        # Clamped rather than wrapped, and silent at either end: a held key
        # reaching the last node is ordinary use, and wrapping would move the
        # canvas and the step pane to the far end of the graph for a keystroke
        # the user meant as "no further".
        if not self._order:
            return
        self._at = max(0, min(index, len(self._order) - 1))
        self._redraw()

    def _redraw(self) -> None:
        """Both walk positions, the overlays, and which node the graph is about."""
        self._control.show_graph(self._order, self._at, self._build_step())
        self._rebind_editors()
        node = self.current_node
        self._tuning.watch(None if node is None else node.node_id)
        self.refill_graph()
        # Ahead of the refill this move just asked for, because that one is
        # deferred by a turn of the event loop and the picture is about the node
        # the walk is on *now* — a viewport still showing the previous node's
        # output until the graph comes back is the stale-mark interval leaking
        # onto a surface that has no mark.
        self._paint_viewport()

    def _build_step(self) -> QWidget:
        """The step position's content for the node the walk is on.

        A bare widget for an empty graph, and for a node whose tool this install
        does not have: a form is generated from a spec, and there is nothing
        honest to draw without one.
        """
        node = self.current_node
        session = self._session
        if node is None or session is None or node.node_id not in self._specs:
            return QWidget()
        pane = StepPane(self._at + 1, node, session, self._specs[node.node_id])
        pane.form.edited.connect(self.refill_graph)
        return pane

    def _build_save_screen(self, session: Session) -> QWidget:
        """The save position's content, or why there is none.

        `output_rows` reads a spec per node and refuses one it has not got, so a
        document naming a tool this install lacks gets the sentence rather than
        a screen offering a partial list — which would read as the whole of what
        the run can keep.
        """
        missing = [
            node.tool_id
            for node in session.project.pipeline.nodes
            if node.node_id not in self._specs
        ]
        if missing:
            return QLabel(
                "no outputs can be offered: this install has no "
                + ", ".join(dict.fromkeys(missing))
            )
        return SaveScreen(session, self._specs)

    def _rebind_editors(self) -> None:
        """Move the composite-kind overlays onto the node the walk is on."""
        for editor in self._editors.values():
            editor.setParent(None)
            editor.deleteLater()
        self._editors = {}

        node = self.current_node
        session = self._session
        if node is None or session is None or node.node_id not in self._specs:
            return
        extent = (
            self._source_extent
            if node.node_id in source_fed_nodes(session.project.pipeline)
            else None
        )
        self._editors = dict(
            bind_editors(
                session,
                node.node_id,
                self._specs[node.node_id],
                session.project.params_for(node.node_id),
                canvas=self._viewport,
                timeline=self._timeline.strip,
                region_extent=extent,
            )
        )
        for editor in self._editors.values():
            editor.edited.connect(self.refill_graph)

    def _on_opened(self, metadata: VideoMetadata) -> None:
        """The container is real: open the preview over it and draw the trace."""
        session = self._session
        window = self._timeline.window
        if session is None or window is None:
            return
        self._source_extent = (metadata.width, metadata.height)
        self._tuning.open(metadata.path, session.project.pipeline, window)
        self._rebind_editors()
        self.refill_graph()

    def _on_failed(self, message: str) -> None:
        del message
        self._source_extent = None
        self._source_frame = None
        self._tuning.close()
        self._rebind_editors()


def main() -> None:
    application = QApplication(sys.argv)
    window = MainWindow(projects_in(Path.cwd()))
    size_window(window)
    sys.exit(application.exec())
