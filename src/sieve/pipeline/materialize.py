"""Cut one replicate's crop to a file, and refuse to register one that lies.

This is the first thing SIEVE writes that outlives the process. What is at rest
is a video file FFV1-encoded from exactly the pixels the executor would have
cropped, in the format the current graph decodes — so it opens in any player,
and it opens in SIEVE as an ordinary source with an identity of its own.

**The artifact is a child source, not a proxy for the parent.** Nothing here
writes a record that claims the parent's identity, and no key derivation
changes: a run against the artifact roots off `source_identity(<the file>)` with
no region at all. See `CropRecord` for what that buys and what it costs.

**Verification is a corruption guard, and it is not optional.** The measurement
that chose the codec also found a *lossless* encoding whose pixels came back
wrong on every frame through the same reader that reads everything else (v2's
`docs/findings/2026.07.28-the-crop-artifact-is-ffv1.md`): right shape, right
size, right frame count, wrong content, and no check anywhere in the decode path
that could tell. So the write pass holds a digest and two cheap statistics per
fed frame, reads its own output back through `VideoReader`, and compares. A file
that fails is deleted and the failure raised — never registered, never returned.

The tolerance is deliberately gross — `MAX_STATISTIC_DRIFT` grey levels of mean
and of standard deviation, and only for frames whose digest did not already
match. FFV1 passes on the digest and always will; what the tolerance is for is
the class of failure the finding actually measured, which is not drift but
garbage, and garbage does not land within two grey levels of the frame it is
impersonating. It is not a parity gate and must not be tightened into one —
byte-parity with the parent is a free bonus of the codec, not part of what makes
the artifact the artifact.

**What the rename changed.** v2 took a `Replicate` and read the region off it. A
v3 replicate carries no geometry — a region is a per-replicate override of a crop
node's `region` parameter (`adr/detector-is-a-node.md`) — so the caller resolves
the region and hands it over, and the name that survives is display text seeding
a file name. The record references no replicate either way: `CropRecord.backs`
matches on geometry and parentage, so a written cut outlives the rename and even
the deletion of the replicate it was cut for.

Nothing is parallelised here. A prefetching source would reorder nothing — this
is a strictly sequential walk — and would take decode workers from whatever else
the session is doing.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from sieve.core.pipeline_model import CropFormat, CropRecord, SourceSpan
from sieve.core.types import ROI, FrameSpan
from sieve.decode.identity import decoder_identity
from sieve.decode.reader import VideoReader
from sieve.pipeline.cache_key import source_identity
from sieve.storage.crop_writer import write_ffv1
from sieve.tools.crop import CropParams
from sieve.tools.crop import run as crop_frame

#: How far a read-back frame's mean or standard deviation may sit from the fed
#: frame's, in grey levels, when the digests do not match. See the module
#: docstring: this is the "is it garbage" threshold, not a fidelity budget.
MAX_STATISTIC_DRIFT = 2.0

#: Where artifacts live: `<video stem>.crops/` beside the project file. A
#: convention rather than a lookup — the record carries the path, so moving the
#: folder costs a rebase and not a search.
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


def artifact_filename(name: str, fmt: CropFormat, span: SourceSpan, region: ROI) -> str:
    """`<name slug>-<format>-<start>-<end>-<x>x<y>-<w>x<h>.mkv`.

    The name is convenience and never identity — two replicates named the same,
    or named nothing, produce the same slug — so every other component of the
    record that a folder can hold is in the stem too, and the path is a pure
    function of the record rather than of what the folder already contains. That
    is what keeps two distinct cuts off one file
    (`findings/2026.08.07-two-crops-of-one-name-and-span-write-one-file-and-backs-still-says-yes.md`)
    while leaving one cut written twice on one file, which is `CropRecord.identity`'s
    rule: the second write replaces the first rather than accumulating beside it.
    A suffix counted off the folder would have satisfied the first and broken the
    second.

    `cut_from` is the one component absent, and the folder carries it instead:
    artifacts live under the parent's stem, so a crop of a different source is
    already elsewhere.
    """
    slug = _SLUG_STRIP.sub("-", name.lower()).strip("-") or "replicate"
    box = f"{region.x}x{region.y}-{region.width}x{region.height}"
    return f"{slug}-{fmt}-{span.start}-{span.end}-{box}.mkv"


def materialize_crop(
    video: Path,
    region: ROI,
    span: SourceSpan,
    *,
    name: str,
    project_dir: Path,
    luma: bool,
    cancelled: Callable[[], bool] | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> CropRecord:
    """Write `region`'s crop of `video` over `span`, verified, and record it.

    Atomic in the sense that matters to a later session: the encode goes to
    `<name>.part.mkv`, verification reads *that*, and only a file that passed is
    renamed into place. A crash, a cancellation, or a verification failure leaves
    the destination name either absent or holding the previous good artifact —
    never a truncated file that `backs` would happily match.

    Args:
        video: The parent footage.
        region: What to cut, in decoded source pixels. Recorded verbatim; the
            clamp to the frame that actually arrived is applied to the pixels
            and not to the record, so a region overhanging the frame edge still
            matches its own file.
        span: Source frames `[start, end)`. Artifact frame 0 is `span.start`.
        name: Display text seeding the file name. Never read back.
        project_dir: What the recorded path is relative to.
        luma: Decode the luma plane rather than colour — `not
            Dag.needs_chroma` for the graph that will read this. One artifact per
            format, and the caller derives it rather than choosing it.
        cancelled: Polled once per source frame. Truthy withdraws the write.
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
    # Before the write, deliberately: this is what the artifact was cut from, and
    # stat'ing the parent after a minute of reading it would record the identity
    # it had at the *end* of a pass that may have raced a copy.
    cut_from = source_identity(video)

    destination = crops_dir(video, project_dir)
    destination.mkdir(parents=True, exist_ok=True)
    final = destination / artifact_filename(name, fmt, span, region)
    part = final.with_name(f"{final.stem}.part.mkv")

    fed = _FedFrames()
    try:
        with VideoReader(video, luma=luma) as reader:
            write_ffv1(
                part,
                fed.tee(_cropped(reader, region, span, cancelled, progress)),
                fps=reader.metadata.fps,
            )
        _verify(part, fed, luma=luma)
    except BaseException:
        part.unlink(missing_ok=True)
        raise

    part.replace(final)
    return CropRecord(
        path=_relative_posix(final, project_dir),
        region=region,
        format=fmt,
        span=span,
        cut_from=cut_from,
        decoder=decoder_identity(),
    )


