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
from typing import TYPE_CHECKING

from PySide6.QtGui import QUndoCommand

from sieve.core.pipeline_model import ClipRange
from sieve.core.replicates import Replicate
from sieve.core.types import ROI

if TYPE_CHECKING:
    from sieve.gui.document import ReplicateDocument


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
