from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from sieve.core.pipeline_model import ClipRange, CropArtifact, CropFormat
from sieve.core.replicates import Replicate
from sieve.core.types import ROI
from sieve.decode.identity import decoder_identity
from sieve.decode.reader import VideoReader
from sieve.pipeline.cache_key import source_identity
from sieve.storage.crop_writer import write_ffv1


MAX_STATISTIC_DRIFT = 2.0


CROPS_SUFFIX = ".crops"

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


class MaterializeCancelledError(RuntimeError):
    pass


class CropVerificationError(RuntimeError):
    pass


def crops_dir(video: Path, project_dir: Path) -> Path:
    return project_dir / f"{video.stem}{CROPS_SUFFIX}"


def artifact_filename(name: str, fmt: CropFormat, span: ClipRange) -> str:
    slug = _SLUG_STRIP.sub("-", name.lower()).strip("-") or "replicate"
    return f"{slug}-{fmt}-{span.start}-{span.end}.mkv"


def materialize_crop(
    video: Path,
    replicate: Replicate,
    span: ClipRange,
    *,
    project_dir: Path,
    luma: bool,
    cancelled: Callable[[], bool] | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> CropArtifact:
    fmt: CropFormat = "luma" if luma else "bgr"
    cut_from = source_identity(video)
    destination = crops_dir(video, project_dir)
    destination.mkdir(parents=True, exist_ok=True)
    final = destination / artifact_filename(replicate.name, fmt, span)
    part = final.with_name(f"{final.stem}.part.mkv")
    fed = _FedFrames()
    try:
        with VideoReader(video, luma=luma) as reader:
            write_ffv1(
                part,
                fed.tee(_cropped(reader, replicate.roi, span, cancelled, progress)),
                fps=reader.metadata.fps,
            )
        _verify(part, fed, luma=luma)
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    part.replace(final)
    return CropArtifact(
        path=_relative_posix(final, project_dir),
        roi=replicate.roi,
        format=fmt,
        span=span,
        cut_from=cut_from,
        decoder=decoder_identity(),
    )


class _FedFrames:
    def __init__(self) -> None:
        self.digests: list[str] = []
        self.stats: list[tuple[float, float]] = []
        self.shape: tuple[int, ...] = ()

    def tee(self, frames: Iterator[NDArray[Any]]) -> Iterator[NDArray[Any]]:
        for array in frames:
            self.shape = self.shape or array.shape
            self.digests.append(_digest(array))
            self.stats.append((float(array.mean()), float(array.std())))
            yield array

    def __len__(self) -> int:
        return len(self.digests)


def _cropped(
    reader: VideoReader,
    roi: ROI,
    span: ClipRange,
    cancelled: Callable[[], bool] | None,
    progress: Callable[[int, int], None] | None,
) -> Iterator[NDArray[Any]]:
    for index in range(span.start, span.end):
        if cancelled is not None and cancelled():
            raise MaterializeCancelledError(
                f"withdrawn after {index - span.start} frames"
            )
        frame = reader.read(index)
        yield roi.clamped_to(frame.width, frame.height).crop(frame.data)
        if progress is not None:
            progress(index - span.start + 1, span.frame_count)


def _verify(path: Path, fed: _FedFrames, *, luma: bool) -> None:
    with VideoReader(path, luma=luma) as reader:
        if reader.metadata.frame_count != len(fed):
            raise CropVerificationError(
                f"{path.name} holds {reader.metadata.frame_count} frames, but "
                f"{len(fed)} were written to it"
            )
        for index, (digest, (mean, deviation)) in enumerate(
            zip(fed.digests, fed.stats, strict=True)
        ):
            data = reader.read(index).data
            if data.shape != fed.shape:
                raise CropVerificationError(
                    f"{path.name} frame {index} reads back as {data.shape}, not {fed.shape}"
                )
            if _digest(data) == digest:
                continue
            drift = max(
                abs(float(data.mean()) - mean), abs(float(data.std()) - deviation)
            )
            if drift > MAX_STATISTIC_DRIFT:
                raise CropVerificationError(
                    f"{path.name} frame {index} reads back as different pixels than were fed "
                    f"(mean and deviation off by up to {drift:.1f} grey levels). The file is "
                    "not a usable crop of this replicate and has been deleted."
                )


def _digest(array: NDArray[Any]) -> str:
    return hashlib.blake2b(
        np.ascontiguousarray(array).tobytes(), digest_size=16
    ).hexdigest()


def _relative_posix(target: Path, base: Path) -> str:
    try:
        relative = target.resolve().relative_to(base.resolve())
    except ValueError:
        return target.resolve().as_posix()
    return relative.as_posix()
