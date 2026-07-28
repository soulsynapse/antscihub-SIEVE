"""Undo commands over the replicate document.

Each command stores what it displaced rather than recomputing it on undo, so
an inverse is always exact even after other edits have moved rows around.
`QUndoStack.push` runs `redo` once immediately — the command is the only
place the edit is expressed, not a duplicate of an eager mutation.

The `text` of each command surfaces in the Edit menu ("Undo Add Replicate"),
which is the cheapest form of user-visible history there is.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import TYPE_CHECKING, Any

from PySide6.QtGui import QUndoCommand

from sieve.core.pipeline_model import (
    ClipRange,
    DetectorSettings,
    Node,
    Pipeline,
    edited_detector,
    edited_params,
)
from sieve.core.replicates import Replicate
from sieve.core.types import ROI

if TYPE_CHECKING:
    from sieve.gui.document import DocumentState, ReplicateDocument


class AddReplicate(QUndoCommand):
    """Insert a replicate at a known position."""

    def __init__(self, document: ReplicateDocument, index: int, replicate: Replicate) -> None:
        super().__init__(f"Add {replicate.name}")
        self._document = document
        self._index = index
        self._replicate = replicate

    def redo(self) -> None:
        """Insert the replicate."""
        self._document.apply_insert(self._index, self._replicate)

    def undo(self) -> None:
        """Remove the replicate again."""
        self._document.apply_remove(self._index)


class RemoveReplicate(QUndoCommand):
    """Delete a replicate, remembering it for undo."""

    def __init__(self, document: ReplicateDocument, index: int) -> None:
        super().__init__(f"Delete {document.at(index).name}")
        self._document = document
        self._index = index
        self._removed: Replicate | None = None

    def redo(self) -> None:
        """Remove the replicate, keeping it to restore."""
        self._removed = self._document.apply_remove(self._index)

    def undo(self) -> None:
        """Put the replicate back where it was."""
        if self._removed is not None:
            self._document.apply_insert(self._index, self._removed)


class RenameReplicate(QUndoCommand):
    """Change a replicate's display name."""

    def __init__(self, document: ReplicateDocument, index: int, name: str) -> None:
        super().__init__(f"Rename to {name}")
        self._document = document
        self._index = index
        self._name = name
        self._previous: Replicate | None = None

    def redo(self) -> None:
        """Apply the new name."""
        current = self._document.at(self._index)
        self._previous = current
        self._document.apply_replace(self._index, current.renamed(self._name))

    def undo(self) -> None:
        """Restore the previous name."""
        if self._previous is not None:
            self._document.apply_replace(self._index, self._previous)


#: Merge identity for geometry commands. Any non-negative constant works; what
#: matters is that it is *not* -1, which is Qt's "never merge".
ROI_MERGE_ID = 1


class SetReplicateROI(QUndoCommand):
    """Change a replicate's geometry, optionally as one step of a live drag.

    A drag across the video emits geometry continuously — that is what makes
    the box follow the cursor and the table's numbers count up under it — and
    without merging, a two-second drag would leave sixty entries on the undo
    stack and Ctrl+Z would crawl the box backwards a pixel at a time. So a
    command that carries a `gesture` token merges with the command below it
    when that command carries the *same* token: the surviving command keeps the
    geometry from before the drag began and takes on the geometry the drag has
    reached.

    The token is per press, not per drag *kind*, which is what stops two
    successive drags of the same box from collapsing into one. And it defaults
    to `None`, so a numeric edit in the table or the tools panel reports `id()`
    of -1 and never merges with anything — one typed number is one undo step,
    which is what a user typing numbers expects.
    """

    def __init__(
        self,
        document: ReplicateDocument,
        index: int,
        roi: ROI,
        *,
        gesture: int | None = None,
        text: str | None = None,
    ) -> None:
        super().__init__(text or f"Resize {document.at(index).name}")
        self._document = document
        self._index = index
        self._roi = roi
        self._gesture = gesture
        self._previous: Replicate | None = None

    def id(self) -> int:
        """Merge identity: shared while a gesture is live, never otherwise."""
        return ROI_MERGE_ID if self._gesture is not None else -1

    def mergeWith(self, other: QUndoCommand) -> bool:
        """Absorb a later step of the same gesture on the same replicate.

        `other` has already had its `redo` run by `QUndoStack.push` — Qt
        redoes first and merges second — so the document is current either
        way. All that is taken from it is the geometry to replay, while
        `_previous` stays what it was at the start of the gesture, which is
        what makes one Ctrl+Z return the box to where the drag began.
        """
        if not isinstance(other, SetReplicateROI):
            return False
        if self._gesture is None or other._gesture != self._gesture:
            return False
        if other._index != self._index:
            return False
        self._roi = other._roi
        return True

    def redo(self) -> None:
        """Apply the new geometry."""
        current = self._document.at(self._index)
        self._previous = current
        self._document.apply_replace(self._index, current.with_roi(self._roi))

    def undo(self) -> None:
        """Restore the previous geometry."""
        if self._previous is not None:
            self._document.apply_replace(self._index, self._previous)


