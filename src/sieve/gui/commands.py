"""Undo commands over the replicate document.

Each command stores what it displaced rather than recomputing it on undo, so
an inverse is always exact even after other edits have moved rows around.
`QUndoStack.push` runs `redo` once immediately — the command is the only
place the edit is expressed, not a duplicate of an eager mutation.

The `text` of each command surfaces in the Edit menu ("Undo Add Replicate"),
which is the cheapest form of user-visible history there is.
"""

from __future__ import annotations

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


class SetReplicateROI(QUndoCommand):
    """Change a replicate's geometry."""

    def __init__(self, document: ReplicateDocument, index: int, roi: ROI) -> None:
        super().__init__(f"Resize {document.at(index).name}")
        self._document = document
        self._index = index
        self._roi = roi
        self._previous: Replicate | None = None

    def redo(self) -> None:
        """Apply the new geometry."""
        current = self._document.at(self._index)
        self._previous = current
        self._document.apply_replace(self._index, current.with_roi(self._roi))

    def undo(self) -> None:
        """Restore the previous geometry."""
        if self._previous is not None:
            self._document.apply_replace(self._index, self._previous)


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
