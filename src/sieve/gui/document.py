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
from sieve.gui.timeline_model import (
    containing,
    effective_window,
    ended_at,
    fitted,
    moved_to,
)
from sieve.pipeline.dag import graph_needs_chroma


@dataclass(frozen=True)
class DocumentState:
    replicates: tuple[Replicate, ...]
    pipeline: Pipeline
    detector: DetectorSettings | None
    clip: ClipRange | None


@dataclass(frozen=True)
class SourceHome:
    video: Path
    project_dir: Path
    identity: str


@dataclass(frozen=True)
class _Gesture:
    token: int
    index: int
    roi: ROI


class ReplicateDocument(QObject):
    structure_changed = Signal()

    replicate_changed = Signal(int)

    replicate_added = Signal(int)

    grouping_changed = Signal()

    clip_changed = Signal()

    source_changed = Signal()

    tuning_changed = Signal()

    detector_changed = Signal()

    pipeline_changed = Signal()

    crops_changed = Signal()

    edit_refused = Signal(str)

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
        self._visited: set[str] = set()
        self._crops: tuple[CropArtifact, ...] = ()
        self._home: SourceHome | None = None
        self._gesture: _Gesture | None = None
        self.undo_stack = QUndoStack(self)

    def __len__(self) -> int:
        return len(self._replicates)

    def at(self, index: int) -> Replicate:
        return self._replicates[index]

    def all(self) -> list[Replicate]:
        return self._replicates.as_list()

    @property
    def selected_index(self) -> int | None:
        return self._selected

    @property
    def selected_replicate(self) -> Replicate | None:
        return None if self._selected is None else self._replicates[self._selected]

    @property
    def source_size(self) -> tuple[int, int] | None:
        return self._source_size

    @property
    def source_frames(self) -> int:
        return self._source_frames

    @property
    def source_fps(self) -> float:
        return self._source_fps

    @property
    def window(self) -> ClipRange | None:
        return effective_window(self._clip, self._source_frames, self._source_fps)

    @property
    def clip(self) -> ClipRange | None:
        return self._clip

    @property
    def pipeline(self) -> Pipeline:
        return self._pipeline

    @property
    def detector(self) -> DetectorSettings | None:
        return self._detector

    def detector_baseline(self) -> DetectorSettings:
        return self._detector or DetectorSettings.default_for(self._source_fps)

    def resolved_node_params(self, node_id: str) -> dict[str, Any]:
        return resolved_params(self._pipeline.node(node_id), self.selected_replicate)

    def resolved_detector_for_selection(self) -> DetectorSettings:
        return resolved_detector(self.detector_baseline(), self.selected_replicate)

    def equivalence_groups(self) -> tuple[int, ...]:
        return equivalence_groups(
            self._pipeline, self._replicates.as_list(), self._detector
        )

    @property
    def crops(self) -> tuple[CropArtifact, ...]:
        return self._crops

    @property
    def source_home(self) -> SourceHome | None:
        return self._home

    def set_source_home(self, home: SourceHome | None) -> None:
        self._home = home

    def set_crops(self, crops: Iterable[CropArtifact]) -> None:
        records = tuple(crops)
        if records == self._crops:
            return
        self._crops = records
        self.crops_changed.emit()

    def register_crop(self, artifact: CropArtifact) -> None:
        self.set_crops(self._as_project().with_crop(artifact).crops)

    def discard_crop(self, artifact: CropArtifact) -> None:
        self.set_crops(self._as_project().without_crop(artifact).crops)

    def _as_project(self) -> Project:
        return Project.for_video(Path("scratch.mp4"), Path()).with_crops(self._crops)

    def crop_backing(self, index: int) -> CropBacking:
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
        return not graph_needs_chroma(self._pipeline)

    def set_pipeline(self, pipeline: Pipeline) -> None:
        if pipeline == self._pipeline:
            return
        self._pipeline = pipeline
        self.grouping_changed.emit()

    def sync_structure(self, pipeline: Pipeline) -> None:
        nodes = tuple(
            self._pipeline.node(node.node_id)
            if node.node_id in self._pipeline
            else node
            for node in pipeline.nodes
        )
        merged = pipeline.model_copy(update={"nodes": nodes})
        surviving = {node.node_id for node in nodes}
        pruned = ReplicateSet(
            replicate.with_overrides_limited_to(surviving)
            for replicate in self._replicates
        )
        if merged == self._pipeline and pruned.as_list() == self._replicates.as_list():
            return
        self._pipeline = merged
        self._replicates = pruned
        self.pipeline_changed.emit()
        self.grouping_changed.emit()

    def bind_source(
        self, width: int, height: int, frame_count: int = 0, fps: float = 0.0
    ) -> None:
        self._source_size = (width, height)
        self._source_frames = max(frame_count, 0)
        self._source_fps = max(fps, 0.0)
        self._reset()
        self.source_changed.emit()
        self.structure_changed.emit()
        self.clip_changed.emit()

    def unbind_source(self) -> None:
        self._source_size = None
        self._source_frames = 0
        self._source_fps = 0.0
        self._reset()
        self.source_changed.emit()
        self.structure_changed.emit()
        self.clip_changed.emit()

    def _reset(self) -> None:
        self._replicates.clear()
        self._pipeline = Pipeline()
        self._detector = None
        self._clip = None
        self._selected = None
        self._visited.clear()
        self._crops = ()
        self._gesture = None
        self.undo_stack.clear()

    def load_project(self, project: Project) -> None:
        self._replicates = ReplicateSet(
            replicate.with_roi(self._fit(replicate.roi))
            for replicate in project.replicates
        )
        self._pipeline = project.pipeline
        self._detector = project.detector
        self._clip = self._fit_clip(project.clip)
        self._visited = set(project.visited)
        self._crops = project.crops
        self._selected = 0 if len(self._replicates) else None
        self.undo_stack.clear()
        self.structure_changed.emit()
        self.grouping_changed.emit()
        self.selection_changed.emit()
        self.pipeline_changed.emit()
        self.detector_changed.emit()
        self.clip_changed.emit()

    def apply_to(self, project: Project) -> Project:
        return (
            project.with_replicates(tuple(self._replicates))
            .with_visited(self._visited)
            .with_clip(self._clip)
            .with_detector(self._detector)
            .with_pipeline(self._pipeline)
            .with_crops(self._crops)
        )

    def capture(self) -> DocumentState:
        return DocumentState(
            replicates=tuple(self._replicates),
            pipeline=self._pipeline,
            detector=self._detector,
            clip=self._clip,
        )

    def state_from_project(self, project: Project) -> DocumentState:
        return DocumentState(
            replicates=tuple(
                replicate.with_roi(self._fit(replicate.roi))
                for replicate in project.replicates
            ),
            pipeline=project.pipeline,
            detector=project.detector,
            clip=self._fit_clip(project.clip),
        )

    def restore(self, state: DocumentState, text: str) -> None:
        if state == self.capture():
            return
        self.undo_stack.push(RestoreSnapshot(self, state, text))

    def _fit_clip(self, clip: ClipRange | None) -> ClipRange | None:
        return fitted(clip, self._source_frames)

    def select(self, index: int) -> None:
        if not 0 <= index < len(self._replicates) or index == self._selected:
            return
        self._selected = index
        self.selection_changed.emit()

    def edit_params(
        self, changes_by_node: Mapping[str, Mapping[str, Any]], text: str
    ) -> None:
        if not self._would_change(changes_by_node):
            return
        self.undo_stack.push(
            EditTuningParams(self, self._selected, changes_by_node, text)
        )

    def _would_change(self, changes_by_node: Mapping[str, Mapping[str, Any]]) -> bool:
        replicate = self.selected_replicate
        for node_id, params in changes_by_node.items():
            node = self._pipeline.node(node_id)
            if replicate is None:
                if {**node.params, **params} != node.params:
                    return True
            else:
                moved, pinned = edited_params(node, replicate, params)
                if (
                    moved.params != node.params
                    or pinned.overrides != replicate.overrides
                ):
                    return True
        return False

    def edit_detector(
        self, changes: Mapping[str, Any], text: str, *, gesture: int | None = None
    ) -> None:
        baseline = self.detector_baseline()
        replicate = self.selected_replicate
        if replicate is None:
            moved = DetectorSettings.model_validate(
                {**baseline.model_dump(), **changes}
            )
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
        self.undo_stack.push(
            EditDetector(self, self._selected, changes, text, gesture=gesture)
        )

    def reset_tuning(self, defaults_by_node: Mapping[str, Mapping[str, Any]]) -> None:
        self.undo_stack.push(ResetTuning(self, defaults_by_node))

    def add_roi(self, roi: ROI) -> None:
        replicate = Replicate(
            roi=self._fit(roi), name=self._replicates.next_default_name()
        )
        self.undo_stack.push(AddReplicate(self, len(self._replicates), replicate))

    def remove(self, index: int) -> None:
        if not 0 <= index < len(self._replicates):
            return
        self.undo_stack.push(RemoveReplicate(self, index))

    def rename(self, index: int, name: str) -> bool:
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
        if gesture is not None and (
            self._gesture is None or self._gesture.token != gesture
        ):
            self._gesture = _Gesture(
                token=gesture, index=index, roi=self._replicates[index].roi
            )
        fitted = self._fit(roi)
        if fitted == self._replicates[index].roi:
            return
        self.undo_stack.push(
            SetReplicateROI(self, index, fitted, gesture=gesture, text=text)
        )

    def finish_roi_gesture(
        self,
        index: int,
        gesture: int,
        confirm: Callable[[Replicate], bool],
    ) -> None:
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
        if 0 <= index < len(self._replicates):
            self._visited.add(self._replicates[index].replicate_id)

    def is_visited(self, index: int) -> bool:
        return (
            0 <= index < len(self._replicates)
            and self._replicates[index].replicate_id in self._visited
        )

    def set_all_to_size(self, width: int, height: int) -> None:
        changed = {
            index: resized
            for index, replicate in enumerate(self._replicates.as_list())
            if (resized := replicate.roi.resized_in(width, height, self._source_size))
            != replicate.roi
        }
        if not changed:
            return
        self.undo_stack.push(
            SetReplicateROIs(self, changed, f"Set All to {width}x{height}")
        )

    def move_window_to(self, frame: int) -> None:
        window = self.window
        if window is None:
            return
        self._push_clip(moved_to(window, frame, self._source_frames), "Move Window")

    def end_window_at(self, frame: int) -> None:
        if self._source_frames <= 0:
            return
        self._push_clip(
            ended_at(self.window, frame, self._source_frames), "Set Window End"
        )

    def set_window_length(self, frames: int) -> None:
        window = self.window
        if window is None:
            return
        length = min(max(frames, 1), self._source_frames)
        origin = min(window.start, self._source_frames - length)
        self._push_clip(
            ClipRange(start=origin, end=origin + length), "Set Window Length"
        )

    def place_window(self, start: int, end: int) -> None:
        if self._source_frames <= 0:
            return
        origin = min(max(start, 0), self._source_frames - 1)
        self._push_clip(
            ClipRange(start=origin, end=min(max(end, origin + 1), self._source_frames)),
            "Resize Window",
        )

    def bring_window_to(self, frame: int) -> None:
        window = self.window
        if window is None:
            return
        self._push_clip(containing(window, frame, self._source_frames), "Move Window")

    def clear_clip(self) -> None:
        self._push_clip(None, "Clear Clip")

    def _push_clip(self, clip: ClipRange | None, text: str) -> None:
        if clip == self._clip:
            return
        self.undo_stack.push(SetClip(self, clip, text))

    def apply_insert(self, index: int, replicate: Replicate) -> None:
        self._replicates.insert(index, replicate)
        changed = self._selected != index
        self._selected = index
        self.structure_changed.emit()
        self.replicate_added.emit(index)
        if changed:
            self.selection_changed.emit()

    def apply_remove(self, index: int) -> Replicate:
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
        previous = self._replicates.replace_at(index, replicate)
        self.replicate_changed.emit(index)
        return previous

    def apply_clip(self, clip: ClipRange | None) -> None:
        self._clip = clip
        self.clip_changed.emit()

    def apply_params(
        self, nodes: Mapping[str, Node], index: int | None, replicate: Replicate | None
    ) -> None:
        substituted = tuple(
            nodes.get(node.node_id, node) for node in self._pipeline.nodes
        )
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
        self._pipeline = pipeline
        self._detector = detector
        self._replicates = ReplicateSet(replicates)
        self.tuning_changed.emit()
        self.detector_changed.emit()
        self.grouping_changed.emit()

    def apply_state(self, state: DocumentState) -> None:
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
        if self._source_size is None:
            return roi
        width, height = self._source_size
        return roi.clamped_to(width, height)