class SetReplicateROIs(QUndoCommand):
    """Give several replicates new geometry as a single undo entry.

    `SetReplicateROI` above solves one shape of "many writes, one action" — a
    drag, which is many commands over one row collapsed by `mergeWith`. This is
    the other shape: one action over many rows. It is deliberately *not* that
    command in a loop, because merging cannot produce this. A merge is between
    adjacent commands carrying the same token and the same row, so a loop that
    pushed one command per replicate would leave one entry per replicate however
    the tokens were arranged, and Ctrl+Z would undo a twelve-arena rack one
    arena at a time.

    The displaced replicates are captured on `redo` rather than at construction,
    for `SetClip`'s reason: a redo after other edits has to displace what is
    there then, not what was there when the button was pressed.
    """

    def __init__(self, document: ReplicateDocument, rois: Mapping[int, ROI], text: str) -> None:
        super().__init__(text)
        self._document = document
        self._rois = dict(rois)
        self._previous: dict[int, Replicate] = {}

    def redo(self) -> None:
        """Apply every region, keeping what each one displaced."""
        self._previous = {}
        for index, roi in self._rois.items():
            current = self._document.at(index)
            self._previous[index] = current
            self._document.apply_replace(index, current.with_roi(roi))

    def undo(self) -> None:
        """Restore every replicate this displaced."""
        for index, replicate in self._previous.items():
            self._document.apply_replace(index, replicate)


class EditTuningParams(QUndoCommand):
    """Rewrite node baselines, pinning what changed on one replicate.

    `core.pipeline_model.edited_params` per node — the two writes are
    computed there, not here, so the GUI and the CLI cannot drift on what an
    edit means. `index` is the replicate being looked at when the knob moved,
    or None when the document holds no replicates, in which case only the
    baseline moves and there is nothing to pin on.

    One command may carry several nodes because one gesture may lawfully
    touch several — the downsample knob writes `rescale.scale` and
    `block_signal.scale` together — and two entries for one knob turn would
    make Ctrl+Z restore half an edit.
    """

    def __init__(
        self,
        document: ReplicateDocument,
        index: int | None,
        changes_by_node: Mapping[str, Mapping[str, Any]],
        text: str,
    ) -> None:
        super().__init__(text)
        self._document = document
        self._index = index
        self._changes = {node_id: dict(params) for node_id, params in changes_by_node.items()}
        self._displaced_nodes: dict[str, Node] = {}
        self._displaced_replicate: Replicate | None = None

    def redo(self) -> None:
        """Move the baselines and pin the diffs, keeping what both displaced."""
        replicate = None if self._index is None else self._document.at(self._index)
        self._displaced_replicate = replicate
        self._displaced_nodes = {}
        updated: dict[str, Node] = {}
        for node_id, params in self._changes.items():
            node = self._document.pipeline.node(node_id)
            self._displaced_nodes[node_id] = node
            if replicate is None:
                updated[node_id] = node.model_copy(update={"params": {**node.params, **params}})
            else:
                updated[node_id], replicate = edited_params(node, replicate, params)
        self._document.apply_params(updated, self._index, replicate)

    def undo(self) -> None:
        """Restore the displaced baselines and the displaced pins."""
        self._document.apply_params(self._displaced_nodes, self._index, self._displaced_replicate)


#: Merge identity for detector edits, `ROI_MERGE_ID`'s sibling. Distinct so a
#: geometry drag and a D drag can never be asked to merge with each other.
DETECTOR_MERGE_ID = 2


class EditDetector(QUndoCommand):
    """Move the detector baseline, pinning what changed on one replicate.

    `EditTuningParams`' twin over `edited_detector`, with `SetReplicateROI`'s
    gesture discipline: the D slider emits one value per detent crossed, and a
    drag across the dial would otherwise stack an undo entry per detent. A
    command carrying a `gesture` token merges with its predecessor carrying
    the same token, keeping the first command's displaced state and the last
    command's values — one drag, one entry, one Ctrl+Z back to where it began.
    """

    def __init__(
        self,
        document: ReplicateDocument,
        index: int | None,
        changes: Mapping[str, Any],
        text: str,
        *,
        gesture: int | None = None,
    ) -> None:
        super().__init__(text)
        self._document = document
        self._index = index
        self._changes = dict(changes)
        self._gesture = gesture
        self._displaced_settings: DetectorSettings | None = None
        self._displaced_replicate: Replicate | None = None

    def id(self) -> int:
        """Merge identity: shared while a gesture is live, never otherwise."""
        return DETECTOR_MERGE_ID if self._gesture is not None else -1

    def mergeWith(self, other: QUndoCommand) -> bool:
        """Absorb a later step of the same drag, keeping the first displaced state."""
        if not isinstance(other, EditDetector):
            return False
        if self._gesture is None or other._gesture != self._gesture:
            return False
        if other._index != self._index:
            return False
        self._changes = {**self._changes, **other._changes}
        return True

    def redo(self) -> None:
        """Move the baseline and pin the diff, keeping what both displaced."""
        settings = self._document.detector_baseline()
        replicate = None if self._index is None else self._document.at(self._index)
        self._displaced_settings = self._document.detector
        self._displaced_replicate = replicate
        if replicate is None:
            moved = DetectorSettings.model_validate({**settings.model_dump(), **self._changes})
        else:
            moved, replicate = edited_detector(settings, replicate, self._changes)
        self._document.apply_detector(moved, self._index, replicate)

    def undo(self) -> None:
        """Restore the displaced baseline — including its never-tuned None."""
        self._document.apply_detector(
            self._displaced_settings, self._index, self._displaced_replicate
        )