class _FedFrames:
    """The per-frame evidence the read-back pass is checked against.

    A digest *and* two statistics, because they answer different questions and
    the cheap one is the only one available when the strict one fails. The digest
    is over the frame's bytes as fed; mean and standard deviation are what the
    tolerance path compares when a digest misses, since the frames themselves are
    long gone by then — holding a whole span's crops in memory to compare against
    is the one thing this pass must not do.
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
    region: ROI,
    span: SourceSpan,
    cancelled: Callable[[], bool] | None,
    progress: Callable[[int, int], None] | None,
) -> Iterator[NDArray[Any]]:
    """`region` of every frame in `span`, in order.

    Through `tools/crop.py`'s own `run`, not through a slice spelt here: the
    clamp and the copy are that tool's definition of what a crop is, and a second
    spelling of it is how an artifact and the graph it stands in for start
    disagreeing about a region that overhangs the frame edge.
    """
    params = CropParams(region=region)
    for index in range(span.start, span.end):
        if cancelled is not None and cancelled():
            raise MaterializeCancelledError(f"withdrawn after {index - span.start} frames")
        frame = reader.read(index)
        yield crop_frame(params, FrameSpan((frame,)), None).data
        if progress is not None:
            progress(index - span.start + 1, span.frame_count)


def _verify(path: Path, fed: _FedFrames, *, luma: bool) -> None:
    """Read `path` back and refuse it if it is not what was fed.

    Through `VideoReader`, in the format the artifact will actually be served in,
    because that is the whole point: the failure this guards against lives in the
    reader's interpretation of the file and is invisible to anything that checks
    the encoder instead.

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
                    "not a usable crop of this region and has been deleted."
                )


def _digest(array: NDArray[Any]) -> str:
    """A content hash of one frame, over its bytes in C order."""
    return hashlib.blake2b(np.ascontiguousarray(array).tobytes(), digest_size=16).hexdigest()


def _relative_posix(target: Path, base: Path) -> str:
    """`target` relative to `base` as POSIX, or absolute across drives.

    The same rule `SourceRef` and `Sink` follow, spelt here because those reach
    it through a private helper on the artifact model and a fourth caller
    importing a private name is worse than four lines.
    """
    try:
        relative = target.resolve().relative_to(base.resolve())
    except ValueError:
        return target.resolve().as_posix()
    return relative.as_posix()
