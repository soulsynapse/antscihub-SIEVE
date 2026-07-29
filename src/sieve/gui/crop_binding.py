






































from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from sieve.core.pipeline_model import ClipRange, CropArtifact
from sieve.core.replicates import Replicate
from sieve.core.types import ROI


class CropState(Enum):









    ABSENT = "absent"

    WRITING = "writing"

    AT_REST = "at rest"


    STALE = "stale"


@dataclass(frozen=True, slots=True)
class CropBacking:








    state: CropState


    artifact: CropArtifact | None = None


    reason: str = ""


def backing_for(
    crops: Sequence[CropArtifact],
    index: int,
    replicates: Sequence[Replicate],
    *,
    source: str,
    luma: bool,
    project_dir: Path,
    window: ClipRange | None,
) -> CropBacking:
























    replicate = replicates[index]
    for artifact in crops:
        if not artifact.backs(replicate, source=source, luma=luma, project_dir=project_dir):
            continue
        if window is not None and (
            artifact.span.start > window.start or artifact.span.end < window.end
        ):
            return CropBacking(
                CropState.STALE,
                artifact,
                f"the window now runs [{window.start}:{window.end}) and this crop holds "
                f"[{artifact.span.start}:{artifact.span.end})",
            )
        return CropBacking(CropState.AT_REST, artifact)

    near = _near_miss(crops, replicate, source=source, luma=luma, project_dir=project_dir)
    if near is not None:
        return near
    orphan = _orphan_for(crops, index, replicates, source=source)
    if orphan is not None:
        return CropBacking(
            CropState.STALE,
            orphan,
            f"cut at {orphan.roi.width}x{orphan.roi.height} at ({orphan.roi.x}, {orphan.roi.y}); "
            "the region has moved since",
        )
    return CropBacking(CropState.ABSENT)


def _near_miss(
    crops: Sequence[CropArtifact],
    replicate: Replicate,
    *,
    source: str,
    luma: bool,
    project_dir: Path,
) -> CropBacking | None:







    for artifact in crops:
        if artifact.roi != replicate.roi:
            continue
        if not artifact.resolve(project_dir).is_file():
            return CropBacking(CropState.STALE, artifact, f"the file is not at {artifact.path}")
        if artifact.cut_from != source:
            return CropBacking(
                CropState.STALE, artifact, "the source has been re-exported since this was cut"
            )
        if artifact.luma != luma:
            written = "colour" if not artifact.luma else "luma"
            wanted = "luma" if luma else "colour"
            return CropBacking(
                CropState.STALE,
                artifact,
                f"written in {written}; the chain now decodes {wanted}",
            )
    return None


def _orphan_for(
    crops: Sequence[CropArtifact],
    index: int,
    replicates: Sequence[Replicate],
    *,
    source: str,
) -> CropArtifact | None:

    claimed = {other.roi for other in replicates}
    for artifact in crops:
        if artifact.cut_from != source or artifact.roi in claimed:
            continue
        touching = [
            position
            for position, other in enumerate(replicates)
            if _overlaps(artifact.roi, other.roi)
        ]
        if touching == [index]:
            return artifact
    return None


def _overlaps(one: ROI, other: ROI) -> bool:

    return (
        one.x < other.right
        and other.x < one.right
        and one.y < other.bottom
        and other.y < one.bottom
    )
