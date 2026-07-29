from __future__ import annotations

import json
import math
import os
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any, Literal, Self
from uuid import uuid4

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from sieve.core.filter_base import (
    DEFAULT_PORT,
    FILTER_ID_PATTERN,
    PORT_PATTERN,
    SEMVER_PATTERN,
)
from sieve.core.replicates import Replicate
from sieve.core.types import ROI


SCHEMA_VERSION = 5


PROJECT_SUFFIX = ".sieve.yaml"


_SINK_FORMAT_PATTERN = FILTER_ID_PATTERN


def project_path_for(video: Path) -> Path:
    return video.parent / (video.stem + PROJECT_SUFFIX)


def _new_id() -> str:
    return uuid4().hex


def _resolved(path: Path) -> Path:
    return path.resolve()


def _posix_relative(target: Path, base: Path) -> str:
    resolved = _resolved(target)
    try:
        relative = os.path.relpath(resolved, _resolved(base))
    except ValueError:
        return PurePosixPath(resolved).as_posix()
    return PurePosixPath(relative.replace(os.sep, "/")).as_posix()


class _Artifact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", ser_json_inf_nan="constants")


class SourceRef(_Artifact):
    path: str

    @field_validator("path")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("source path must not be empty")
        return value

    @classmethod
    def relative_to(cls, video: Path, project_dir: Path) -> Self:
        return cls(path=_posix_relative(video, project_dir))

    def resolve(self, project_dir: Path) -> Path:
        return _resolved(Path(project_dir, self.path))


class ClipRange(_Artifact):
    start: int
    end: int

    @model_validator(mode="after")
    def _ordered_and_nonempty(self) -> Self:
        if self.start < 0:
            raise ValueError(f"clip start must be non-negative, got {self.start}")
        if self.end <= self.start:
            raise ValueError(
                f"clip must cover at least one frame, got [{self.start}, {self.end})"
            )
        return self

    @property
    def frame_count(self) -> int:
        return self.end - self.start


class DetectorSettings(_Artifact):
    freq_band: tuple[float, float] = (0.0, math.inf)

    value_band: tuple[float, float] = (-math.inf, math.inf)

    count_frac: tuple[float, float] | None = None

    window_frames: int = 30
    centered: bool = True

    @model_validator(mode="after")
    def _bands_ordered(self) -> Self:
        for name in ("freq_band", "value_band", "count_frac"):
            band: tuple[float, float] | None = getattr(self, name)
            if band is not None and band[0] > band[1]:
                raise ValueError(f"{name} must be ordered, got {band}")
        if self.freq_band[0] < 0:
            raise ValueError(f"freq_band must be non-negative, got {self.freq_band}")
        if self.window_frames < 1:
            raise ValueError(
                f"window_frames must be at least 1, got {self.window_frames}"
            )
        return self

    @classmethod
    def default_for(cls, fps: float) -> Self:
        return cls(window_frames=max(1, round(fps)) if fps > 0 else 30)


def resolved_detector(
    settings: DetectorSettings, replicate: Replicate | None = None
) -> DetectorSettings:
    if replicate is None or not replicate.detector_overrides:
        return settings
    return DetectorSettings.model_validate(
        {**settings.model_dump(), **replicate.detector_overrides}
    )


class Node(_Artifact):
    node_id: str = Field(default_factory=_new_id)
    filter_id: str
    version: str

    params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("filter_id")
    @classmethod
    def _known_shape_id(cls, value: str) -> str:
        if not FILTER_ID_PATTERN.match(value):
            raise ValueError(
                f"filter_id must match {FILTER_ID_PATTERN.pattern!r}, got {value!r}"
            )
        return value

    @field_validator("version")
    @classmethod
    def _known_shape_version(cls, value: str) -> str:
        if not SEMVER_PATTERN.match(value):
            raise ValueError(f"version must be MAJOR.MINOR.PATCH, got {value!r}")
        return value


def resolved_params(node: Node, replicate: Replicate | None = None) -> dict[str, Any]:
    if replicate is None:
        return dict(node.params)
    return {**node.params, **replicate.overrides.get(node.node_id, {})}


