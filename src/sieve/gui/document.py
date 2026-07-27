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

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QUndoStack

from sieve.core.pipeline_model import ClipRange, Pipeline, Project, equivalence_groups
from sieve.core.replicates import Replicate, ReplicateSet
from sieve.core.types import ROI
from sieve.gui.commands import (
    AddReplicate,
    RemoveReplicate,
    RenameReplicate,
    SetClip,
    SetReplicateROI,
)
from sieve.gui.timeline_model import containing, effective_window, ended_at, fitted, moved_to


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
    #: A different replicate is the one being tuned — or none is. Not emitted
    #: when a removal above the selection merely shifts its row number: the
    #: arena on screen is the same arena, and a re-render of it would say
    #: nothing new. Views that track the *row* resync on `structure_changed`.
    selection_changed = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._replicates = ReplicateSet()
        self._pipeline = Pipeline()
        self._source_size: tuple[int, int] | None = None
        self._source_frames = 0
        self._source_fps = 0.0
        self._clip: ClipRange | None = None
        self._selected: int | None = None
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

    def equivalence_groups(self) -> tuple[int, ...]:
        """Group number per row, derived on every call.

        Delegates to `core`, and must keep doing so — the number a table paints
        and the number a report prints have to come from one definition, for the
        same reason `resolved_params` is the only answer to what a node runs
        with. An empty graph puts every replicate in group 1, which is the
        correct answer to "which of these run the same thing" when the answer is
        "nothing yet".
        """
        return equivalence_groups(self._pipeline, self._replicates.as_list())

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
        """Drop replicates, clip, graph, selection, and history silently."""
        self._replicates.clear()
        self._pipeline = Pipeline()
        self._clip = None
        self._selected = None
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
        self._clip = self._fit_clip(project.clip)
        # The first row, not none: a loaded project must open looking at *an*
        # arena, and with nothing remembered in the file the first is the only
        # unarbitrary one.
        self._selected = 0 if len(self._replicates) else None
        self.undo_stack.clear()
        self.structure_changed.emit()
        self.grouping_changed.emit()
        self.clip_changed.emit()
        self.selection_changed.emit()

    def apply_to(self, project: Project) -> Project:
        """`project` carrying this document's replicates, clip, and graph.

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
            .with_clip(self._clip)
            .with_pipeline(self._pipeline)
        )

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
        """
        if not 0 <= index < len(self._replicates) or index == self._selected:
            return
        self._selected = index
        self.selection_changed.emit()

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
        """
        fitted = self._fit(roi)
        if fitted == self._replicates[index].roi:
            return
        self.undo_stack.push(SetReplicateROI(self, index, fitted, gesture=gesture, text=text))

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
