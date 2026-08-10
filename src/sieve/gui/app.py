"""The window: what the parts are, and what the four navigation verbs mean.

The central widget is built exactly once — the viewing half on the left (canvas
over the pinned step), the control track on the right (`layout.compose`). The
track is never rebuilt either, so which of its four positions is current
survives every navigation; only its contents are replaced.

**Where the walk is, is here.** The session layer holds the open project and
nothing about being looked at; the track holds which position is showing and
nothing about the graph. The index into `walk.node_order` belongs to neither
and would be duplicated into both if it lived in one of them, so the window
keeps it and hands it down on every redraw. Which project the shelf's accent is
on is held here too and for the same reason — it is a second selection, one
position earlier, and Up and Down move whichever of the two the position showing
is about (`go_up`).

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

from PySide6.QtCore import QEvent
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QWidget

from sieve.core.pipeline_model import PROJECT_SUFFIX, Node, Pipeline, Replicate
from sieve.core.tool_base import (
    DisplaySurface,
    ElementKind,
    ParamStereotype,
    StreamSpec,
    ToolSpec,
)
from sieve.core.tool_registry import ToolRegistry, UnknownToolError, offered_tools
from sieve.core.types import VideoMetadata
from sieve.gui.canvas import VideoCanvas
from sieve.gui.chain_stack import Adding, Fan, Outputs, PipelinePane, Regions, Step, Write
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
from sieve.gui.project_select import (
    ProjectSelect,
    ask_where,
    library_folder,
    listings,
    mint,
    projects_in,
    reveal,
)
from sieve.gui.save_screen import SaveScreen, kept_products
from sieve.gui.step_pane import StepPane
from sieve.gui.streams import stream_specs
from sieve.gui.surface_panel import SurfacePanel
from sieve.gui.timeline.bar import TimelineBar
from sieve.gui.transport.player import VideoPlayer
from sieve.gui.transport.request_intent import RequestKind
from sieve.gui.tuning import TuningLoop
from sieve.gui.walk import node_order
from sieve.pipeline.resolve_source import resolved_sources
from sieve.pipeline.shelf import loaded_shelf
from sieve.session.intents import (
    AddNode,
    AddReplicate,
    RemoveNode,
    RemoveReplicate,
    RetoolNode,
    issue,
)
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


def region_param(spec: ToolSpec | None) -> str | None:
    """The name of the parameter a step's box is, or `None` where it has none.

    Read off the stereotype rather than off a tool id, which is the only reading
    available here (`adr/gui-knows-kinds-not-tools.md`) and the same one
    `pipeline/crop_serving.crop_roots` makes from the resolved params type. The
    first, for `_region_fan`'s reason one level down: a tool declaring two boxes
    would leave which of them the regions deviate at unanswerable, and nothing
    on the shelf does.
    """
    if spec is None:
        return None
    return next(
        (name for name, kind in spec.param_stereotypes.items() if kind is ParamStereotype.REGION),
        None,
    )


def cuts_regions(spec: ToolSpec | None, node_id: str, pipeline: Pipeline) -> bool:
    """Whether this node's box is the one the project's regions are deviations of.

    Roots only, for `source_fed_nodes`' reason: a region is denominated in the
    frame its own node is handed, and a replicate's box is a box on the footage.
    Which is also what makes this the predicate the + verb keys an override on
    (`MainWindow.add_region`) — a fan under a node reading a reshaped frame
    would offer regions whose value the canvas has no editor for, and the
    overrides would be pinned in a space nothing here can name.
    """
    return region_param(spec) is not None and node_id in source_fed_nodes(pipeline)


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


def _after_adding(position: int, index: int) -> int:
    """Where a walk or a pin standing at `position` lands once a step goes in under `index`.

    The new step lands immediately below the gap's own: `walk.py` visits a node
    and then what it feeds, and the splice leaves the gap's step feeding the new
    one and nothing else. So everything below the gap counts one higher and
    everything at or above it is where it was — a stack renumbers under an
    insertion the way it renumbers under a removal, and an index left alone
    would quietly be about a different node.
    """
    return position + 1 if position > index else position


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
    def __init__(
        self,
        projects: Sequence[Path],
        registry: ToolRegistry | None = None,
        library: Path | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("SIEVE")
        self.setStyleSheet(window_stylesheet())
        darken_title_bar(self)

        self._projects = tuple(projects)
        # Where a mint lands, and what the library card is titled with. Derived
        # from the projects when it is not given, which is every caller holding a
        # scan; passed explicitly by `main`, because the folder a user launched
        # in may hold no projects at all and that is precisely when minting is
        # the only thing there is to do.
        self._library = library_folder(self._projects) if library is None else library
        self._registry = loaded_shelf() if registry is None else registry
        self._session: Session | None = None
        self._specs: Mapping[str, ToolSpec] = {}
        # What one value of each node's output is a value of, which decides
        # which steps have a trace to draw. Derived beside the specs and for the
        # same reason: it is a fact about the graph's shape, and a parameter
        # moves no tool onto or off the graph (`tuning.open`).
        self._elements: Mapping[str, ElementKind | None] = {}
        # The other half of the same spec, folded down the same walk: what each
        # node's output stream actually is, which is what a position's offer is
        # computed against (`gui/streams.py`).
        self._streams: Mapping[str, StreamSpec | None] = {}
        # What each source root's path parameter names on disk, ordered. Beside
        # the three above and unlike them: those are folds over the document,
        # and this one read the filesystem, so it is the only one here that can
        # be wrong while the document is untouched (`changeEvent`).
        self._resolved_sources: Mapping[str, tuple[Path, ...]] = {}
        self._order: tuple[Node, ...] = ()
        self._at = 0
        # Which project card wears the accent. The walk's number one position
        # earlier, and held here for the same reason: a click on a card and an
        # Up are two ways to move one number, and a widget that kept its own
        # would be the second answer to which project is being looked at.
        self._project_at = 0
        # Which of the project's regions the stack below the fan is drawn for.
        # View state for the walk's reason: which region is being looked at is
        # not something the document records, and a widget holding its own would
        # be the second answer to it. It is also the tail of every address the
        # forms and the overlays write at (`selected_replicate`), so a move of it
        # is a redraw of both for the same reason a move of the walk is.
        self._region = 0
        # Which step holds the slot under the canvas. `None` until a project is
        # open, and an index into `_order` after — one slot, so pinning is a
        # move of this number and eviction is what that means.
        self._pinned: int | None = None
        # Which position the box is standing at, which of that position's offers
        # is lit, and whether it stands *in place of* that position's step rather
        # than in the gap under it. `None` while no box is open, which is not the
        # same as a box at gap 0 — view state for the pin's reason, and doubly so
        # here: the box is a picker and the document knows nothing about one
        # being open.
        self._adding: int | None = None
        self._offer = 0
        self._anchored = False
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
        self._control = Control(self._build_project_select())
        self.setCentralWidget(compose(self._viewing, self._control, self._timeline))

        self._box_keys = bind_navigation_hotkeys(self)
        self._box_keys(False)

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
        if cuts_regions(self._specs.get(node.node_id), node.node_id, pipeline):
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
    def resolved_sources(self) -> Mapping[str, tuple[Path, ...]]:
        """The files each source root names, ordered, as of the last re-read.

        `{}` before a project is open, and `()` for a source with nothing
        chosen or a folder that is not mounted — three states a document may
        legitimately be in, so none of them is an absence of the mapping
        (`pipeline/resolve_source.resolved_sources`).
        """
        return self._resolved_sources

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

        The project being left is written back first, for `closeEvent`'s reason
        read the other way: opening a second project is how a session ends
        without the window going, and an edit lost here would be lost to a
        gesture that never mentioned the document it discarded.

        Raises:
            OSError: if `path` cannot be read.
            ValidationError: if the document is structurally invalid.
        """
        if self._session is not None:
            self._session.save_if_edited()
        self._tuning.close()
        self._source_extent = None
        self._source_frame = None
        if path in self._projects:
            # The accent follows what is open, so Left lands on a shelf whose
            # selection is the project the user is in rather than wherever it
            # was left. A path from outside the library moves nothing: there is
            # no card for it to move to.
            self._project_at = self._projects.index(path)
        self._session = Session.open(path)
        self._reread_graph()
        self._at = 0
        # The walk's reason one line up: where the previous project's regions had
        # reached is an index into a different set of them.
        self._region = 0
        self._pinned = default_pinned(self._order, self._elements)
        self._show_pinned()
        self._control.set_save_screen(self._build_save_screen(self._session))
        # The path is resolved against the project's own directory and handed
        # over as a string: whether the file is there is the decode thread's
        # answer to give, and a check here would be a second one that could
        # disagree with it. A project that names no footage has nothing to hand
        # it — the window opens on the chain it does not have yet, which is where
        # a source is added (`adr/superseded/a-document-may-name-no-footage.md`).
        source = self._session.project.source
        if source is not None:
            self._player.open(str(source.resolve(path.parent)))
        self._redraw()
        self._control.show_pipeline()

    def changeEvent(self, event: QEvent) -> None:
        """Coming back to SIEVE re-asks what the document's sources name.

        VISION's new-project scenario drops a second video into the folder a
        source names while the user is elsewhere, and has them "come back to
        SIEVE" to find both files showing. That is this: the first input in the
        product that is neither a user gesture nor a run, and the only one that
        exists because the answer can move with nothing here having moved it.

        On the way *in* only. Qt sends this event for a window losing activation
        as well as gaining it, and re-reading on the way out would be claiming
        the answer can have changed between the user leaving and this window
        hearing about it — which is the one interval in which nothing happened.

        Not a poll, and deliberately not: a watcher on the folder would make the
        answer arrive while the user is looking at something else, and a timer
        would spend the interactive loop's budget on a stat nobody asked for.
        The gesture that brings them back is the one moment the answer is worth
        having, which is also the moment it is free.
        """
        super().changeEvent(event)  # type: ignore[arg-type]
        if event.type() == QEvent.Type.ActivationChange and self.isActiveWindow():
            self._reread_graph()
            self._redraw()

    def closeEvent(self, event: object) -> None:
        """Write the document back, then stop the decode thread.

        The save is first because it is the only thing here that can still fail
        in a way the user would care about, and everything after it is teardown.

        **Closing the window is a save, and there is no other gesture that is
        one.** Every mutation the command layer issues lives in the session
        until something calls `save`, and the only other caller is the run
        button — so without this, tuning six parameters and closing leaves the
        file as it was opened. Silently rather than through a prompt: the
        document is the value the user has been editing all along, the stacks
        that made those edits are this session's and are not saved with it, and
        a dialog asking whether to keep work already done would be the one
        surface in the window that treats an edit as provisional.

        A `QThread` still running when its `QObject` is finalised takes the
        process down, which turns closing the app into a crash report. The
        preview's own readers are closed first, for the ordinary reason: they
        hold one open container per worker.
        """
        if self._session is not None:
            self._session.save_if_edited()
        self._tuning.close()
        self._player.shutdown()
        super().closeEvent(event)  # type: ignore[arg-type]

    def go_back(self) -> None:
        """Left: save to step, step to pipeline, pipeline to project select.

        A no-op at the project position — there is nothing further back, and the
        session underneath it is left open so that Right returns to exactly the
        node the walk was on.

        An open box owns this pair as well as Up and Down: it is a position the
        walk cannot stand on, so while it is there both pairs are about it.
        """
        if self.adding:
            self.move_offer(-1)
            return
        position = self._control.current_position()
        if position == "save":
            self._control.show_step()
        elif position == "step":
            self._control.show_pipeline()
        elif position == "pipeline":
            # Rebuilt on the way out rather than left as it was: a project saved
            # since the shelf was last drawn has a different date on it, and the
            # card is what says so.
            self._control.set_project_select(self._build_project_select())
            self._control.show_project_select()

    def go_forward(self) -> None:
        """Right: project select to pipeline, pipeline to step, step to save.

        A no-op at the project position with nothing open — there is no
        workspace to move into until a project has been chosen — and at the save
        position, which is the end of the line. An open box takes it, for
        `go_back`'s reason.
        """
        if self.adding:
            self.move_offer(1)
            return
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

    def add_step(self) -> None:
        """ADD STEP, and A: open the box in the gap under the walk, or take it back.

        Nothing is written. The box is a picker — it asks which gap and what
        should go in it, and the one mutation the gesture makes is issued when
        an offer is taken (`take_offer`), which is what makes esc free.

        Only where the walk is what the position is about, for `pin_current`'s
        reason, and only where the chain has a gap. A project with no steps has
        none: a gap is between two positions the chain has, and the first step
        of an empty project is a source, which is a question the offering
        predicate does not answer yet (`core/tool_registry.offered_tools`).
        """
        if self.adding:
            self.cancel_add()
            return
        if not self._order or self._control.current_position() not in ("pipeline", "step"):
            return
        self._adding, self._offer, self._anchored = self._at, 0, False
        self._box_keys(True)
        self._control.show_pipeline()
        self._redraw()

    def swap_step(self, index: int) -> None:
        """A card's ⇄: open the same box standing where step `index` is.

        Not a menu, and not a second surface: the question is the position's and
        the box is what asks a position (`adr/a-position-is-asked-for-in-the-chain.md`).
        The tool already there is what the offer opens lit on, because the box
        is standing in its place and the entry a menu would have carried checked
        is the one saying "and it could stay".

        Refused rather than opened where the position offers nothing, which is
        the ⇄'s own predicate reached from the other side. The add box opens on
        an empty gap because ↑/↓ are how the user reaches a gap that offers;
        this one cannot move, so opening it there would take the card away and
        leave esc as the only exit.
        """
        session = self._session
        if session is None or not 0 <= index < len(self._order):
            return
        offer = self._offer_over(index)
        if not offer:
            return
        tool = self._order[index].tool_id
        lit = next((at for at, spec in enumerate(offer) if spec.tool_id == tool), 0)
        self._adding, self._offer, self._anchored = index, lit, True
        self._box_keys(True)
        self._control.show_pipeline()
        self._redraw()

    @property
    def adding(self) -> bool:
        """Whether a box is standing in the chain waiting to be filled."""
        return self._adding is not None

    def move_box(self, delta: int) -> None:
        """Up/Down while a box is open move the box, not the walk.

        Clamped for `_walk_to`'s reason. The lit offer does not travel with it:
        the next gap's offering is a different list, and an index carried into
        it would light whatever happened to be third.

        Nothing at all while the box is anchored: it is standing at a position
        that exists, and walking it into the gaps would flip it between
        replacing and inserting as it travelled.
        """
        if self._adding is None or self._anchored:
            return
        site = max(0, min(self._adding + delta, len(self._order) - 1))
        if site == self._adding:
            return
        self._adding, self._offer = site, 0
        self._redraw()

    def move_offer(self, delta: int) -> None:
        """Left/Right while a box is open walk its offers, not the panes.

        Wrapped where the walk is clamped: the offer is a short ring of names
        and neither end is somewhere the user is trying to stop.
        """
        offer = self._box_offer()
        if not offer:
            return
        self._offer = (self._offer + delta) % len(offer)
        self._redraw()

    def take_offer(self) -> None:
        """Enter, and a click on an offer: put that tool where the box is standing.

        The one mutation the whole gesture writes, and it is the document's — a
        stack drawing a chain the file does not hold would be the second answer
        to what the project computes, and the next `sieve run` would run the one
        the user is not looking at.

        *Which* mutation is the one thing the two gestures do not share. A box
        in a gap splices (`session/intents.AddNode`); an anchored one replaces
        the tool and keeps the name (`RetoolNode`), because `node_id` is what
        names the artifact on disk, what the checkpoints and sinks hold and what
        `bench/` addresses — so a swap written as a removal and an addition
        would break every one of those with nothing going red.

        The walk lands on what the offer put there, for the reason a removal
        lands on the step above: the next thing the user does is set it up. A
        box with nothing to offer takes nothing, which is the whole of what
        enter means there.
        """
        session = self._session
        offer = self._box_offer()
        if session is None or self._adding is None or not offer:
            return
        spec = offer[self._offer % len(offer)]
        site = self._adding
        anchored = self._anchored
        if anchored:
            issue(
                session,
                RetoolNode(
                    node_id=self._order[site].node_id,
                    tool_id=spec.tool_id,
                    version=spec.version,
                ),
            )
        else:
            # No params: an unset field resolves to the tool's declared default
            # (`param_form.py`), and writing those into the document at mint time
            # would freeze them against the next version of the tool. A retool
            # drops the departed tool's for the same reason read backwards.
            issue(
                session,
                AddNode(
                    site_id=self._order[site].node_id,
                    node=Node(tool_id=spec.tool_id, version=spec.version),
                ),
            )
        self._close_box()
        self._reread_graph()
        self._at = site if anchored else site + 1
        # The chain is no shorter or longer for a swap, so the slot's index still
        # means what it meant — and the step it points at is the same position,
        # which is what keeping the node's identity buys the view state too.
        self._pinned = (
            self._pinned if anchored or self._pinned is None else _after_adding(self._pinned, site)
        )
        self._show_pinned()
        # Rebuilt because the new step is a result the run could be asked to
        # keep, and a checkoff that did not list it would be offering less than
        # the document computes.
        self._control.set_save_screen(self._build_save_screen(session))
        self._redraw()

    def cancel_add(self) -> None:
        """Esc: the box goes and the document is where it was.

        Free because nothing was written when it opened — the position it is
        standing at is unchanged until an offer is taken, which is what makes
        the anchored box's exit restore the card rather than undo anything.
        """
        if self._adding is None:
            return
        self._close_box()
        self._redraw()

    def _close_box(self) -> None:
        """Drop the box and hand enter and esc back, which only an open box owns."""
        self._adding = None
        self._anchored = False
        self._box_keys(False)

    def _shelf(self) -> tuple[ToolSpec, ...]:
        """One version of each tool, which is the shelf a gap is offered from.

        Which version a step is minted at is not a question the gap is asking —
        two entries of one tool would read as two tools — so the newest stands
        for it, and the older ones stay reachable through a document that
        already names one (`core/tool_registry.ToolRegistry.latest`).
        """
        return tuple(self._registry.latest(tool_id) for tool_id in self._registry.ids())

    def _offer_at(self, site: int | None) -> tuple[ToolSpec, ...]:
        """What could plausibly stand in the gap under step `site`.

        The question is the position's and not the tool's: `offered_tools` is
        handed what the gap's step *resolved to* and the element meaning folded
        to it — the two halves of one walk — and nothing here reads a tool id
        (`adr/gui-knows-kinds-not-tools.md`). Empty where the gap's step names a
        tool this install does not have, and where the chain is rooted on one
        that declares its stream no more completely than a preserving tool does:
        both are positions with nothing proven about them, which is the state
        every gap was in before the fold
        (`findings/2026.08.09-the-shelf-declares-too-little-for-eight-of-ten-positions-to-offer-anything.md`).
        """
        if site is None or not 0 <= site < len(self._order):
            return ()
        produced = self._streams.get(self._order[site].node_id)
        if produced is None:
            return ()
        return offered_tools(produced, self._elements.get(self._order[site].node_id), self._shelf())

    def _offer_over(self, position: int) -> tuple[ToolSpec, ...]:
        """What could plausibly stand *at* `position`, in place of what does.

        The gap above it, asked again — `offered_tools` is handed what flows
        into a position and never anything about the tool standing there, so
        the swap site and the add site are one predicate under two names rather
        than a second one (`core/tool_registry.offered_tools`).

        Empty at the chain's root, which is what makes the source unswappable:
        offering against a folder of picked files needs their count and
        extension class, and that is a question this predicate does not answer
        yet.
        """
        feeding = self._feeding(position)
        return () if feeding is None else self._offer_at(feeding)

    def _feeding(self, position: int) -> int | None:
        """Which position's output `position` reads, or `None` at the root.

        At most one: schema v1 refuses two edges into one node
        (`core/pipeline_model.Pipeline`), so there is no choice to make here
        that a merging tool has not yet given the document.
        """
        session = self._session
        if session is None or not 0 <= position < len(self._order):
            return None
        at = {node.node_id: index for index, node in enumerate(self._order)}
        node_id = self._order[position].node_id
        return next(
            (
                at[edge.upstream]
                for edge in session.project.pipeline.edges
                if edge.downstream == node_id and edge.upstream in at
            ),
            None,
        )

    def _box_offer(self) -> tuple[ToolSpec, ...]:
        """What the box now open is offering, whichever position it is asking about."""
        if self._adding is None:
            return ()
        return self._offer_over(self._adding) if self._anchored else self._offer_at(self._adding)

    def go_up(self) -> None:
        """Up: the previous card of whichever stack the position showing is.

        Two selections exist at once — which project the shelf is on and where
        the walk is — and the key moves the one the user is looking at. Moving
        both would leave the walk somewhere the user never went, in a graph they
        may not have opened yet. A third arrives while a box is open, and it
        takes the pair: the box is where the user is standing and the walk is
        behind it.
        """
        if self.adding:
            self.move_box(-1)
            return
        if self._control.current_position() == "project":
            self.select_project(self._project_at - 1)
            return
        self._walk_to(self._at - 1)

    def go_down(self) -> None:
        """Down: the next card of whichever stack the position showing is."""
        if self.adding:
            self.move_box(1)
            return
        if self._control.current_position() == "project":
            self.select_project(self._project_at + 1)
            return
        self._walk_to(self._at + 1)

    def select_project(self, index: int) -> None:
        """Move the accent to project `index`, and open nothing.

        Clamped rather than wrapped, for `_walk_to`'s reason. Nothing is read
        off disk here beyond what redrawing the shelf reads: selecting is the
        pointer's Up/Down, and a selection that opened a document would make
        arrowing down a library the most expensive keystroke in the app.
        """
        if not self._projects:
            return
        self._project_at = max(0, min(index, len(self._projects) - 1))
        self._control.set_project_select(self._build_project_select())

    def enter_project(self, index: int) -> None:
        """A project card's double click: select it, then open it and slide.

        Both halves, in `_open_step`'s order and for its reason — arriving at
        the pipeline position without having moved the selection would open
        whichever project the accent was on before.
        """
        if not self._projects:
            return
        self.select_project(index)
        self.open_project(self._projects[self._project_at])

    def new_project(self) -> None:
        """The library card's NEW PROJECT: ask where it goes, mint, stand on it.

        The ask comes first and nothing follows a cancelled one
        (`adr/a-project-lives-where-the-user-put-it.md`): a project lives where
        the user put it, so there is no directory this falls back to when it is
        given none.

        Standing on it rather than opening it, which is the referent's ruling
        and the reason the shelf is the position that mints: the chain pane
        would show a chain the project does not have, and the next act — adding
        sources — is a knob on the card the selection just landed on.

        The answer becomes the folder being listed, re-scanned rather than the
        new path being appended, so the shelf stays one folder's own answer in
        the folder's own order: a mint appended at the foot would be the one
        card out of sorted order until the next relaunch moved it. That the
        shelf is one folder at all is what the remembered list replaces
        (`todo/pinning-a-project-is-state-the-library-has-nowhere-to-put.md`).
        """
        directory = ask_where(self)
        if directory is None:
            return
        minted = mint(directory)
        self._library = directory
        self._projects = projects_in(directory)
        self._project_at = self._projects.index(minted)
        self._control.set_project_select(self._build_project_select())

    def reveal_project(self, index: int) -> None:
        """Show project `index` on disk, and move nothing.

        Not routed through `select_project` first, though the button only
        appears on the selected card: the index is the pane's answer to which
        card was pressed, and a select on the way past would make the one verb
        in the surface that acts on the selection also able to change it.
        """
        if not 0 <= index < len(self._projects):
            return
        reveal(self._projects[index])

    @property
    def region(self) -> int:
        """Which of the project's regions the stack is drawn for."""
        return self._region

    @property
    def selected_replicate(self) -> str | None:
        """Which replicate every parameter edit is addressed to, or the baseline.

        The window's own `_region` resolved against the document, and the one
        place that resolution is made: a form and an overlay reading it
        separately could open on one region and commit to another.

        `None` where the project has no replicates, which is the arm of the
        branch the surface had before there were any — an edit with no region to
        be about moves the node's baseline, and that is the value such a project
        runs (`core/pipeline_model.resolved_params`).
        """
        session = self._session
        if session is None or not session.project.replicates:
            return None
        return session.project.replicates[self._region].replicate_id

    def select_region(self, index: int) -> None:
        """A square in the fan: walk onto one of the regions the crop step cuts.

        The same kind of move as a card's click, so it is the same redraw: the
        fan, the walk and the stack below all show one region, and which one is
        as much the crop's value as where its box is. Clamped rather than
        wrapped, for `_walk_to`'s reason.
        """
        session = self._session
        if session is None or not session.project.replicates:
            return
        index = max(0, min(index, len(session.project.replicates) - 1))
        if index == self._region:
            return
        self._region = index
        self._redraw()

    def add_region(self) -> None:
        """The card's +: another region, carrying the showing one's box, selected.

        **Selected, which is the fan's selection moving from a gesture that is
        not a click on a square.** The region a user just made is the one they
        are about to place, and a + that left the walk where it was would make
        placing it a second gesture the surface never asked for.

        **It arrives pinned to the box it was copied from.** A replicate with no
        deviation follows the node's baseline, and the baseline is what the next
        edit on *any* region moves (`Project.with_param_edit`) — so an unpinned
        new region would be dragged along by an edit made to place its sibling,
        and the user would find a region they never touched sitting under the
        one they did. Copied rather than offset off it: the identity crop is
        larger than any frame (`tools/crop.WHOLE_FRAME`), and a fraction of that
        offset is a rectangle that clamps to nothing at all.

        Keyed on the step the fan hangs under, which is the step whose box the
        regions are deviations of and the only one whose value is denominated in
        a frame this window can name (`cuts_regions`). A project whose chain has
        no such step has no + to press.
        """
        session = self._session
        cutting = self._cutting()
        if session is None or cutting is None:
            return
        node = self._order[cutting]
        # Not None: `cuts_regions` found the node by having one.
        param = region_param(self._specs.get(node.node_id))
        box = session.project.params_for(node.node_id, self.selected_replicate).get(param)
        issue(
            session,
            AddReplicate(
                Replicate(
                    name=f"region {len(session.project.replicates) + 1}",
                    overrides={} if box is None else {node.node_id: {param: box}},
                )
            ),
        )
        self._region = len(session.project.replicates) - 1
        self._redraw()

    def remove_region(self) -> None:
        """The card's −: drop the region showing, and stand on what is left.

        **The selection moves down with it, and that is what this method is
        for.** `_region` is otherwise only ever clamped against a count that
        cannot shrink, and the fan indexes its tiles by it inside `paintEvent` —
        where an `IndexError` is thrown through a Qt virtual override and takes
        the process down rather than raising. So the verb that makes the count
        able to shrink is the verb that has to move it.

        The last one goes too. A project with no regions is the baseline run
        once, which is the state every project is minted in, and a floor here
        would make the first + a gesture with no way back
        (`session/intents.RemoveReplicate`).
        """
        session = self._session
        if session is None or not session.project.replicates:
            return
        issue(session, RemoveReplicate(session.project.replicates[self._region].replicate_id))
        self._region = max(0, min(self._region, len(session.project.replicates) - 1))
        self._redraw()

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

    def _build_project_select(self) -> QWidget:
        """The project position's content: a card per project file in the library.

        Built here rather than in `control.py` for `_build_pipeline_pane`'s
        reason — the track owns which position is showing and nothing about what
        is on one — and rebuilt whole on every move of the selection, because
        that is what the rest of the window does with a redraw.
        """
        select = ProjectSelect(listings(self._projects), self._project_at, self._library)
        select.selected.connect(self.select_project)
        select.opened.connect(self.enter_project)
        select.revealed.connect(self.reveal_project)
        select.minted.connect(self.new_project)
        return select

    def _reread_graph(self) -> None:
        """The five facts about the document's shape, taken together.

        Together because they are one derivation — the two folds that give each
        node its element kind and its output stream both read the specs and the
        walk, and what the chain starts from is what its sources resolved to —
        and because every caller that invalidates one has invalidated all five:
        a project opening, a step leaving the chain, and the window becoming the
        active one again.

        That third caller is not like the other two. The first four facts are
        folds over a document that only this window writes, so nothing can move
        them behind its back; the fifth read the filesystem, and a file dropped
        into a folder a source names moves it with no gesture and no run
        (`changeEvent`).
        """
        session = self._session
        if session is None:
            return
        pipeline = session.project.pipeline
        self._specs = resolved_specs(pipeline, self._registry)
        self._order = node_order(pipeline)
        self._elements = element_kinds(self._order, pipeline, self._specs)
        self._streams = stream_specs(self._order, pipeline, self._specs)
        self._resolved_sources = resolved_sources(self._order, self._specs)

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
        self._show_surfaces()
        self._rebind_editors()
        self._watch_the_pin()
        self.refill_graph()
        # Ahead of the refill this move just asked for, because that one is
        # deferred by a turn of the event loop and the picture is about the node
        # the walk is on *now*. The badge would not cover a viewport still
        # showing the previous node's output: it says the picture is the source,
        # and that picture is a render — of a node the walk has left.
        self._paint_viewport()

    @property
    def surfaces(self) -> Mapping[DisplaySurface, SurfacePanel]:
        """The pictures the current step's bands are dragged on, empty for most steps.

        The step pane's own, because a surface exists only while the step that
        declares it is being looked at — unlike the graph, which is the *pinned*
        step's and outlives every walk. Exposed for the reason the graph is: what
        a band drag repaints is these, and a painted pixel is not something a
        test or a benchmark can ask about.
        """
        pane = self._control.step_pane
        return pane.surfaces if isinstance(pane, StepPane) else {}

    @property
    def overlays(self) -> Mapping[str, Any]:
        """The composite-kind editors bound to the current step, by parameter.

        Exposed for the reason `surfaces` is: the gestures these carry are the
        ones a budget is measured through, and a benchmark that reached past them
        to `SetParam` would be timing the layer under the widget — which is the
        number the headless pass already has (`tests/bench/`). The type is
        `kind_editors`' own private one; nothing outside reads more of it than
        the gesture.
        """
        return self._editors

    def _show_surfaces(self) -> None:
        """Point the loop at the current step's surfaces, and at nothing otherwise.

        The current node and not the pinned one, which is the opposite of
        `_watch_the_pin` and for the same rule read the other way: the panels are
        *in* the step pane, so they can only ever be about the step on screen.
        Unconditionally rather than on a change, because the pane — and every
        panel in it — is rebuilt on every move of the walk, so there is no
        previous collector whose rows survive the move.
        """
        node = self.current_node
        self._tuning.show(None if node is None else node.node_id, self.surfaces)

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

        Each card also carries where its input came from, as positions in this
        same stack: the edges are the document's and the numbering is the walk's,
        and the pane draws the lines from the pair (`chain_stack.ChainColumn`).
        """
        session = self._session
        if session is None:
            return QWidget()
        at = {node.node_id: position for position, node in enumerate(self._order)}
        reads: dict[str, tuple[int, ...]] = {node.node_id: () for node in self._order}
        for edge in session.project.pipeline.edges:
            reads[edge.downstream] += (at[edge.upstream],)
        steps: list[Step] = []
        for position, node in enumerate(self._order):
            spec = self._specs.get(node.node_id)
            knobs = None
            if spec is not None:
                form = ParamForm(session, node.node_id, spec, replicate_id=self.selected_replicate)
                form.edited.connect(self.refill_graph)
                knobs = form
            steps.append(
                Step(
                    node=node,
                    knobs=knobs,
                    removable=removable(spec),
                    swappable=bool(self._offer_over(position)),
                    reads=reads[node.node_id],
                    regions=self._regions(position),
                )
            )
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
            on_swap=self.swap_step,
            on_add=self.add_step,
            fan=self._region_fan(),
            adding=self._adding_box(),
            outputs=self._outputs(session),
        )

    def _adding_box(self) -> Adding | None:
        """The box's state for the pane, or nothing where none is open.

        The offer is recomputed here rather than held beside `_adding`, for the
        output card's reason: it is a function of the position and the shelf, so
        a copy kept across a move of the box would be the one that went stale
        against the gap it is now in. What crosses into the pane is names — the
        surface renders a shortlist it is handed and computes nothing.
        """
        if self._adding is None:
            return None
        offer = self._box_offer()
        return Adding(
            site=self._adding,
            offer=tuple(spec.tool_id for spec in offer),
            lit=self._offer % len(offer) if offer else 0,
            on_take=self._take,
            anchored=self._anchored,
        )

    def _take(self, position: int) -> None:
        """A click on an offer: light it, and take it. The pointer's Right-then-enter."""
        self._offer = position
        self.take_offer()

    def _outputs(self, session: Session) -> Outputs:
        """The card at the foot of the chain, and the writes reaching into it.

        Derived on every redraw from the document's own two lists rather than
        held: the card is a picture of what the run keeps, so a copy of the write
        list here would be the one that went stale against a tick
        (`adr/the-output-card-is-a-picture-of-the-write-list.md`). Nothing is
        added to the graph by any of it — the edges are view state, and a tick
        moves no cache key.

        Drawn whether or not anything is kept, because it is also the way to the
        form that keeps things: a card that appeared once the first box was
        ticked would be reachable only from the screen it leads to.
        """
        at = {node.node_id: position for position, node in enumerate(self._order)}
        return Outputs(
            writes=tuple(
                Write(at[node_id], product)
                for node_id, product in kept_products(session.project, self._specs)
            ),
            on_open=self._control.show_save,
        )

    def _cutting(self) -> int | None:
        """Which position's box the project's regions are deviations of.

        The first such step rather than every one: a second region at a second
        root is a second box on the same footage, and which of them the
        replicates deviate at is a question the document does not answer. Two
        fans drawn off one selection would be two pictures claiming to be the
        same walk, so the branch hangs where the chain first cuts and the second
        root keeps the plain arrow it already had.

        One answer for the three surfaces that need it — the fan, the count row,
        and the node the + keys its override on — because a second reading could
        add a region at one step and draw it under another.
        """
        session = self._session
        if session is None:
            return None
        pipeline = session.project.pipeline
        return next(
            (
                position
                for position, node in enumerate(self._order)
                if cuts_regions(self._specs.get(node.node_id), node.node_id, pipeline)
            ),
            None,
        )

    def _regions(self, position: int) -> Regions | None:
        """The count row for `position`, or nothing on a step that cuts none.

        Offered at zero, unlike the fan: the row is where a region is made, so a
        project reduced to its baseline would otherwise have taken away the one
        gesture that gets a branch back.
        """
        session = self._session
        if session is None or position != self._cutting():
            return None
        return Regions(
            count=len(session.project.replicates),
            selected=self._region,
            on_add=self.add_region,
            on_drop=self.remove_region,
        )

    def _region_fan(self) -> Fan | None:
        """The branch the region step makes, or nothing where there is none.

        The regions are the project's replicates, in the document's order: a
        replicate's box is a per-replicate override of this step's own region
        parameter (`core/pipeline_model.Replicate`), so the fan is that value's
        editor and holds no list of its own. A project with no replicates runs
        the step's baseline once and has no branch to draw.
        """
        session = self._session
        cutting = self._cutting()
        if session is None or cutting is None or not session.project.replicates:
            return None
        return Fan(
            position=cutting,
            regions=tuple(replicate.name for replicate in session.project.replicates),
            selected=self._region,
            on_select=self.select_region,
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
        pane = StepPane(
            self._at + 1,
            node,
            session,
            self._specs[node.node_id],
            replicate_id=self.selected_replicate,
        )
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
        screen = SaveScreen(session, self._specs)
        # A tick is an edge into the output card, so it redraws the stack behind
        # this screen — the picture is derived from the document and there is
        # nothing to update in place.
        screen.checked.connect(self._redraw)
        return screen

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
        replicate_id = self.selected_replicate
        self._editors = dict(
            bind_editors(
                session,
                node.node_id,
                self._specs[node.node_id],
                session.project.params_for(node.node_id, replicate_id),
                canvas=self._viewport,
                timeline=self._timeline.strip,
                region_extent=extent,
                bands=self.surfaces,
                replicate_id=replicate_id,
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
    # No projects and no folder. The directory the process started in is not a
    # library and nothing else is either (`adr/a-project-lives-where-the-user-
    # put-it.md`), so the first launch opens on an empty shelf whose one gesture
    # asks. What will fill it is the remembered list of locations the app has
    # been shown, which is not this window's to invent
    # (`todo/pinning-a-project-is-state-the-library-has-nowhere-to-put.md`).
    window = MainWindow(())
    size_window(window)
    sys.exit(application.exec())
