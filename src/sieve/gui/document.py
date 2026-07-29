"""The editable replicate document: a `ReplicateSet` plus its undo history.

Every mutation goes through a `QUndoCommand`, without exception. That is not
ceremony — it is the only way Ctrl+Z stays honest as edit paths multiply. A
single method that mutates the set directly is a silent hole in the history,
and holes in undo are discovered by users, not by tests.

The document is GUI-side because undo is GUI state: it never reaches the
pipeline artifact. The data it edits is `core`, and stays `core`.

What it edits has grown past the replicates its name records — the graph those
replicates deviate from, and the representative clip they are tuned over. They
are here because they share the one thing a document is for: a source binding
they are all invalidated by, and an undo stack the user expects to cover the
whole window rather than one table in it.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QUndoStack

from sieve.core.pipeline_model import (
    ClipRange,
    CropArtifact,
    DetectorSettings,
    Node,
    Pipeline,
    Project,
    edited_detector,
    edited_params,
    equivalence_groups,
    resolved_detector,
    resolved_params,
)
from sieve.core.replicates import Replicate, ReplicateSet
from sieve.core.types import ROI
from sieve.gui.commands import (
    AddReplicate,
    EditDetector,
    EditTuningParams,
    RemoveReplicate,
    RenameReplicate,
    ResetTuning,
    RestoreSnapshot,
    SetClip,
    SetReplicateROI,
    SetReplicateROIs,
)
from sieve.gui.crop_binding import CropBacking, CropState, backing_for
from sieve.gui.timeline_model import containing, effective_window, ended_at, fitted, moved_to
from sieve.pipeline.dag import graph_needs_chroma


@dataclass(frozen=True)
class DocumentState:
    """The whole of what a document owns, in one comparable value.

    What a rollback moves the document between, and deliberately *not* a
    `Project`: `source`, `checkpoints`, and `outputs` are the window's, so a
    state that carried them would let a restore silently rewrite fields the GUI
    is not allowed to edit. Restoring a snapshot must return the user's editing
    to an earlier point, not reassign the video underneath it.

    Frozen and compared by value, which is what lets `restore` refuse a no-op:
    picking the snapshot you are already at should not stack a history entry.

    The geometry lock's visitation set is absent for a different reason than
    those three, and a deliberate one: it is edited by the GUI, but not by the
    *user*. Rolling back to Friday's geometry does not unsee the arena, and a
    restore that reinstated a dropped lock would re-arm it behind a user who
    had already been asked and had already answered.
    """

    replicates: tuple[Replicate, ...]
    pipeline: Pipeline
    detector: DetectorSettings | None
    clip: ClipRange | None


@dataclass(frozen=True)
class SourceHome:
    """Where the bound footage is, what it is, and what its crops sit beside.

    The three facts a crop record cannot be read without, carried as one value
    for `ResolvedSource`'s reason: a caller holding `project_dir` without
    `identity` would resolve a path and then match it against nothing, and one
    holding `identity` without `video` would know a record is stale and have
    nothing to re-cut from.

    `project_dir` is the directory `CropArtifact.path` is relative to — the
    project file's home once there is one, and the conventional home beside the
    video until then, exactly as `MainWindow._retarget_history` anchors history.
    An artifact written before the first save must not become unfindable by the
    save.
    """

    video: Path
    project_dir: Path
    identity: str


@dataclass(frozen=True)
class _Gesture:
    """One continuous geometry drag, and the box it started from."""

    token: int
    index: int
    roi: ROI


class ReplicateDocument(QObject):
    """Ordered replicates for one source video, with undo/redo."""

    #: A row was added or removed. Views rebuild; the count changed.
    structure_changed = Signal()
    #: The replicate at this row was edited in place.
    replicate_changed = Signal(int)
    #: A row was added at this position, by a user action or a redo.
    replicate_added = Signal(int)
    #: The graph changed, so every replicate's equivalence group may have. No
    #: row index: a parameter edit anywhere can move any replicate into or out
    #: of any group, so there is no smaller claim to make than "all of them".
    grouping_changed = Signal()
    #: The representative clip was placed, moved, or dropped.
    clip_changed = Signal()
    #: A source was bound or unbound, so the length and frame rate everything
    #: is measured against have changed. Distinct from `structure_changed`,
    #: which also fires for every added row: the timeline's whole horizontal
    #: axis is the source's length, and rebuilding it per replicate would reset
    #: the window controls under a user who is typing into them.
    source_changed = Signal()
    #: A node baseline or a parameter pin moved — a knob edit, its undo, or a
    #: reset. The tab re-resolves what the selected replicate runs with and
    #: re-renders; no payload names *which* node, because a reset moves them
    #: all and the tab resubmits the whole prefix either way.
    tuning_changed = Signal()
    #: The detector baseline or a detector pin moved. Separate from
    #: `tuning_changed` because the response differs in kind: parameters
    #: re-run extraction through the runner, the detector re-derives over the
    #: retained series.
    detector_changed = Signal()
    #: The graph's *structure* was replaced — a load, or a step added,
    #: swapped, or removed. Views rebuild from the pipeline rather than
    #: re-resolving values into an existing shape.
    pipeline_changed = Signal()
    #: The set of crop records changed — one was written, or one discarded.
    #: Separate from every signal above because nothing about the *document*
    #: moved: what changed is which replicates are read from a file at rest,
    #: which is a storage fact the render worker and the source card follow and
    #: no undo entry covers.
    crops_changed = Signal()
    #: An edit was refused because a materialized crop depends on it standing
    #: still, with the reason as the user can read it. Rule 6's mirror: a freeze
    #: that silently swallowed the gesture would look like a control that does
    #: nothing rather than one that is frozen.
    edit_refused = Signal(str)
    #: A different replicate is the one being tuned — or none is. Not emitted
    #: when a removal above the selection merely shifts its row number: the
    #: arena on screen is the same arena, and a re-render of it would say
    #: nothing new. Views that track the *row* resync on `structure_changed`.
    selection_changed = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._replicates = ReplicateSet()
        self._pipeline = Pipeline()
        self._detector: DetectorSettings | None = None
        self._source_size: tuple[int, int] | None = None
        self._source_frames = 0
        self._source_fps = 0.0
        self._clip: ClipRange | None = None
        self._selected: int | None = None
        #: Replicates opened in the filter tab, by id — the geometry lock's
        #: state, saved with the project and *not* on the undo stack. See
        #: `mark_visited`.
        self._visited: set[str] = set()
        #: Materialized crops of the bound source, in document order — owned
        #: the way `_visited` is: edited by the GUI, saved with the project,
        #: and off the undo stack, because what a record describes is a file
        #: that exists and Ctrl+Z does not un-write a file.
        self._crops: tuple[CropArtifact, ...] = ()
        #: Where those records are relative to, and what they were cut from.
        #: None until a source is bound; set by the window, which is the one
        #: object that knows both the video and the project's home.
        self._home: SourceHome | None = None
        #: The live geometry gesture: its token, the row, and where the box was
        #: before the first step of it. Held so a refused move can be put back
        #: exactly, which the command cannot do for itself — its `_previous` is
        #: private and a caller asking for it would be asking the undo stack to
        #: report a state it is in the middle of building.
        self._gesture: _Gesture | None = None
        self.undo_stack = QUndoStack(self)

    # ---- reading ---------------------------------------------------------

    def __len__(self) -> int:
        return len(self._replicates)

    def at(self, index: int) -> Replicate:
        """Replicate at `index`."""
        return self._replicates[index]

    def all(self) -> list[Replicate]:
        """Snapshot of every replicate, in order."""
        return self._replicates.as_list()

    @property
    def selected_index(self) -> int | None:
        """Row of the replicate being tuned, or None when there are none.

        The one answer to "which arena am I looking at". The executor has
        cropped per replicate since it was written; this is the selection that
        decides which crop, so it is here rather than on a view — two views
        each keeping their own answer is the failure the transport had before
        the timeline replaced it. None only while the document holds no
        replicates: every mutation below keeps the selection on a real row
        while one exists.
        """
        return self._selected

    @property
    def selected_replicate(self) -> Replicate | None:
        """The replicate being tuned, or None when there are none.

        What the preview path takes: the filter tab hands exactly this to
        `PreviewRunner`, and None means the graph runs over the whole frame —
        which is the honest reading of a project with no arenas cut yet.
        """
        return None if self._selected is None else self._replicates[self._selected]

    @property
    def source_size(self) -> tuple[int, int] | None:
        """Dimensions of the video these replicates were cut from."""
        return self._source_size

    @property
    def source_frames(self) -> int:
        """Length of the bound source, zero when nothing is bound."""
        return self._source_frames

    @property
    def source_fps(self) -> float:
        """Frame rate of the bound source, zero when nothing is bound.

        Held only so a window has a length before the user has chosen one —
        ten seconds is a count of frames and there is no other way to know how
        many. Nothing else here is in the time domain.
        """
        return self._source_fps

    @property
    def window(self) -> ClipRange | None:
        """The span the timeline shows and playback is bounded by.

        `clip` below, or the default window until the user has chosen one. The
        fallback is derived on every read rather than written into `_clip`,
        which is the difference between a *tuning-session* rule and a document
        rule: a project saved straight after opening a video must still come
        back with `clip` unset, because that is what makes `plan.py` run the
        whole video and what the HPC handoff produces by dropping the field.
        Resolving it on open would make an unset clip unreachable from the GUI.

        `None` only when nothing is bound.
        """
        return effective_window(self._clip, self._source_frames, self._source_fps)

    @property
    def clip(self) -> ClipRange | None:
        """The representative span tuning runs against, or None for all of it.

        None is not "the whole video" written a shorter way — it is the state
        where the user has not chosen yet, and `pipeline/plan.py` already draws
        that distinction by building a full-length span from a `Project` whose
        `clip` is `None`. Keeping the absence here means a project saved before
        the user marked anything does not come back claiming they marked
        everything.

        This is what a project is saved from; `window` above is what the user is
        looking at. The two differ exactly while nothing has been chosen.
        """
        return self._clip

    @property
    def pipeline(self) -> Pipeline:
        """The graph these replicates are processed by, empty until one is set.

        The document holds it rather than resolving it from somewhere on demand
        because a replicate's deviation is stored against a node id: without
        the graph, `overrides` is a mapping whose keys name nothing and the
        equivalence groups below cannot be computed at all.
        """
        return self._pipeline

    @property
    def detector(self) -> DetectorSettings | None:
        """The detector baseline, or None while nothing has been tuned.

        What a save writes. The GUI never renders this directly — it renders
        `resolved_detector_for`, which is this resolved against the selected
        replicate with the never-tuned fallback applied.
        """
        return self._detector

    def detector_baseline(self) -> DetectorSettings:
        """The baseline an edit diffs against: tuned, or the source's defaults.

        The fallback is derived on every read rather than written into
        `_detector`, for `window`'s reason one section up: a project saved
        before anyone touched the detector must come back with `detector`
        unset, and resolving the fallback into the field would make that
        state unreachable. "One second of D" needs the frame rate, which is
        why this is a method on the document and not a constant on the model.
        """
        return self._detector or DetectorSettings.default_for(self._source_fps)

    def resolved_node_params(self, node_id: str) -> dict[str, Any]:
        """What `node_id` runs with for the selected replicate.

        A lookup around `resolved_params` — the one definition — against the
        selection, because "the values on screen" is always a question about
        the arena being tuned.

        Raises:
            KeyError: if `node_id` names nothing.
        """
        return resolved_params(self._pipeline.node(node_id), self.selected_replicate)

    def resolved_detector_for_selection(self) -> DetectorSettings:
        """The detector values the selected replicate runs with."""
        return resolved_detector(self.detector_baseline(), self.selected_replicate)

    def equivalence_groups(self) -> tuple[int, ...]:
        """Group number per row, derived on every call.

        Delegates to `core`, and must keep doing so — the number a table paints
        and the number a report prints have to come from one definition, for the
        same reason `resolved_params` is the only answer to what a node runs
        with. An empty graph puts every replicate in group 1, which is the
        correct answer to "which of these run the same thing" when the answer is
        "nothing yet".
        """
        return equivalence_groups(self._pipeline, self._replicates.as_list(), self._detector)

    # ---- the source boundary ---------------------------------------------
    # Crops are read here and nowhere else in the GUI. `gui/crop_binding.py`
    # holds the rule; this section is the one place that has all four of its
    # inputs at once — the records, the replicates, the parent's identity, and
    # the format the graph decodes — so the card, the box, and the timeline
    # handles cannot end up asking three slightly different questions.

    @property
    def crops(self) -> tuple[CropArtifact, ...]:
        """The crop records for the bound source, in document order."""
        return self._crops

    @property
    def source_home(self) -> SourceHome | None:
        """Where the footage and its crops live, or None while nothing is bound."""
        return self._home

    def set_source_home(self, home: SourceHome | None) -> None:
        """Declare where the bound footage is and what its records sit beside.

        Called on open and after every save: a Save As moves the project's home
        and the records must be re-expressed against it *before* they are stored
        here, which is the window's job (`Project.relocated` is the one rebasing
        rule) — this setter only records where they now point.
        """
        self._home = home

    def set_crops(self, crops: Iterable[CropArtifact]) -> None:
        """Replace the record set wholesale — a load, or a save that rebased them."""
        records = tuple(crops)
        if records == self._crops:
            return
        self._crops = records
        self.crops_changed.emit()

    def register_crop(self, artifact: CropArtifact) -> None:
        """Record a crop that has just been written and verified.

        Not a command, for `mark_visited`'s reason turned up one notch: the
        file is on disk, and an undo that dropped its record would leave a
        verified artifact the session can no longer find while the folder still
        holds it. Discarding is the inverse gesture, and it is explicit.

        Replacement rather than append, keyed on `CropArtifact.identity` — the
        same rule `Project.with_crop` states, reached by handing it the set
        rather than restated here, so a re-cut after a deleted file replaces its
        record in place instead of producing the pair the artifact refuses.
        """
        self.set_crops(self._as_project().with_crop(artifact).crops)

    def discard_crop(self, artifact: CropArtifact) -> None:
        """Drop the record of `artifact`'s cut, unfreezing what it held still.

        The file is not touched here — deleting it is the caller's separate act
        (`Project.without_crop` states the same split), because a record dropped
        while the file survives is exactly the never-registered state the writer
        already treats as safe.
        """
        self.set_crops(self._as_project().without_crop(artifact).crops)

    def _as_project(self) -> Project:
        """The record set as the model holds it, for one of its own operations.

        A scratch `Project` carrying nothing but the crops: `with_crop` and
        `without_crop` are the one home for what makes two records the same
        record, and a document that reimplemented the identity comparison would
        be a second answer to it. The video it names is never read — the paths
        on the records are already relative to the real home.
        """
        return Project.for_video(Path("scratch.mp4"), Path()).with_crops(self._crops)

    def crop_backing(self, index: int) -> CropBacking:
        """Which of the four states the replicate at `index` is in.

        `ABSENT` whenever nothing is bound: with no home there is no directory
        to resolve a record against, so "no artifact backs this" is the only
        answer that is true rather than merely unavailable.
        """
        home = self._home
        if home is None or not 0 <= index < len(self._replicates):
            return CropBacking(CropState.ABSENT)
        return backing_for(
            self._crops,
            index,
            self._replicates.as_list(),
            source=home.identity,
            luma=self.decodes_luma(),
            project_dir=home.project_dir,
            window=self.window,
        )

    def decodes_luma(self) -> bool:
        """Whether the current graph decodes the luma plane. Never a choice.

        A consequence of the chain (`Dag.needs_chroma`), and public because the
        write pass has to be handed the same answer the matching rule will use:
        an artifact written in the other format is one the next render declines,
        which is a minute of encoding spent on a file nothing will read.
        """
        return not graph_needs_chroma(self._pipeline)

    # ---- lifecycle -------------------------------------------------------

    def set_pipeline(self, pipeline: Pipeline) -> None:
        """Attach a graph, announcing that every group number may have moved.

        Not undoable and not a command: this is how a loaded project or a
        future graph editor hands the document the graph, not a user edit to
        it. When there is a GUI that edits nodes, its edits go through the undo
        stack and land here — the setter stays the one write either way.
        """
        if pipeline == self._pipeline:
            return
        self._pipeline = pipeline
        self.grouping_changed.emit()

    def sync_structure(self, pipeline: Pipeline) -> None:
        """Adopt `pipeline`'s structure, keeping the baselines this document owns.

        The tab's structural edits — a step added, swapped, or removed — land
        here. Incoming nodes whose id the document already carries keep the
        *document's* parameters: the tab's copy of a node holds the values
        resolved for the selected replicate, and adopting those as the
        baseline would silently promote one arena's pins to the default for
        all of them. A node the document has never seen is genuinely new and
        its parameters are its freshly minted defaults, which is exactly what
        a baseline starts as.

        Pins naming nodes the new structure lost are dropped, because the
        artifact refuses them (`Project._references_resolve`) — a deviation on
        a deleted node is a parameter set nothing will ever read. Dropped
        outside undo, as the structural edit itself is: the wizard's Cancel is
        its own restore path, and a removal is offered no way back today.

        Not a command and not undoable, for `set_pipeline`'s reason.
        """
        nodes = tuple(
            self._pipeline.node(node.node_id) if node.node_id in self._pipeline else node
            for node in pipeline.nodes
        )
        merged = pipeline.model_copy(update={"nodes": nodes})
        surviving = {node.node_id for node in nodes}
        pruned = ReplicateSet(
            replicate.with_overrides_limited_to(surviving) for replicate in self._replicates
        )
        if merged == self._pipeline and pruned.as_list() == self._replicates.as_list():
            return
        self._pipeline = merged
        self._replicates = pruned
        self.pipeline_changed.emit()
        self.grouping_changed.emit()

    def bind_source(self, width: int, height: int, frame_count: int = 0, fps: float = 0.0) -> None:
        """Attach to a new source video, discarding replicates and history.

        Replicates are geometry in one video's pixel space; carrying them
        across a file open would silently reinterpret them against different
        dimensions. Clearing is not undoable for the same reason — there is no
        coherent state to return to once the source is gone.

        The clip goes for the same reason, one axis over: it is geometry in the
        source's *frame index* space, and frame 4000 of a different video is a
        different moment or no moment at all. `frame_count` is what the marks
        are clamped against, and defaults to zero so a caller that does not know
        it gets a document where no clip can be set rather than one where a mark
        lands somewhere unverifiable. `fps` is what makes the default window ten
        *seconds* rather than a frame count; a caller that does not know it gets
        a window over the whole asset, which is the honest answer when nothing
        has said how long a second is.

        The graph goes with them. It is not geometry and would survive the
        reinterpretation, but a replicate's deviation is keyed by node id, so
        keeping the graph while dropping every replicate leaves a set of
        defaults tuned against footage nobody is looking at any more.
        """
        self._source_size = (width, height)
        self._source_frames = max(frame_count, 0)
        self._source_fps = max(fps, 0.0)
        self._reset()
        self.source_changed.emit()
        self.structure_changed.emit()
        self.clip_changed.emit()

    def unbind_source(self) -> None:
        """Detach from any source video."""
        self._source_size = None
        self._source_frames = 0
        self._source_fps = 0.0
        self._reset()
        self.source_changed.emit()
        self.structure_changed.emit()
        self.clip_changed.emit()

    def _reset(self) -> None:
        """Drop replicates, clip, graph, detector, selection, and history silently."""
        self._replicates.clear()
        self._pipeline = Pipeline()
        self._detector = None
        self._clip = None
        self._selected = None
        self._visited.clear()
        # The records go with the source, not with the home: they are cuts of
        # *this* footage, and the next video's boundary starts empty. The home
        # itself is the window's to reassign, and it does so as the new source
        # binds.
        self._crops = ()
        self._gesture = None
        self.undo_stack.clear()

    # ---- project ---------------------------------------------------------

    def load_project(self, project: Project) -> None:
        """Fill the document from a saved project, replacing whatever is here.

        The load path the command-facing primitives below could not be. It
        writes all three fields at once and records no history, because a load
        has no prior state for Ctrl+Z to return to — the document it is
        replacing belongs to a source that has already been unbound.

        Ordering is why this exists as its own method rather than as a sequence
        of calls from the window. `bind_source` clears replicates, clip, and
        graph, and it must: geometry in one video's pixel space cannot carry to
        another. Opening a project opens its video first, so the clear always
        lands *between* reading the file and populating from it, and anything
        that went through `add_roi` or `mark_clip_in` would be wiped by the very
        bind that made the source known.

        Everything is refitted to the source actually bound rather than trusted.
        A project names its video by path, and a path is not a promise about
        dimensions or length — footage re-encoded at another resolution, or
        truncated, would otherwise return as replicates hanging off the frame
        and a clip pointing past the end of it.
        """
        self._replicates = ReplicateSet(
            replicate.with_roi(self._fit(replicate.roi)) for replicate in project.replicates
        )
        self._pipeline = project.pipeline
        self._detector = project.detector
        self._clip = self._fit_clip(project.clip)
        # The locks come back with the file. A lock that evaporated on close
        # would protect only the session that did not need it: the drag that
        # costs a user a week of tuning is the one they make on Monday over
        # footage they tuned on Friday.
        self._visited = set(project.visited)
        # And so do the crops, unrefitted: a record is a claim about a file on
        # disk, and `backs` re-checks every clause of it against the source
        # actually bound. Trimming them here would be guessing at a question
        # `crop_backing` answers exactly, one replicate at a time.
        self._crops = project.crops
        # No `crops_changed` for them: the window is mid-adoption and has not
        # yet said where this project's home is, so a listener that re-read the
        # records now would resolve them against the *previous* project's
        # directory. Adoption declares the home and the records together.
        # The first row, not none: a loaded project must open looking at *an*
        # arena, and with nothing remembered in the file the first is the only
        # unarbitrary one.
        self._selected = 0 if len(self._replicates) else None
        self.undo_stack.clear()
        self.structure_changed.emit()
        self.grouping_changed.emit()
        self.selection_changed.emit()
        # After the selection, so a view rebuilding its chain from the graph
        # already sees the restored selection and resolves the right arena's
        # values.
        self.pipeline_changed.emit()
        self.detector_changed.emit()
        # Last, and after the graph above all: `clip_changed` is a render
        # trigger, and one that fired before `pipeline_changed` submitted a
        # render of whatever chain the tab held *before* the load — a stale
        # graph holding the runner's slot while the loaded one queued.
        self.clip_changed.emit()

    def apply_to(self, project: Project) -> Project:
        """`project` carrying this document's replicates, clip, detector, and graph.

        A copy of something else rather than a project built from nothing, and
        that is the whole point: `source`, `checkpoints`, and `outputs` are
        fields the GUI cannot edit, so a save that assembled a fresh `Project`
        would silently drop every sink a project was opened with. Handing back
        the document it came from is what keeps open-save-reopen identical in
        the parts nothing touched.

        The graph goes last because `with_pipeline` is the validating one, and
        by then it can see the replicates whose overrides have to name nodes in
        it.

        Raises:
            ValidationError: if the graph no longer carries a node something
                references. Nothing in the GUI edits the graph yet, so this is
                unreachable today and deliberately not caught here — a save
                that cannot name what went wrong is worse than one that raises.
        """
        return (
            project.with_replicates(tuple(self._replicates))
            # After the replicates and before the graph: `with_visited` drops
            # ids that name no replicate, which is how a deleted arena's lock
            # leaves the file without the document having to prune on every
            # removal — and be re-locked by an undo of that removal.
            .with_visited(self._visited)
            .with_clip(self._clip)
            .with_detector(self._detector)
            .with_pipeline(self._pipeline)
            # Last, and after the graph, because `with_crops` validates the
            # whole project: run before `with_pipeline` it would judge the
            # intermediate state, where the replicates already carry pins
            # naming nodes the old graph does not have. Wholesale, because the
            # document is the live set — an artifact written this session is on
            # disk whether or not the `Project` this copies from predates it,
            # and a save that kept the base's crops would drop the record and
            # leave the file orphaned. The paths are relative to
            # `source_home.project_dir`, which is what makes the window's
            # relocate-after-assemble ordering load-bearing.
            .with_crops(self._crops)
        )

    def capture(self) -> DocumentState:
        """Everything this document owns, right now.

        What autosave writes and what a restore's undo puts back. Cheap: every
        field is already immutable or is copied into a tuple here, so the value
        does not move when the document does.
        """
        return DocumentState(
            replicates=tuple(self._replicates),
            pipeline=self._pipeline,
            detector=self._detector,
            clip=self._clip,
        )

    def state_from_project(self, project: Project) -> DocumentState:
        """`project`'s editable half, refitted onto the source actually bound.

        `load_project`'s refitting, factored out and reused for the same reason
        it exists there: a snapshot names its video by path, and a path is not a
        promise about dimensions or length. A history file written before the
        footage was re-encoded must not come back as replicates hanging off the
        frame.
        """
        return DocumentState(
            replicates=tuple(
                replicate.with_roi(self._fit(replicate.roi)) for replicate in project.replicates
            ),
            pipeline=project.pipeline,
            detector=project.detector,
            clip=self._fit_clip(project.clip),
        )

    def restore(self, state: DocumentState, text: str) -> None:
        """Roll the document back to `state`, as an undoable action.

        The rollback half of "no save prompts": the user is never asked to
        predict a mistake, and the correction for one they have made is on the
        undo stack like everything else. Restoring is therefore itself covered
        by the net — a restore chosen by accident is one Ctrl+Z, not a hunt
        through the history of histories.
        """
        if state == self.capture():
            return
        self.undo_stack.push(RestoreSnapshot(self, state, text))

    def _fit_clip(self, clip: ClipRange | None) -> ClipRange | None:
        """A saved span trimmed onto the bound source, or `None` if none of it lands.

        `None` out is a different statement from `None` in, and both are honest:
        it means the span that was saved covers no frame of the video that is
        actually open, which is the state a user is in before they have chosen
        anything. Clamping it to the last frame instead would hand back a
        one-frame clip nobody marked.
        """
        return fitted(clip, self._source_frames)

    # ---- user intents ----------------------------------------------------

    def select(self, index: int) -> None:
        """Make the replicate at `index` the one being tuned.

        Not a command and not undoable, for `set_pipeline`'s reason: it does
        not change what a save writes, only which arena the session is looking
        at, and a Ctrl+Z that hopped the selection around between real edits
        would be undoing things the user never thinks of as edits.

        A row that does not exist is refused rather than read as "none": there
        is no deselection gesture, because "no replicate selected" is not a
        state the tuning loop has a rendering for while replicates exist.

        Re-selecting the current row emits nothing, and that is kept: a re-emit
        would make `select` a refresh primitive, which every caller would then
        inherit. Views that must notice an edit to the selected arena listen to
        `replicate_changed`, which is the signal that actually carries one.
        """
        if not 0 <= index < len(self._replicates) or index == self._selected:
            return
        self._selected = index
        self.selection_changed.emit()

    def edit_params(self, changes_by_node: Mapping[str, Mapping[str, Any]], text: str) -> None:
        """Tune node parameters for the arena being looked at.

        The GUI's entry to the two-write mechanism: the submitted fields move
        each node's baseline, and whatever actually changed against what the
        selected replicate resolved to is pinned on it — so an untouched
        arena keeps following, and a touched one deviates by exactly the
        fields touched. Submit only what the user edited; see
        `core.pipeline_model.edited_params` for why a whole resolved view
        must not be submitted.

        A no-op edit — every submitted value already resolved — pushes
        nothing, so re-committing a spinbox does not stack history.

        Raises:
            KeyError: if a node id names nothing in the graph.
        """
        if not self._would_change(changes_by_node):
            return
        self.undo_stack.push(EditTuningParams(self, self._selected, changes_by_node, text))

    def _would_change(self, changes_by_node: Mapping[str, Mapping[str, Any]]) -> bool:
        replicate = self.selected_replicate
        for node_id, params in changes_by_node.items():
            node = self._pipeline.node(node_id)
            if replicate is None:
                if {**node.params, **params} != node.params:
                    return True
            else:
                moved, pinned = edited_params(node, replicate, params)
                if moved.params != node.params or pinned.overrides != replicate.overrides:
                    return True
        return False

    def edit_detector(
        self, changes: Mapping[str, Any], text: str, *, gesture: int | None = None
    ) -> None:
        """Tune the detector for the arena being looked at.

        `edit_params` for the detection suffix, with `set_roi`'s gesture
        contract: steps of one continuous drag share a token and collapse to
        a single undo entry; a discrete edit passes nothing and stands alone.

        Raises:
            ValidationError: if `changes` names no such field or misfits one.
        """
        baseline = self.detector_baseline()
        replicate = self.selected_replicate
        if replicate is None:
            moved = DetectorSettings.model_validate({**baseline.model_dump(), **changes})
            unchanged = self._detector is not None and moved == self._detector
        else:
            moved, pinned = edited_detector(baseline, replicate, changes)
            unchanged = (
                self._detector is not None
                and moved == self._detector
                and pinned.detector_overrides == replicate.detector_overrides
            )
        if unchanged:
            return
        self.undo_stack.push(EditDetector(self, self._selected, changes, text, gesture=gesture))

    def reset_tuning(self, defaults_by_node: Mapping[str, Mapping[str, Any]]) -> None:
        """Return named baselines to their defaults and drop every pin.

        One undo entry however many replicates were following their own
        values, for `set_all_to_size`'s reason. `defaults_by_node` names the
        nodes that *have* defaults — a step the user inserted is absent and
        keeps its parameters.
        """
        self.undo_stack.push(ResetTuning(self, defaults_by_node))

    def add_roi(self, roi: ROI) -> None:
        """Append a replicate covering `roi`, named with the next free default."""
        replicate = Replicate(roi=self._fit(roi), name=self._replicates.next_default_name())
        self.undo_stack.push(AddReplicate(self, len(self._replicates), replicate))

    def remove(self, index: int) -> None:
        """Delete the replicate at `index`."""
        if not 0 <= index < len(self._replicates):
            return
        self.undo_stack.push(RemoveReplicate(self, index))

    def rename(self, index: int, name: str) -> bool:
        """Give the replicate at `index` a new display name.

        Returns whether the name was taken. An empty or unchanged name is not,
        and the caller cannot work that out for itself without reimplementing
        the strip-and-compare above — `Qt`'s `setData` has to answer "did the
        model change?" and answering it wrongly costs the user their feedback.
        """
        name = name.strip()
        if not name or name == self._replicates[index].name:
            return False
        self.undo_stack.push(RenameReplicate(self, index, name))
        return True

    def set_roi(
        self,
        index: int,
        roi: ROI,
        *,
        gesture: int | None = None,
        text: str | None = None,
    ) -> None:
        """Give the replicate at `index` new geometry.

        `gesture` is a token identifying one continuous drag, and passing the
        same token on every step of that drag is what collapses it to a single
        undo entry — see `SetReplicateROI`. A caller with a discrete edit (a
        typed number) passes nothing and gets its own step.

        The ROI still goes through `_fit` even when the caller has already
        clamped it against the frame, which for a placement it has: `_fit`
        leaves a region that is already inside untouched, so the safety net
        costs a stamp none of its exact extent.

        **A materialized crop does not hold the box still.** It used to, and
        that was the wrong trade: an artifact is an acceleration, and an
        acceleration that refuses an edit has stopped being one. A moved box
        misses `CropArtifact.backs` on the ROI by construction, so the render
        falls back to the parent — same pixels, same keys, slower — and the card
        says the region has moved since. The file is still there to be re-cut or
        discarded, and neither is a prerequisite for moving anything.
        """
        # Before the no-op check below, not after: a gesture whose first step
        # lands the box exactly where it already was is still that gesture, and
        # recording its origin one step later would record a box that has
        # already moved.
        if gesture is not None and (self._gesture is None or self._gesture.token != gesture):
            self._gesture = _Gesture(token=gesture, index=index, roi=self._replicates[index].roi)
        fitted = self._fit(roi)
        if fitted == self._replicates[index].roi:
            return
        self.undo_stack.push(SetReplicateROI(self, index, fitted, gesture=gesture, text=text))

    def finish_roi_gesture(
        self,
        index: int,
        gesture: int,
        confirm: Callable[[Replicate], bool],
    ) -> None:
        """Close a live drag, refusing it first if the arena has been tuned.

        The geometry lock, and the whole of it. A replicate that has been opened
        in the filter tab has had work done *against* its geometry, so moving
        its box is refused and then offered: `confirm` is called once, with the
        replicate as it now stands, and returns whether the user accepts what
        the move costs. It is a callback rather than a dialog because the rule
        is the document's and the wording is a widget's — and because a test
        that had to click a modal would pin neither.

        **On release, not per step.** `set_roi` fires per mouse-move, so a
        refusal hung there would put a dialog under a held button; this is the
        merged command's boundary, one drag and one question. Nothing is
        interrupted mid-gesture and the box follows the pointer throughout —
        the user sees the move they are being asked about.

        Declined, the box goes back and *no command is left on the stack*: the
        restore rides the gesture's own token, merges into the entry the drag
        built, and takes it with it (`SetReplicateROI.mergeWith`). The user
        should be unable to tell afterwards that they dragged, which one no-op
        undo entry would give away.

        Accepted, the replicate leaves the visitation set — it has not been
        opened in the filter tab *at this geometry*, so the lock re-arms the
        next time it is. Nothing else is done to make the old results go away:
        the ROI is hashed, so a moved box misses every entry keyed on the old
        one by construction, and `replicate_id` is deliberately not rotated —
        it is what the pins, the visitation set, and the undo history are all
        keyed on.
        """
        live, self._gesture = self._gesture, None
        if live is None or live.token != gesture or live.index != index:
            return
        replicate = self._replicates[index]
        if replicate.roi == live.roi or replicate.replicate_id not in self._visited:
            return
        if confirm(replicate):
            self._visited.discard(replicate.replicate_id)
            return
        self.set_roi(index, live.roi, gesture=gesture)
        self._gesture = None

    def mark_visited(self, index: int) -> None:
        """Record that the replicate at `index` has been opened for tuning.

        The lock's trigger, and it is *being looked at*, not *having pins*: an
        arena can be opened, watched, and used to confirm that the shared
        baseline works without ever deviating from it, and that is real work
        done against its geometry.

        Not an undoable command. Undo returns the user's edits, and looking at
        an arena is not one — a Ctrl+Z that un-looked at footage would be
        claiming to reverse something that happened to the user rather than to
        the document. The consequence at the other end is the reason to accept
        it: undoing an accepted move restores the tuned geometry with the lock
        still down, and the next look re-arms it.
        """
        if 0 <= index < len(self._replicates):
            self._visited.add(self._replicates[index].replicate_id)

    def is_visited(self, index: int) -> bool:
        """Whether the replicate at `index` has been opened for tuning."""
        return (
            0 <= index < len(self._replicates)
            and self._replicates[index].replicate_id in self._visited
        )

    def set_all_to_size(self, width: int, height: int) -> None:
        """Give every replicate this extent, each held about its own centre.

        Applying this only to the selected replicate is an easy mistake. The
        gesture serves a rack: a dozen arenas that are physically identical, cut by hand into a dozen
        boxes that are not quite. That difference is not cosmetic. Section **D**
        of the same document is the reason — the expected number of false
        positives scales with blocks times frames, so two boxes of different
        size run the *same* settings at different false-positive rates, and the
        difference between them arrives looking like a difference between
        colonies. Making the rack uniform is what lets one threshold mean one
        thing across it.

        The sizes come from the stamp fields rather than from the selected box,
        so the two numbers the button is about to apply are on screen beside it
        before it is pressed.

        One undo entry for however many rows it touched, and no entry at all
        when the rack is already uniform at this size — a button that stacks a
        no-op onto the history every time it is pressed teaches users not to
        press it.

        Every row, including the ones a materialized crop was cut at: see
        `set_roi` for why an artifact no longer holds a box still. A rack that
        squared up all but the arenas someone had already accelerated would be
        the one shape this gesture exists to rule out.
        """
        changed = {
            index: resized
            for index, replicate in enumerate(self._replicates.as_list())
            if (resized := replicate.roi.resized_in(width, height, self._source_size))
            != replicate.roi
        }
        if not changed:
            return
        self.undo_stack.push(SetReplicateROIs(self, changed, f"Set All to {width}x{height}"))

    def move_window_to(self, frame: int) -> None:
        """Move the working window so it starts at `frame`, holding its length.

        The in point, and the reason the window is an origin and a length rather
        than two marks. The user's gesture is "keep the ten seconds I chose, put
        them here"; two independent indices cannot express it, because an in
        point moved past the out point has to invent an out point and every
        answer to that question is a span nobody asked for. A window pushed off
        the end of the source rests against it at full length — see
        `timeline_model.moved_to`.
        """
        window = self.window
        if window is None:
            return
        self._push_clip(moved_to(window, frame, self._source_frames), "Move Window")

    def end_window_at(self, frame: int) -> None:
        """End the window after `frame`, inclusive of it. This is the resize.

        The user presses this on the frame they want *last*; `ClipRange` is
        half-open. That `+ 1` lives in `timeline_model.ended_at` rather than in
        the caller so that every front end marking an out point agrees on which
        frame the user meant.
        """
        if self._source_frames <= 0:
            return
        self._push_clip(ended_at(self.window, frame, self._source_frames), "Set Window End")

    def set_window_length(self, frames: int) -> None:
        """Give the window `frames` frames, keeping its origin where it is.

        The numeric field on the timeline row. Growing a window at the end of
        the source slides its origin back rather than refusing the number, for
        the same reason a move clamps rather than shortens: the length is what
        the user typed and the origin is what they did not.
        """
        window = self.window
        if window is None:
            return
        length = min(max(frames, 1), self._source_frames)
        origin = min(window.start, self._source_frames - length)
        self._push_clip(ClipRange(start=origin, end=origin + length), "Set Window Length")

    def place_window(self, start: int, end: int) -> None:
        """Put the window at exactly `[start, end)`. The bracket-handle drag.

        The only window edit that names both edges, because a handle drag is the
        only gesture that has already decided both — the strip resolved the
        cursor into a span before it let go, and re-deriving one edge from a
        length here would fight it. What is clamped here is only the structural
        invariant (inside the source, at least one frame); the one-second floor
        on a *drag* is the strip's, and deliberately not imposed on the keystroke
        marks, which are allowed to name a single frame.
        """
        if self._source_frames <= 0:
            return
        origin = min(max(start, 0), self._source_frames - 1)
        self._push_clip(
            ClipRange(start=origin, end=min(max(end, origin + 1), self._source_frames)),
            "Resize Window",
        )

    def bring_window_to(self, frame: int) -> None:
        """Move the window the least distance that puts `frame` inside it.

        What a click outside the window on the timeline means. A no-op when the
        frame is already inside, which is what makes a click *inside* the window
        a plain seek — the strip does not have to decide which gesture it was.
        """
        window = self.window
        if window is None:
            return
        self._push_clip(containing(window, frame, self._source_frames), "Move Window")

    def clear_clip(self) -> None:
        """Drop the user's choice, returning the window to the default.

        Not "no window": `window` above falls back, so the timeline always has
        one. What is cleared is the *claim* that this span was chosen, which is
        the thing the saved project carries.
        """
        self._push_clip(None, "Clear Clip")

    def _push_clip(self, clip: ClipRange | None, text: str) -> None:
        """Record a clip edit. Nothing refuses one.

        A materialized crop used to hold the window inside the span it was cut
        over, because a window reaching past either end un-backs the replicate
        (`pipeline/resolve_source.py` declines whole rather than half-serving).
        The answer to that is on the writing side, not here: the cut is taken
        over the whole source (`gui/filter_tab.py`'s materialize), so every
        window is inside it and there is nothing left to hold. A cut that
        predates that — or one hand-edited to a shorter span — simply stops
        backing its replicate when the window leaves it, and the card says so.
        """
        if clip == self._clip:
            return
        self.undo_stack.push(SetClip(self, clip, text))

    # ---- command-facing primitives ---------------------------------------
    # Called only by the commands in `commands.py`. Nothing else may mutate.

    def apply_insert(self, index: int, replicate: Replicate) -> None:
        """Insert without recording history. The inserted row is selected.

        Selecting it is what the tab did for the user's sake — the box just
        drawn is the one they are about to name or accept — and it holds for a
        redo for the same reason. Set before the emits so a view resyncing on
        `structure_changed` already sees the new answer.
        """
        self._replicates.insert(index, replicate)
        changed = self._selected != index
        self._selected = index
        self.structure_changed.emit()
        self.replicate_added.emit(index)
        if changed:
            self.selection_changed.emit()

    def apply_remove(self, index: int) -> Replicate:
        """Remove without recording history, keeping the selection on a real row.

        A removal above the selection shifts its row without changing which
        arena is selected, so nothing re-renders; removing the selected row
        itself falls to the nearest survivor, which is a genuinely different
        arena and says so.
        """
        removed = self._replicates.remove_at(index)
        changed = False
        if self._selected is not None:
            if self._selected == index:
                survivor = min(index, len(self._replicates) - 1)
                self._selected = survivor if survivor >= 0 else None
                changed = True
            elif self._selected > index:
                self._selected -= 1
        self.structure_changed.emit()
        if changed:
            self.selection_changed.emit()
        return removed

    def apply_replace(self, index: int, replicate: Replicate) -> Replicate:
        """Overwrite without recording history."""
        previous = self._replicates.replace_at(index, replicate)
        self.replicate_changed.emit(index)
        return previous

    def apply_clip(self, clip: ClipRange | None) -> None:
        """Replace the clip without recording history."""
        self._clip = clip
        self.clip_changed.emit()

    def apply_params(
        self, nodes: Mapping[str, Node], index: int | None, replicate: Replicate | None
    ) -> None:
        """Substitute node baselines, and one replicate's pins, without history.

        `index` and `replicate` arrive together or not at all: a document
        with no replicates tunes only baselines, and a command undoing a pin
        must restore the row it pinned on whatever is selected *now*.
        """
        substituted = tuple(nodes.get(node.node_id, node) for node in self._pipeline.nodes)
        self._pipeline = self._pipeline.model_copy(update={"nodes": substituted})
        if index is not None and replicate is not None:
            self._replicates.replace_at(index, replicate)
        self.tuning_changed.emit()
        self.grouping_changed.emit()

    def apply_detector(
        self,
        settings: DetectorSettings | None,
        index: int | None,
        replicate: Replicate | None,
    ) -> None:
        """Replace the detector baseline, and one replicate's pins, without history.

        `settings` may be None because an undo of the first-ever detector
        edit restores the never-tuned state, which is a real state a save
        must be able to write.
        """
        self._detector = settings
        if index is not None and replicate is not None:
            self._replicates.replace_at(index, replicate)
        self.detector_changed.emit()
        self.grouping_changed.emit()

    def apply_tuning_state(
        self,
        pipeline: Pipeline,
        detector: DetectorSettings | None,
        replicates: tuple[Replicate, ...],
    ) -> None:
        """Replace the whole tuning state without history — Reset and its undo.

        Wholesale because that is what the command captured; the replicate
        count never changes here, so no structural signal fires.
        """
        self._pipeline = pipeline
        self._detector = detector
        self._replicates = ReplicateSet(replicates)
        self.tuning_changed.emit()
        self.detector_changed.emit()
        self.grouping_changed.emit()

    def apply_state(self, state: DocumentState) -> None:
        """Replace everything the document owns, without recording history.

        `RestoreSnapshot`'s primitive, in both directions. Distinct from
        `load_project`, which clears the undo stack: a rollback is a *step* in
        the session's history rather than the start of a new one, so the stack
        has to survive it.

        Signals go out in `load_project`'s order and for its reasons, with one
        difference: the selection is held where the user left it when the row
        still exists, because a rollback that also moved which arena is on
        screen would make the safety net a navigation gesture.
        """
        self._replicates = ReplicateSet(state.replicates)
        self._pipeline = state.pipeline
        self._detector = state.detector
        self._clip = state.clip
        previous = self._selected
        if len(self._replicates) == 0:
            self._selected = None
        else:
            self._selected = min(previous or 0, len(self._replicates) - 1)
        self.structure_changed.emit()
        self.grouping_changed.emit()
        if self._selected != previous:
            self.selection_changed.emit()
        self.pipeline_changed.emit()
        self.tuning_changed.emit()
        self.detector_changed.emit()
        self.clip_changed.emit()

    def _fit(self, roi: ROI) -> ROI:
        """Trim an ROI to the source frame.

        Numeric edits in the table and boxes dragged past the frame edge both
        arrive here. Clamping rather than rejecting keeps a fat-fingered width
        from throwing away the rest of a valid edit.
        """
        if self._source_size is None:
            return roi
        width, height = self._source_size
        return roi.clamped_to(width, height)
