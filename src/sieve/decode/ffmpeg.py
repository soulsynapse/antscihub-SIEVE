"""FFmpeg rawvideo source for a crop/scale prefix lowered out of the graph."""

from __future__ import annotations

import subprocess
from fractions import Fraction
from functools import cache
from pathlib import Path
from types import TracebackType
from typing import Self

import numpy as np
from numpy.typing import NDArray

from sieve.core.types import ChannelSpec, Frame, FrameCount, FrameIndex, VideoMetadata
from sieve.decode.lowered import LOWERED_SOURCE_POLICY_VERSION, LoweredPrefix
from sieve.decode.reader import VideoDecodeError, VideoReader
from sieve.mutual.machine import available_cpus
from sieve.mutual.pool_meter import PoolMeter
from sieve.mutual.shares import PREVIEW_WORKERS

# A cap, not an ambition. An explicit CLI `--workers` can raise it, while the
# interactive GUI passes its resolved preview share.
FFMPEG_LOWERED_WORKER_CAP = PREVIEW_WORKERS


class FfmpegUnavailableError(VideoDecodeError):
    """The FFmpeg executable needed for the lowered source is not usable."""


def resolve_ffmpeg_workers(requested: int | None = None) -> int:
    """Threads the FFmpeg subprocess may use."""
    if requested is not None:
        return max(requested, 1)
    return min(available_cpus(), FFMPEG_LOWERED_WORKER_CAP)


@cache
def ffmpeg_decoder_identity(executable: str = "ffmpeg") -> str:
    """The FFmpeg build that owns lowered-source pixels."""
    try:
        result = subprocess.run(
            [executable, "-version"],
            capture_output=True,
            check=True,
            text=True,
            timeout=5.0,
        )
    except (
        FileNotFoundError,
        OSError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ) as error:
        raise FfmpegUnavailableError(f"{executable!r} is not a usable FFmpeg executable") from error
    first = result.stdout.splitlines()[0].strip()
    if not first:
        raise FfmpegUnavailableError(f"{executable!r} reported no version")
    return f"{first}/lowered-policy-{LOWERED_SOURCE_POLICY_VERSION}"


def ffmpeg_lowered_command(
    path: Path,
    prefix: LoweredPrefix,
    *,
    start_index: int | FrameIndex,
    fps: Fraction,
    workers: int,
    executable: str = "ffmpeg",
) -> tuple[str, ...]:
    """Command that emits gray8 working-size frames from `start_index` onward."""
    return (
        executable,
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-threads",
        str(max(workers, 1)),
        "-ss",
        _timestamp(start_index, fps),
        "-i",
        str(path),
        "-filter_threads",
        str(max(workers, 1)),
        "-filter_complex_threads",
        str(max(workers, 1)),
        "-vf",
        prefix.filtergraph,
        "-an",
        "-sn",
        "-dn",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "gray",
        "-",
    )