def edited_params(
    node: Node, replicate: Replicate, params: Mapping[str, Any]
) -> tuple[Node, Replicate]:
    before = resolved_params(node, replicate)
    changed = {
        name: value
        for name, value in params.items()
        if name not in before or before[name] != value
    }
    updated = node.model_copy(update={"params": {**node.params, **params}})
    return updated, replicate.with_override(node.node_id, changed)


def edited_detector(
    settings: DetectorSettings, replicate: Replicate, changes: Mapping[str, Any]
) -> tuple[DetectorSettings, Replicate]:
    moved = DetectorSettings.model_validate({**settings.model_dump(), **changes})
    before = resolved_detector(settings, replicate)
    changed = {
        name: value for name, value in changes.items() if getattr(before, name) != value
    }
    return moved, replicate.with_detector_pins(changed)


class Edge(_Artifact):
    upstream: str
    downstream: str
    port: str = DEFAULT_PORT

    @field_validator("port")
    @classmethod
    def _known_shape_port(cls, value: str) -> str:
        if not PORT_PATTERN.match(value):
            raise ValueError(f"port must match {PORT_PATTERN.pattern!r}, got {value!r}")
        return value

    @model_validator(mode="after")
    def _not_a_self_loop(self) -> Self:
        if self.upstream == self.downstream:
            raise ValueError(f"edge from {self.upstream} to itself")
        return self


class Sink(_Artifact):
    sink_id: str = Field(default_factory=_new_id)

    node_id: str

    format: str
    path: str

    params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("format")
    @classmethod
    def _known_shape_format(cls, value: str) -> str:
        if not _SINK_FORMAT_PATTERN.match(value):
            raise ValueError(
                f"sink format must match {_SINK_FORMAT_PATTERN.pattern!r}, got {value!r}"
            )
        return value

    @field_validator("path")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("sink path must not be empty")
        return value

    def resolve(self, project_dir: Path) -> Path:
        return _resolved(Path(project_dir, self.path))


CropFormat = Literal["luma", "bgr"]


class CropArtifact(_Artifact):
    path: str

    roi: ROI
    format: CropFormat

    span: ClipRange

    cut_from: str

    decoder: str

    @field_validator("path", "cut_from", "decoder")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("crop artifact fields must not be empty")
        return value

    @property
    def luma(self) -> bool:
        return self.format == "luma"

    def resolve(self, project_dir: Path) -> Path:
        return _resolved(Path(project_dir, self.path))

    def identity(self) -> tuple[str, ROI, CropFormat, ClipRange]:
        return (self.cut_from, self.roi, self.format, self.span)

    def backs(
        self, replicate: Replicate, *, source: str, luma: bool, project_dir: Path
    ) -> bool:
        return (
            self.cut_from == source
            and self.roi == replicate.roi
            and self.luma == luma
            and self.resolve(project_dir).is_file()
        )


class Pipeline(_Artifact):
    nodes: tuple[Node, ...] = ()
    edges: tuple[Edge, ...] = ()

    @model_validator(mode="after")
    def _referential_integrity(self) -> Self:
        seen: set[str] = set()
        for node in self.nodes:
            if node.node_id in seen:
                raise ValueError(f"duplicate node_id {node.node_id!r}")
            seen.add(node.node_id)
        for edge in self.edges:
            for endpoint in (edge.upstream, edge.downstream):
                if endpoint not in seen:
                    raise ValueError(f"edge names no such node: {endpoint!r}")
        fed: set[tuple[str, str]] = set()
        for edge in self.edges:
            target = (edge.downstream, edge.port)
            if target in fed:
                raise ValueError(
                    f"two edges feed {edge.downstream!r} on port {edge.port!r}"
                )
            fed.add(target)
        return self

    def __contains__(self, node_id: str) -> bool:
        return any(node.node_id == node_id for node in self.nodes)

    def node(self, node_id: str) -> Node:
        for candidate in self.nodes:
            if candidate.node_id == node_id:
                return candidate
        raise KeyError(node_id)


def _params_fingerprint(
    nodes: Sequence[Node],
    replicate: Replicate | None,
    detector: DetectorSettings | None,
) -> str:
    resolved = resolved_detector(detector or DetectorSettings(), replicate)
    return json.dumps(
        [
            [[node.node_id, resolved_params(node, replicate)] for node in nodes],
            resolved.model_dump(),
        ],
        sort_keys=True,
        separators=(",", ":"),
    )


