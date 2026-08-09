"""The window: what the parts are, and what the four navigation verbs mean.

The central widget is built exactly once — the viewing half on the left (canvas
over the pinned step), the control track on the right (`layout.compose`). The
track is never rebuilt either, so which of its four positions is current
survives every navigation; only its contents are replaced.

**Where the walk is, is here.** The session layer holds the open project and
nothing about being looked at; the track holds which position is showing and
nothing about the graph. The index into `walk.node_order` belongs to neither
and would be duplicated into both if it lived in one of them, so the window
keeps it and hands it down on every redraw.

**Which step is pinned is here too, and it is not the walk.** The slot under the
canvas holds one step's surface and the walk is somewhere else — that is what
the slot is for, a trace to tune *against* while the knobs being turned are
upstream of it. So the tuning loop watches the pinned node rather than the
current one, and a move of the walk leaves the trace alone: `watch` is called
only when the answer changes, because a fresh collector throws away the rows
already assembled (`tuning.watch`). The pin is view state and never reaches the
document — nothing in `session/` has a word for it, and a `sieve run` of the
same project cannot tell which step the window was looking at.

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

**Three edges have to be redrawn on every move of the walk**, and none of them
is incremental. The step pane and the card stack are rebuilt because
`param_form.py` reads the document once and never reads it back — and both hold
a generated form, so both go stale the same way. The composite-kind editors are
rebuilt for a different reason: they hang on the canvas and the band rather than
on a pane, and a walk that left the previous node's overlay on the viewport would
be editing a parameter the user has moved off.

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

from sieve.core.pipeline_model import PROJECT_SUFFIX, Node, Pipeline
from sieve.core.tool_base import ElementKind, ParamStereotype, ToolSpec
from sieve.core.tool_registry import ToolRegistry, UnknownToolError
from sieve.core.types import VideoMetadata
from sieve.gui.canvas import VideoCanvas
from sieve.gui.chain_stack import PipelinePane, Step
from sieve.gui.chrome import darken_title_bar, window_stylesheet
from sieve.gui.control import Control
from sieve.gui.graph_panel import GraphPanel
from sieve.gui.hotkeys import bind_navigation_hotkeys
from sieve.gui.kind_editors import bind_editors
from sieve.gui.layout import CanvasSlot, ViewingColumn, compose, size_window
from sieve.gui.param_form import ParamForm
from sieve.gui.pinned import (
    EmptySlot,
    PinnedStep,
    card_note,
    default_pinned,
    draws_a_trace,
    element_kinds,
    surface_note,
)
from sieve.gui.project_select import projects_in
from sieve.gui.save_screen import SaveScreen
from sieve.gui.step_pane import StepPane
from sieve.gui.timeline.bar import TimelineBar
from sieve.gui.transport.player import VideoPlayer
from sieve.gui.transport.request_intent import RequestKind
from sieve.gui.tuning import TuningLoop
from sieve.gui.walk import node_order
from sieve.pipeline.shelf import loaded_shelf
from sieve.session.intents import RemoveNode, issue
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


def removable(spec: ToolSpec | None) -> bool:
    """Whether the chain would still have something to read without this step.

    A source tool is where the footage enters the graph
    (`adr/a-users-file-wires-in-like-any-other-input.md`), and dropping it
    leaves the steps below reading nothing — so its ✕ is offered disabled, the
    mockup's one refusal read off the declaration that makes it derivable
    rather than off a tool id. A node whose tool this install does not have is
    removable: nothing can say it is a source, and a step naming a missing tool
    is one of the things a user most needs to be able to drop.
    """
    return spec is None or spec.source is None


def _after_removing(position: int, index: int) -> int:
    """Where a walk or a pin standing at `position` lands once `index` is gone.

    The step above, where it was standing on the removed step itself — that
    neighbour is what the removed step read, so it is the nearest surviving
    place the user was standing, and it is not whatever slid into the gap. One
    expression covers the other case because a stack renumbers under a removal:
    a position below the gap keeps the node it was already on by counting one
    lower.
    """
    return max(0, position - 1) if position >= index else position


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
        self.setStyleSheet(window_stylesheet())
        darken_title_bar(self)

        self._projects = tuple(projects)
        self._registry = loaded_shelf() if registry is None else registry
        self._session: Session | None = None
        self._specs: Mapping[str, ToolSpec] = {}
        # What one value of each node's output is a value of, which decides
        # which steps have a trace to draw. Derived beside the specs and for the
        # same reason: it is a fact about the graph's shape, and a parameter
        # moves no tool onto or off the graph (`tuning.open`).
        self._elements: Mapping[str, ElementKind | None] = {}
        self._order: tuple[Node, ...] = ()
        self._at = 0
        # Which step holds the slot under the canvas. `None` until a project is
        # open, and an index into `_order` after — one slot, so pinning is a
        # move of this number and eviction is what that means.
        self._pinned: int | None = None
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
        self._viewing = ViewingColumn(self._canvas, EmptySlot())
        self._control = Control(self._projects)
        self._control.project_chosen.connect(self.open_project)
        self.setCentralWidget(compose(self._viewing, self._control, self._timeline))

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
        """The trace under the canvas, drawn for whichever step is pinned."""
        return self._graph

    @property
    def viewing(self) -> ViewingColumn:
        """The left half: the canvas over the slot the pinned step holds."""
        return self._viewing

    @property
    def pinned_node(self) -> Node | None:
        """The step under the canvas, or `None` before a project is open."""
        if self._pinned is None or not self._order:
            return None
        return self._order[self._pinned]

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
        self._reread_graph()
        self._at = 0
        self._pinned = default_pinned(self._order, self._elements)
        self._show_pinned()
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

    def pin(self, index: int) -> None:
        """Give the slot under the canvas to step `index`, evicting what held it.

        One slot, so this is a move and not a toggle: there is no gesture that
        leaves the slot empty while a project is open, because a step is always
        the thing the canvas is being read against.
        """
        if not self._order or index == self._pinned:
            return
        self._pinned = max(0, min(index, len(self._order) - 1))
        self._show_pinned()
        self._redraw()

    def pin_current(self) -> None:
        """P: pin the step the walk is standing on.

        Only where the walk is what the position is about. At the project
        position there is no current step in view, and at the save position the
        walk is not what the user is looking at (`control.py`) — a key that
        silently repointed the slot from either would be a change to the one
        surface they were not reading.
        """
        if self._control.current_position() in ("pipeline", "step"):
            self.pin(self._at)

    def remove_step(self, index: int) -> None:
        """A card's ✕: drop step `index`, and let whatever read it read past it.

        The mutation is the document's (`session/intents.RemoveNode`) and
        everything after it here is the three view-state answers that were
        indices into a list one shorter now: the walk, the pin, and the save
        screen — which is rebuilt because a sink on the removed step went with
        the step, and a checkoff still showing it would be offering a result
        nothing computes.

        Refused rather than clamped where the step is the chain's source: the
        card offers a disabled ✕ there and this is the same predicate, because
        a caller reaching the method directly is the case where the button was
        not the gesture.
        """
        session = self._session
        if session is None or not 0 <= index < len(self._order):
            return
        node = self._order[index]
        if not removable(self._specs.get(node.node_id)):
            return
        issue(session, RemoveNode(node.node_id))
        self._reread_graph()
        self._at = _after_removing(self._at, index)
        self._pinned = (
            _after_removing(self._pinned, index)
            if self._order and self._pinned is not None
            else None
        )
        self._show_pinned()
        self._control.set_save_screen(self._build_save_screen(session))
        self._redraw()

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

    def _reread_graph(self) -> None:
        """The three facts about the document's shape, taken together.

        Together because they are one derivation in three steps — the fold that
        gives each node its element kind reads the specs and the walk — and
        because every caller that invalidates one has invalidated all three: a
        project opening, and a step leaving the chain.
        """
        session = self._session
        if session is None:
            return
        pipeline = session.project.pipeline
        self._specs = resolved_specs(pipeline, self._registry)
        self._order = node_order(pipeline)
        self._elements = element_kinds(self._order, pipeline, self._specs)

    def _on_frame_changed(self, index: int, image: QImage, kind: RequestKind) -> None:
        """The transport has reached a frame. Hold it, and decide what to show."""
        self._source_frame = (index, image)
        self._paint_viewport(render=kind.may_be_rendered)

    def _paint_viewport(self, render: bool = True) -> None:
        """The watched node's output for the frame under the playhead.

        The source frame is the fallback and not the subject: it is what the
        window shows before a pipeline can answer for that index, for a node
        with no picture, and for a render that failed — which the tuning loop
        reports through `last_error` rather than by handing over a blank. All
        four causes are marked here, and only here, because this is the only
        place that knows which of the two frames went to the canvas
        (`canvas.mark_source`).

        It is also what a drag in flight gets, which is the one caller that
        passes `render=False`: the render would otherwise sit inside the round
        trip `ScrubPolicy` degrades on (`transport/request_intent.py`). A refill
        and a walk render by default because neither is a frame arriving — they
        are the window redrawing the position it is already on.
        """
        held = self._source_frame
        if held is None:
            return
        index, image = held
        node = self.viewport_node
        session = self._session
        values = (
            None
            if not render or node is None or session is None
            else self._tuning.render_at(session.project.pipeline, node, index)
        )
        if values is None or not self._viewport.set_values(index, values):
            self._viewport.set_frame(index, image)
            self._viewport.mark_source()

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
        self._control.show_graph(
            self._order, self._at, self._build_pipeline_pane(), self._build_step()
        )
        self._rebind_editors()
        self._watch_the_pin()
        self.refill_graph()
        # Ahead of the refill this move just asked for, because that one is
        # deferred by a turn of the event loop and the picture is about the node
        # the walk is on *now*. The badge would not cover a viewport still
        # showing the previous node's output: it says the picture is the source,
        # and that picture is a render — of a node the walk has left.
        self._paint_viewport()

    def _watch_the_pin(self) -> None:
        """Point the loop at the pinned step, or at nothing if it draws no trace.

        Nothing rather than the walk's node: the panel is inside the slot, so a
        trace drawn there for any other step would be captioned with this one's
        name. And only on a change, because `watch` starts a fresh collector —
        a walk that re-pointed it at the node it was already on would blank the
        graph on every Up and Down.
        """
        node = self.pinned_node
        watched = (
            node.node_id
            if node is not None and draws_a_trace(self._elements.get(node.node_id))
            else None
        )
        if self._tuning.watching != watched:
            self._tuning.watch(watched)

    def _show_pinned(self) -> None:
        """Rebuild the slot for the step now pinned, and re-fit it to that step.

        The panel is taken out of the old slot first: `set_pinned` destroys what
        it replaces, and the one `GraphPanel` the loop fills has to outlive every
        pin the user makes.
        """
        self._graph.setParent(None)
        self._viewing.set_pinned(self._build_pinned())

    def _build_pinned(self) -> QWidget:
        """The pinned step's caption over its surface, or over a sentence.

        The surface is the graph for a step whose values are coarser than a
        pixel, and nothing for one whose output is a picture — `pinned.py` holds
        both that predicate and the sentence a step without one gets.
        """
        node = self.pinned_node
        if node is None or self._pinned is None:
            return EmptySlot()
        surface = self._graph if draws_a_trace(self._elements.get(node.node_id)) else None
        return PinnedStep(self._pinned, node, surface, surface_note(self._specs.get(node.node_id)))

    def _build_pipeline_pane(self) -> QWidget:
        """The pipeline position's content: a card per node of the walk.

        The knobs on each card are the same generated form the step position
        gets, from the same spec, and `None` for a node whose tool this install
        does not have — `_build_step`'s reason, one card at a time: a form is
        generated from a spec and there is nothing honest to draw without one.
        The card itself still stands, because a document naming a missing tool is
        still a chain the user has to be able to walk.
        """
        session = self._session
        if session is None:
            return QWidget()
        steps: list[Step] = []
        for node in self._order:
            spec = self._specs.get(node.node_id)
            knobs = None
            if spec is not None:
                form = ParamForm(session, node.node_id, spec)
                form.edited.connect(self.refill_graph)
                knobs = form
            steps.append(Step(node=node, knobs=knobs, removable=removable(spec)))
        return PipelinePane(
            session.path.name.removesuffix(PROJECT_SUFFIX),
            steps,
            self._at,
            self._pinned,
            self._pinned_note(),
            on_select=self._walk_to,
            on_open=self._open_step,
            on_pin=self.pin,
            on_remove=self.remove_step,
        )

    def _pinned_note(self) -> str:
        """The sentence the pinned step's card carries, or nothing to carry it.

        Empty for an empty graph, which is the case where no card is drawn to
        put it on.
        """
        node = self.pinned_node
        if node is None:
            return ""
        return card_note(self._elements.get(node.node_id), self._specs.get(node.node_id))

    def _open_step(self, index: int) -> None:
        """A card's arrow: select that step, then slide to its form.

        Both halves, in that order, because the step position shows the node the
        walk is on — arriving there without having moved the walk would open the
        form of whichever step the user was standing on before.
        """
        self._walk_to(index)
        self._control.show_step()

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
