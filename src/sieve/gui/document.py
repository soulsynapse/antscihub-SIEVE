"""The editable replicate document: a `ReplicateSet` plus its undo history.

Every mutation goes through a `QUndoCommand`, without exception. That is not
ceremony — it is the only way Ctrl+Z stays honest as edit paths multiply. A
single method that mutates the set directly is a silent hole in the history,
and holes in undo are discovered by users, not by tests.

The document is GUI-side because undo is GUI state: it never reaches the
pipeline artifact. The data it edits is `core`, and stays `core`.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QUndoStack

from sieve.core.pipeline_model import Pipeline, equivalence_groups
from sieve.core.replicates import Replicate, ReplicateSet
from sieve.core.types import ROI
from sieve.gui.commands import (
    AddReplicate,
    RemoveReplicate,
    RenameReplicate,
    SetReplicateROI,
)


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

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._replicates = ReplicateSet()
        self._pipeline = Pipeline()
        self._source_size: tuple[int, int] | None = None
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
    def source_size(self) -> tuple[int, int] | None:
        """Dimensions of the video these replicates were cut from."""
        return self._source_size

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

    def bind_source(self, width: int, height: int) -> None:
        """Attach to a new source video, discarding replicates and history.

        Replicates are geometry in one video's pixel space; carrying them
        across a file open would silently reinterpret them against different
        dimensions. Clearing is not undoable for the same reason — there is no
        coherent state to return to once the source is gone.

        The graph goes with them. It is not geometry and would survive the
        reinterpretation, but a replicate's deviation is keyed by node id, so
        keeping the graph while dropping every replicate leaves a set of
        defaults tuned against footage nobody is looking at any more.
        """
        self._source_size = (width, height)
        self._reset()
        self.structure_changed.emit()

    def unbind_source(self) -> None:
        """Detach from any source video."""
        self._source_size = None
        self._reset()
        self.structure_changed.emit()

    def _reset(self) -> None:
        """Drop replicates, graph, and history without announcing structure."""
        self._replicates.clear()
        self._pipeline = Pipeline()
        self.undo_stack.clear()

    # ---- user intents ----------------------------------------------------

    def add_roi(self, roi: ROI) -> None:
        """Append a replicate covering `roi`, named with the next free default."""
        replicate = Replicate(roi=self._fit(roi), name=self._replicates.next_default_name())
        self.undo_stack.push(AddReplicate(self, len(self._replicates), replicate))

    def remove(self, index: int) -> None:
        """Delete the replicate at `index`."""
        if not 0 <= index < len(self._replicates):
            return
        self.undo_stack.push(RemoveReplicate(self, index))

    def rename(self, index: int, name: str) -> None:
        """Give the replicate at `index` a new display name."""
        name = name.strip()
        if not name or name == self._replicates[index].name:
            return
        self.undo_stack.push(RenameReplicate(self, index, name))

    def set_roi(self, index: int, roi: ROI) -> None:
        """Give the replicate at `index` new geometry."""
        fitted = self._fit(roi)
        if fitted == self._replicates[index].roi:
            return
        self.undo_stack.push(SetReplicateROI(self, index, fitted))

    # ---- command-facing primitives ---------------------------------------
    # Called only by the commands in `commands.py`. Nothing else may mutate.

    def apply_insert(self, index: int, replicate: Replicate) -> None:
        """Insert without recording history."""
        self._replicates.insert(index, replicate)
        self.structure_changed.emit()
        self.replicate_added.emit(index)

    def apply_remove(self, index: int) -> Replicate:
        """Remove without recording history."""
        removed = self._replicates.remove_at(index)
        self.structure_changed.emit()
        return removed

    def apply_replace(self, index: int, replicate: Replicate) -> Replicate:
        """Overwrite without recording history."""
        previous = self._replicates.replace_at(index, replicate)
        self.replicate_changed.emit(index)
        return previous

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
