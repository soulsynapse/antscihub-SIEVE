"""Cut one replicate's crop to a file, and refuse to register one that lies.

This is the first thing SIEVE writes that outlives the process. The result is a video file
FFV1-encoded from exactly the pixels the executor would have cropped, in the
format the current graph decodes — so it opens in any player, and it opens in
SIEVE as an ordinary source with an identity of its own.

**The artifact is a child source, not a proxy for the parent.** Nothing here
writes a record that claims the parent's identity, and no key derivation
changes: a run against the artifact roots off `source_identity(<the file>)`
with `roi=None`. See `CropArtifact` for what that buys and what it costs.

**Verification is a corruption guard, and it is not optional.** The measurement
that chose the codec also found a *lossless* encoding whose pixels came back
wrong on every frame through the same reader that reads everything else
(`docs/findings/2026.07.28-the-crop-artifact-is-ffv1.md`): right shape, right
size, right frame count, wrong content, and no check anywhere in the decode path
that could tell. So the write pass holds a digest and two cheap statistics per
fed frame, reads its own output back through `VideoReader`, and compares. A file
that fails is deleted and the failure raised — never registered, never returned
(rule 6: refuse rather than hand back a plausible artifact).

The tolerance is deliberately gross — `MAX_STATISTIC_DRIFT` grey levels of mean
and of standard deviation, and only for frames whose digest did not already
match. FFV1 passes on the digest and always will; what the tolerance is for is
the class of failure the finding actually measured, which is not drift but
garbage, and garbage does not land within two grey levels of the frame it is
impersonating. It is not a parity gate and must not be tightened into one —
byte-parity with the parent was demoted to a free bonus the day the identity
model changed.

**Cost.** The write pass is the decode it was already going to do: 46 s luma /
124 s BGR over the 77-second reference clip, with under 7 s of encode on top,
plus a read-back that costs 0.09 ms/frame. Nothing is parallelised here — a
`PrefetchFrameSource` would reorder nothing (this is a strictly sequential
walk) and would take decode workers from whatever else the session is doing,
which rule 5 makes a declaration, not a local optimisation.
"""

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

#: How far a read-back frame's mean or standard deviation may sit from the fed
#: frame's, in grey levels, when the digests do not match. See the module
#: docstring: this is the "is it garbage" threshold, not a fidelity budget.
MAX_STATISTIC_DRIFT = 2.0

#: Where artifacts live: `<video stem>.crops/` beside the project file. VISION
#: step 1's folder-per-transformation, and a convention rather than a lookup —
#: the record carries the path, so moving the folder costs a rebase and not a
#: search.
CROPS_SUFFIX = ".crops"

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


class MaterializeCancelledError(RuntimeError):
    """The caller withdrew mid-write. No file is left behind."""


class CropVerificationError(RuntimeError):
    """The written file did not read back as what was fed to it.

    Raised after the part file has been deleted, so the failure cannot leave a
    half-trusted artifact on disk for a later session to find and believe.
    """


def crops_dir(video: Path, project_dir: Path) -> Path:
    """The folder artifacts cut from `video` belong in. Need not exist."""
    return project_dir / f"{video.stem}{CROPS_SUFFIX}"