def equivalence_groups(
    pipeline: Pipeline,
    replicates: Sequence[Replicate],
    detector: DetectorSettings | None = None,
) -> tuple[int, ...]:
    groups: dict[str, int] = {}
    numbers: list[int] = []
    for replicate in replicates:
        fingerprint = _params_fingerprint(pipeline.nodes, replicate, detector)
        numbers.append(groups.setdefault(fingerprint, len(groups) + 1))
    return tuple(numbers)


class Project(_Artifact):
    schema_version: int = SCHEMA_VERSION
    source: SourceRef

    replicates: tuple[Replicate, ...] = ()

    clip: ClipRange | None = None
    pipeline: Pipeline = Pipeline()

    detector: DetectorSettings | None = None

    checkpoints: tuple[str, ...] = ()
    outputs: tuple[Sink, ...] = ()

    crops: tuple[CropArtifact, ...] = ()

    visited: tuple[str, ...] = ()

    @field_validator("schema_version")
    @classmethod
    def _readable(cls, value: int) -> int:
        if value > SCHEMA_VERSION:
            raise ValueError(
                f"project uses schema version {value}; this build reads up to {SCHEMA_VERSION}"
            )
        return SCHEMA_VERSION

    @model_validator(mode="after")
    def _references_resolve(self) -> Self:
        ids = [replicate.replicate_id for replicate in self.replicates]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate replicate_id")
        for replicate in self.replicates:
            for node_id in replicate.overrides:
                if node_id not in self.pipeline:
                    raise ValueError(
                        f"replicate {replicate.replicate_id!r} overrides no such node: {node_id!r}"
                    )
            for field_name in replicate.detector_overrides:
                if field_name not in DetectorSettings.model_fields:
                    raise ValueError(
                        f"replicate {replicate.replicate_id!r} pins no such detector "
                        f"field: {field_name!r}"
                    )
            try:
                resolved_detector(self.detector or DetectorSettings(), replicate)
            except ValidationError as error:
                raise ValueError(
                    f"replicate {replicate.replicate_id!r} pins a detector value that "
                    f"does not fit its field: {error}"
                ) from error
        for node_id in self.checkpoints:
            if node_id not in self.pipeline:
                raise ValueError(f"checkpoint names no such node: {node_id!r}")
        if len(set(self.checkpoints)) != len(self.checkpoints):
            raise ValueError("duplicate checkpoint")
        sink_ids = [sink.sink_id for sink in self.outputs]
        if len(set(sink_ids)) != len(sink_ids):
            raise ValueError("duplicate sink_id")
        for sink in self.outputs:
            if sink.node_id not in self.pipeline:
                raise ValueError(f"sink names no such node: {sink.node_id!r}")
        cuts = [artifact.identity() for artifact in self.crops]
        if len(set(cuts)) != len(cuts):
            raise ValueError("two crop artifacts record the same cut")
        known = set(ids)
        for replicate_id in self.visited:
            if replicate_id not in known:
                raise ValueError(f"visited names no such replicate: {replicate_id!r}")
        if len(set(self.visited)) != len(self.visited):
            raise ValueError("duplicate visited replicate")
        return self

    def to_yaml(self) -> str:
        return yaml.safe_dump(
            self.model_dump(mode="json"),
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
        )

    @classmethod
    def from_yaml(cls, text: str) -> Self:
        return cls.model_validate(yaml.safe_load(text))

    def save(self, path: Path) -> None:
        path.write_text(self.to_yaml(), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Self:
        return cls.from_yaml(path.read_text(encoding="utf-8"))

    @classmethod
    def for_video(cls, video: Path, project_dir: Path | None = None) -> Self:
        directory = project_dir if project_dir is not None else video.parent
        return cls(source=SourceRef.relative_to(video, directory))

    def relocated(self, from_dir: Path, to_dir: Path) -> Self:
        def rebase(sink: Sink) -> Sink:
            return sink.model_copy(
                update={"path": _posix_relative(sink.resolve(from_dir), to_dir)}
            )
        def rebase_crop(artifact: CropArtifact) -> CropArtifact:
            return artifact.model_copy(
                update={"path": _posix_relative(artifact.resolve(from_dir), to_dir)}
            )
        return self.model_copy(
            update={
                "source": SourceRef.relative_to(self.source.resolve(from_dir), to_dir),
                "outputs": tuple(rebase(sink) for sink in self.outputs),
                "crops": tuple(rebase_crop(artifact) for artifact in self.crops),
            }
        )

    def source_path(self, project_path: Path) -> Path:
        return self.source.resolve(project_path.parent)

    def with_replicates(self, replicates: tuple[Replicate, ...]) -> Self:
        return self.model_copy(update={"replicates": replicates})

    def with_pipeline(self, pipeline: Pipeline) -> Self:
        return self.model_validate(self.model_copy(update={"pipeline": pipeline}))

    def with_clip(self, clip: ClipRange | None) -> Self:
        return self.model_copy(update={"clip": clip})

    def with_crop(self, artifact: CropArtifact) -> Self:
        existing = [candidate.identity() for candidate in self.crops]
        if artifact.identity() in existing:
            index = existing.index(artifact.identity())
            crops = (*self.crops[:index], artifact, *self.crops[index + 1 :])
        else:
            crops = (*self.crops, artifact)
        return self.model_copy(update={"crops": crops})

    def with_crops(self, crops: Iterable[CropArtifact]) -> Self:
        return self.model_validate(self.model_copy(update={"crops": tuple(crops)}))

    def without_crop(self, artifact: CropArtifact) -> Self:
        wanted = artifact.identity()
        return self.model_copy(
            update={
                "crops": tuple(
                    candidate
                    for candidate in self.crops
                    if candidate.identity() != wanted
                )
            }
        )

    def with_visited(self, visited: Iterable[str]) -> Self:
        wanted = set(visited)
        kept = tuple(
            replicate.replicate_id
            for replicate in self.replicates
            if replicate.replicate_id in wanted
        )
        return self.model_copy(update={"visited": kept})

    def replicate(self, replicate_id: str) -> Replicate:
        for candidate in self.replicates:
            if candidate.replicate_id == replicate_id:
                return candidate
        raise KeyError(replicate_id)

    def params_for(
        self, node_id: str, replicate_id: str | None = None
    ) -> dict[str, Any]:
        node = self.pipeline.node(node_id)
        return resolved_params(
            node, None if replicate_id is None else self.replicate(replicate_id)
        )

    def equivalence_groups(self) -> tuple[int, ...]:
        return equivalence_groups(self.pipeline, self.replicates, self.detector)

    def with_param_edit(
        self, node_id: str, replicate_id: str, params: Mapping[str, Any]
    ) -> Self:
        node = self.pipeline.node(node_id)
        target = self.replicate(replicate_id)
        updated_node, edited = edited_params(node, target, params)
        return self._replacing(node, updated_node, target, edited)

    def with_param_reset(self, node_id: str, replicate_id: str) -> Self:
        node = self.pipeline.node(node_id)
        target = self.replicate(replicate_id)
        return self._replacing(node, node, target, target.without_override(node_id))

    def with_detector(self, detector: DetectorSettings | None) -> Self:
        return self.model_copy(update={"detector": detector})

    def with_detector_edit(self, replicate_id: str, changes: Mapping[str, Any]) -> Self:
        target = self.replicate(replicate_id)
        moved, edited = edited_detector(
            self.detector or DetectorSettings(), target, changes
        )
        replicates = tuple(edited if r is target else r for r in self.replicates)
        return self.model_copy(update={"detector": moved, "replicates": replicates})

    def _replacing(
        self, node: Node, new_node: Node, replicate: Replicate, new_replicate: Replicate
    ) -> Self:
        return self.model_copy(
            update={
                "pipeline": self.pipeline.model_copy(
                    update={
                        "nodes": tuple(
                            new_node if candidate is node else candidate
                            for candidate in self.pipeline.nodes
                        )
                    }
                ),
                "replicates": tuple(
                    new_replicate if candidate is replicate else candidate
                    for candidate in self.replicates
                ),
            }
        )
