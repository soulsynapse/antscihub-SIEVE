from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from sieve.core.pipeline_model import ClipRange, CropArtifact
from sieve.core.replicates import Replicate
from sieve.core.types import Frame
from sieve.decode.reader import VideoDecodeError
from sieve.pipeline.cache_key import source_identity
from sieve.pipeline.executor import FrameSource


@dataclass(frozen=True, slots=True)
class ResolvedSource:
    path: Path

    identity: str

    pre_cropped: bool

    first_index: int

    artifact: CropArtifact | None = None

    def wrap(self, reader: FrameSource) -> FrameSource:
        if self.first_index == 0:
            return reader
        return OffsetFrameSource(reader, self.first_index)


class OffsetFrameSource:
    def __init__(self, inner: FrameSource, first: int) -> None:
        self._inner = inner
        self._first = first

    def read(self, index: int) -> Frame:
        if index < self._first:
            raise VideoDecodeError(
                f"frame {index} is before this footage begins (frame {self._first})"
            )
        frame = self._inner.read(index - self._first)
        return Frame(data=frame.data, index=index, channels=frame.channels)


def resolve(
    crops: Sequence[CropArtifact],
    replicate: Replicate | None,
    *,
    project_dir: Path,
    parent: Path,
    parent_identity: str,
    luma: bool,
    want: ClipRange,
) -> ResolvedSource:
    if replicate is None:
        return ResolvedSource(
            path=parent, identity=parent_identity, pre_cropped=False, first_index=0
        )
    for artifact in crops:
        if not artifact.backs(
            replicate, source=parent_identity, luma=luma, project_dir=project_dir
        ):
            continue
        if artifact.span.start > want.start or artifact.span.end < want.end:
            continue
        path = artifact.resolve(project_dir)
        try:
            identity = source_identity(path)
        except OSError:
            continue
        return ResolvedSource(
            path=path,
            identity=identity,
            pre_cropped=True,
            first_index=artifact.span.start,
            artifact=artifact,
        )
    return ResolvedSource(
        path=parent, identity=parent_identity, pre_cropped=False, first_index=0
    )