def artifact_filename(name: str, fmt: CropFormat, span: ClipRange) -> str:
    """`<replicate slug>-<format>-<start>-<end>.mkv`.

    Convenience, never identity: two replicates named the same produce the same
    stem, and what distinguishes their artifacts is the ROI on the record, so
    the name is disambiguated on the way out rather than trusted on the way in.
    """
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
    """Write `replicate`'s crop of `video` over `span`, verified, and record it.

    Atomic in the sense that matters to a later session: the encode goes to
    `<name>.part.mkv`, verification reads *that*, and only a file that passed is
    renamed into place. A crash, a cancellation, or a verification failure
    leaves the destination name either absent or holding the previous good
    artifact — never a truncated file that `backs()` would happily match.

    Args:
        video: The parent footage.
        replicate: Whose ROI is cut. Its name seeds the file name; its
            `roi` goes on the record verbatim.
        span: Source frames `[start, end)`. Artifact frame 0 is `span.start`.
        project_dir: What the recorded path is relative to.
        luma: Decode the luma plane rather than colour — `not
            Dag.needs_chroma` for the graph that will read this. One artifact
            per format, and the caller derives it rather than choosing it.
        cancelled: Polled once per fed frame. Truthy withdraws the write.
        progress: Called with `(frames written, frames total)` per fed frame.

    Returns:
        The record to hand to `Project.with_crop`.

    Raises:
        VideoDecodeError: if the parent cannot be opened or the span is not in
            it.
        CropWriteError: if the encoder refuses what it was fed.
        CropVerificationError: if the file does not read back as what was fed.
        MaterializeCancelledError: if `cancelled` returned true.
        OSError: if the parent is not where it is said to be, or the artifact
            folder cannot be made.
    """
    fmt: CropFormat = "luma" if luma else "bgr"
    # Before the write, deliberately: this is what the artifact was cut from,
    # and stat'ing the parent after a minute of reading it would record the
    # identity it had at the *end* of a pass that may have raced a copy.
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
    """The per-frame evidence the read-back pass is checked against.

    A digest *and* two statistics, because they answer different questions and
    the cheap one is the only one available when the strict one fails. The
    digest is over the frame's bytes as fed; mean and standard deviation are
    what the tolerance path compares when a digest misses, since the frames
    themselves are long gone by then — holding 4 630 crops in memory to compare
    against is the one thing this pass must not do.
    """

    def __init__(self) -> None:
        self.digests: list[str] = []
        self.stats: list[tuple[float, float]] = []
        self.shape: tuple[int, ...] = ()

    def tee(self, frames: Iterator[NDArray[Any]]) -> Iterator[NDArray[Any]]:
        """Yield `frames` unchanged, recording evidence as they pass."""
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
    """The replicate's region of every frame in `span`, in order.

    The crop is `ROI.clamped_to(...).crop(...)` — the executor's one definition,
    reached through the same two calls rather than reimplemented — which is what
    makes "the artifact holds the pixels the graph would have seen" a property
    of construction instead of a claim to be tested.
    """
    for index in range(span.start, span.end):
        if cancelled is not None and cancelled():
            raise MaterializeCancelledError(f"withdrawn after {index - span.start} frames")
        frame = reader.read(index)
        yield roi.clamped_to(frame.width, frame.height).crop(frame.data)
        if progress is not None:
            progress(index - span.start + 1, span.frame_count)


def _verify(path: Path, fed: _FedFrames, *, luma: bool) -> None:
    """Read `path` back and refuse it if it is not what was fed.

    Through `VideoReader`, in the format the artifact will actually be served
    in, because that is the whole point: the failure this guards against lives
    in the reader's interpretation of the file and is invisible to anything
    that checks the encoder instead.

    Raises:
        CropVerificationError: on a frame count, a shape, or a content mismatch.
    """
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
            drift = max(abs(float(data.mean()) - mean), abs(float(data.std()) - deviation))
            if drift > MAX_STATISTIC_DRIFT:
                raise CropVerificationError(
                    f"{path.name} frame {index} reads back as different pixels than were fed "
                    f"(mean and deviation off by up to {drift:.1f} grey levels). The file is "
                    "not a usable crop of this replicate and has been deleted."
                )


def _digest(array: NDArray[Any]) -> str:
    """A content hash of one frame, over its bytes in C order."""
    return hashlib.blake2b(np.ascontiguousarray(array).tobytes(), digest_size=16).hexdigest()


def _relative_posix(target: Path, base: Path) -> str:
    """`target` relative to `base` as POSIX, or absolute across drives.

    The same rule `SourceRef` and `Sink` follow, spelt here because those two
    reach it through a private helper on the artifact model and a fourth caller
    importing a private name is worse than four lines.
    """
    try:
        relative = target.resolve().relative_to(base.resolve())
    except ValueError:
        return target.resolve().as_posix()
    return relative.as_posix()
