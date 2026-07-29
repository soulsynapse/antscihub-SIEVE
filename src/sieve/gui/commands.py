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
    def __init__(
        self, document: ReplicateDocument, index: int, replicate: Replicate
    ) -> None:
        super().__init__(f"Add {replicate.name}")
        self._document = document
        self._index = index
        self._replicate = replicate

    def redo(self) -> None:
        self._document.apply_insert(self._index, self._replicate)

    def undo(self) -> None:
        self._document.apply_remove(self._index)


class RemoveReplicate(QUndoCommand):
    def __init__(self, document: ReplicateDocument, index: int) -> None:
        super().__init__(f"Delete {document.at(index).name}")
        self._document = document
        self._index = index
        self._removed: Replicate | None = None

    def redo(self) -> None:
        self._removed = self._document.apply_remove(self._index)

    def undo(self) -> None:
        if self._removed is not None:
            self._document.apply_insert(self._index, self._removed)


class RenameReplicate(QUndoCommand):
    def __init__(self, document: ReplicateDocument, index: int, name: str) -> None:
        super().__init__(f"Rename to {name}")
        self._document = document
        self._index = index
        self._name = name
        self._previous: Replicate | None = None

    def redo(self) -> None:
        current = self._document.at(self._index)
        self._previous = current
        self._document.apply_replace(self._index, current.renamed(self._name))

    def undo(self) -> None:
        if self._previous is not None:
            self._document.apply_replace(self._index, self._previous)


ROI_MERGE_ID = 1


class SetReplicateROI(QUndoCommand):
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
        return ROI_MERGE_ID if self._gesture is not None else -1

    def mergeWith(self, other: QUndoCommand) -> bool:
        if not isinstance(other, SetReplicateROI):
            return False
        if self._gesture is None or other._gesture != self._gesture:
            return False
        if other._index != self._index:
            return False
        self._roi = other._roi
        if self._previous is not None and self._roi == self._previous.roi:
            self.setObsolete(True)
        return True

    def redo(self) -> None:
        current = self._document.at(self._index)
        self._previous = current
        self._document.apply_replace(self._index, current.with_roi(self._roi))

    def undo(self) -> None:
        if self._previous is not None:
            self._document.apply_replace(self._index, self._previous)


class SetReplicateROIs(QUndoCommand):
    def __init__(
        self, document: ReplicateDocument, rois: Mapping[int, ROI], text: str
    ) -> None:
        super().__init__(text)
        self._document = document
        self._rois = dict(rois)
        self._previous: dict[int, Replicate] = {}

    def redo(self) -> None:
        self._previous = {}
        for index, roi in self._rois.items():
            current = self._document.at(index)
            self._previous[index] = current
            self._document.apply_replace(index, current.with_roi(roi))

    def undo(self) -> None:
        for index, replicate in self._previous.items():
            self._document.apply_replace(index, replicate)


class EditTuningParams(QUndoCommand):
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
        self._changes = {
            node_id: dict(params) for node_id, params in changes_by_node.items()
        }
        self._displaced_nodes: dict[str, Node] = {}
        self._displaced_replicate: Replicate | None = None

    def redo(self) -> None:
        replicate = None if self._index is None else self._document.at(self._index)
        self._displaced_replicate = replicate
        self._displaced_nodes = {}
        updated: dict[str, Node] = {}
        for node_id, params in self._changes.items():
            node = self._document.pipeline.node(node_id)
            self._displaced_nodes[node_id] = node
            if replicate is None:
                updated[node_id] = node.model_copy(
                    update={"params": {**node.params, **params}}
                )
            else:
                updated[node_id], replicate = edited_params(node, replicate, params)
        self._document.apply_params(updated, self._index, replicate)

    def undo(self) -> None:
        self._document.apply_params(
            self._displaced_nodes, self._index, self._displaced_replicate
        )


DETECTOR_MERGE_ID = 2


class EditDetector(QUndoCommand):
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
        return DETECTOR_MERGE_ID if self._gesture is not None else -1

    def mergeWith(self, other: QUndoCommand) -> bool:
        if not isinstance(other, EditDetector):
            return False
        if self._gesture is None or other._gesture != self._gesture:
            return False
        if other._index != self._index:
            return False
        self._changes = {**self._changes, **other._changes}
        return True

    def redo(self) -> None:
        settings = self._document.detector_baseline()
        replicate = None if self._index is None else self._document.at(self._index)
        self._displaced_settings = self._document.detector
        self._displaced_replicate = replicate
        if replicate is None:
            moved = DetectorSettings.model_validate(
                {**settings.model_dump(), **self._changes}
            )
        else:
            moved, replicate = edited_detector(settings, replicate, self._changes)
        self._document.apply_detector(moved, self._index, replicate)

    def undo(self) -> None:
        self._document.apply_detector(
            self._displaced_settings, self._index, self._displaced_replicate
        )


class ResetTuning(QUndoCommand):
    def __init__(
        self,
        document: ReplicateDocument,
        defaults_by_node: Mapping[str, Mapping[str, Any]],
    ) -> None:
        super().__init__("Reset Tuning")
        self._document = document
        self._defaults = {
            node_id: dict(params) for node_id, params in defaults_by_node.items()
        }
        self._displaced: (
            tuple[Pipeline, DetectorSettings | None, tuple[Replicate, ...]] | None
        ) = None

    def redo(self) -> None:
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
            replace(replicate, overrides={}, detector_overrides={})
            for replicate in document.all()
        )
        document.apply_tuning_state(pipeline, None, replicates)

    def undo(self) -> None:
        if self._displaced is not None:
            document = self._document
            document.apply_tuning_state(*self._displaced)


class SetClip(QUndoCommand):
    def __init__(
        self, document: ReplicateDocument, clip: ClipRange | None, text: str
    ) -> None:
        super().__init__(text)
        self._document = document
        self._clip = clip
        self._previous: ClipRange | None = None

    def redo(self) -> None:
        self._previous = self._document.clip
        self._document.apply_clip(self._clip)

    def undo(self) -> None:
        self._document.apply_clip(self._previous)


class RestoreSnapshot(QUndoCommand):
    def __init__(
        self, document: ReplicateDocument, state: DocumentState, text: str
    ) -> None:
        super().__init__(text)
        self._document = document
        self._state = state
        self._previous: DocumentState | None = None

    def redo(self) -> None:
        self._previous = self._document.capture()
        self._document.apply_state(self._state)

    def undo(self) -> None:
        if self._previous is not None:
            self._document.apply_state(self._previous)