class ResetTuning(QUndoCommand):
    """Return every baseline to its defaults and drop every pin, everywhere.

    The filter tab's Reset is parameters-not-structure across the *document*:
    named nodes take their default parameters (nodes the user inserted are
    not named and keep their own — there is no default to reset them to), the
    detector baseline returns to never-tuned, and every replicate follows
    again. Whole-state capture rather than per-field inverses, because the
    inverse of "drop every pin on twelve replicates" is exactly the twelve
    replicates as they were.
    """

    def __init__(
        self, document: ReplicateDocument, defaults_by_node: Mapping[str, Mapping[str, Any]]
    ) -> None:
        super().__init__("Reset Tuning")
        self._document = document
        self._defaults = {node_id: dict(params) for node_id, params in defaults_by_node.items()}
        self._displaced: tuple[Pipeline, DetectorSettings | None, tuple[Replicate, ...]] | None = (
            None
        )

    def redo(self) -> None:
        """Apply the defaults, keeping the whole displaced tuning state."""
        document = self._document
        self._displaced = (document.pipeline, document.detector, tuple(document.all()))
        nodes = tuple(
            node.model_copy(update={"params": dict(self._defaults[node.node_id])})
            if node.node_id in self._defaults
            else node
            for node in document.pipeline.nodes
        )
        pipeline = document.pipeline.model_copy(update={"nodes": nodes})
        replicates = tuple(
            replace(replicate, overrides={}, detector_overrides={}) for replicate in document.all()
        )
        document.apply_tuning_state(pipeline, None, replicates)

    def undo(self) -> None:
        """Restore the tuning exactly as it was, pins and all."""
        if self._displaced is not None:
            document = self._document
            document.apply_tuning_state(*self._displaced)


class SetClip(QUndoCommand):
    """Move, place, or drop the representative clip.

    One command for all three because they are one edit to one field, and the
    caller already knows which of them it is — the text it passes is what the
    Edit menu reads back. Splitting it into `SetClipIn`/`SetClipOut`/`ClearClip`
    would be three classes whose `redo` bodies are the same assignment, and the
    in/out asymmetry the user sees lives in the document's mark rules, not here.

    The displaced range is captured on `redo` rather than at construction, for
    the same reason the replicate commands do it: a redo after other edits must
    displace what is there *then*, not what was there when the click happened.
    """

    def __init__(self, document: ReplicateDocument, clip: ClipRange | None, text: str) -> None:
        super().__init__(text)
        self._document = document
        self._clip = clip
        self._previous: ClipRange | None = None

    def redo(self) -> None:
        """Apply the new range."""
        self._previous = self._document.clip
        self._document.apply_clip(self._clip)

    def undo(self) -> None:
        """Restore the range this displaced, including no range at all."""
        self._document.apply_clip(self._previous)


class RestoreSnapshot(QUndoCommand):
    """Roll the whole document back to a state autosave wrote earlier.

    The one command that replaces everything at once, and the reason it is a
    command at all: rollback is the safety net that replaced the save prompt, so
    the net has to cover itself. A restore chosen by mistake is one Ctrl+Z, not
    a hunt through the history of histories.

    The displaced state is captured on `redo` for the reason every command here
    does it — a redo after other edits must displace what is there *then*. That
    also makes a chain of restores self-inverse: undoing the second returns to
    what the first left, not to where the session started.
    """

    def __init__(self, document: ReplicateDocument, state: DocumentState, text: str) -> None:
        super().__init__(text)
        self._document = document
        self._state = state
        self._previous: DocumentState | None = None

    def redo(self) -> None:
        """Put the snapshot's state into the document."""
        self._previous = self._document.capture()
        self._document.apply_state(self._state)

    def undo(self) -> None:
        """Return the document to whatever the restore displaced."""
        if self._previous is not None:
            self._document.apply_state(self._previous)