class FfmpegLoweredFrameSource:
    """A `FrameSource` backed by one FFmpeg rawvideo pipe.

    Optimized for the executor's forward walk. A non-sequential read restarts
    the pipe at that source frame, which keeps single-frame previews correct
    without building a prefetcher around a process that already owns threads.
    """

    def __init__(
        self,
        path: Path | str,
        prefix: LoweredPrefix,
        *,
        workers: int | None = None,
        meter: PoolMeter | None = None,
        executable: str = "ffmpeg",
        source_metadata: VideoMetadata | None = None,
    ) -> None:
        self._path = Path(path)
        if not self._path.is_file():
            raise VideoDecodeError(f"No such video file: {self._path}")
        self._prefix = prefix
        self._worker_count = resolve_ffmpeg_workers(workers)
        self._meter = PoolMeter() if meter is None else meter
        self._executable = executable
        source = _metadata(self._path) if source_metadata is None else source_metadata
        _check_prefix_fits(prefix, source)
        if source.fps <= 0:
            raise VideoDecodeError(
                f"{self._path} states no frame rate; FFmpeg lowering seeks by frame time"
            )
        self._metadata = VideoMetadata(
            path=self._path,
            width=prefix.output_width,
            height=prefix.output_height,
            fps=source.fps,
            frame_count=source.frame_count,
        )
        self._process: subprocess.Popen[bytes] | None = None
        self._next: FrameIndex | None = None

    @property
    def luma(self) -> bool:
        """Lowered FFmpeg currently emits only gray8 frames."""
        return True

    @property
    def metadata(self) -> VideoMetadata:
        return self._metadata

    @property
    def workers(self) -> int:
        return self._worker_count

    @property
    def meter(self) -> PoolMeter:
        return self._meter

    def read(self, index: int | FrameIndex) -> Frame:
        index = FrameIndex.of(index)
        if not 0 <= index < self._metadata.frame_count:
            raise VideoDecodeError(
                f"Frame {index} out of range 0..{self._metadata.frame_count - 1}"
            )
        if self._process is None or self._next != index:
            self._restart(index)
        process = self._require_process()
        stdout = process.stdout
        if stdout is None:
            raise VideoDecodeError("FFmpeg process has no stdout pipe")
        with self._meter.working():
            raw = stdout.read(self._prefix.frame_bytes)
        if len(raw) != self._prefix.frame_bytes:
            error = _stderr_text(process)
            self._stop_process()
            suffix = "" if not error else f": {error}"
            raise VideoDecodeError(f"FFmpeg ended before frame {index} of {self._path}{suffix}")
        data = _gray_frame(raw, self._prefix.output_width, self._prefix.output_height)
        self._next = index + FrameCount(1)
        self._meter.set_depth(0)
        return Frame(data=data, index=index, channels=ChannelSpec.GRAY)

    def _restart(self, index: FrameIndex) -> None:
        self._stop_process()
        command = ffmpeg_lowered_command(
            self._path,
            self._prefix,
            start_index=index,
            fps=self._metadata.fps,
            workers=self._worker_count,
            executable=self._executable,
        )
        try:
            self._process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except (FileNotFoundError, OSError) as error:
            raise FfmpegUnavailableError(
                f"{self._executable!r} is not a usable FFmpeg executable"
            ) from error
        self._next = index

    def _require_process(self) -> subprocess.Popen[bytes]:
        if self._process is None:
            raise VideoDecodeError("FFmpeg process is not running")
        return self._process

    def close(self) -> None:
        self._stop_process()

    def _stop_process(self) -> None:
        process, self._process = self._process, None
        self._next = None
        if process is None:
            return
        for pipe in (process.stdout, process.stderr):
            if pipe is not None:
                pipe.close()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


def _metadata(path: Path) -> VideoMetadata:
    with VideoReader(path, luma=True) as reader:
        return reader.metadata


def _check_prefix_fits(prefix: LoweredPrefix, metadata: VideoMetadata) -> None:
    roi = prefix.ffmpeg_roi
    if roi.right > metadata.width or roi.bottom > metadata.height:
        raise VideoDecodeError(
            f"lowered crop {roi.width}x{roi.height}+{roi.x}+{roi.y} exceeds "
            f"{metadata.width}x{metadata.height}"
        )


def _timestamp(index: int | FrameIndex, fps: Fraction) -> str:
    if fps <= 0:
        raise VideoDecodeError("FFmpeg lowering cannot seek a source with no frame rate")
    seconds = Fraction(int(index), 1) / fps
    return f"{float(seconds):.9f}"


def _gray_frame(raw: bytes, width: int, height: int) -> NDArray[np.uint8]:
    return np.frombuffer(raw, dtype=np.uint8).reshape((height, width)).copy()


def _stderr_text(process: subprocess.Popen[bytes]) -> str:
    stderr = process.stderr
    if stderr is None:
        return ""
    try:
        return stderr.read().decode("utf-8", errors="replace").strip()
    except OSError:
        return ""
