"""OpenCV `VideoCapture` wrapper trading grab-vs-seek and BGR-vs-luma for
measured cost, keeping only the change the cache key can see.

DECISION: seek accuracy over source bit-depth. Frames come back 8-bit — BGR,
or luma under `luma=True` — because that is what `VideoCapture` gives and what
the cache key assumes; a high-bit-depth path would be a separate reader.

Forward jumps under `GRAB_FORWARD_LIMIT` grab instead of seeking — cheaper,
and landing on the exact frame rather than wherever the container's index
rounds to (`docs/findings/2026.07.25-decode-cost-is-colour-conversion.md`,
`...2026.07.25-the-seek-is-irreducible.md`). Parallelising the convert is
`prefetch.py`'s job, one reader per thread; nothing here is thread-safe (see
`VideoReader`, below).

The one thing here that is not OpenCV's is the frame rate: `container_rate`
probes the header with PyAV because a `double` cannot carry 30000/1001. It
reads metadata and no frames — see its docstring for why that boundary matters.

`luma=True` requests the Y plane instead of a BGR convert
(`CAP_PROP_CONVERT_RGB=0`) — about a third the bytes and cost
(`docs/completed-todo/2026.07.27-grayscale-and-the-luma-decode.md`) — off by
default so an existing caller's cache key never moves unasked. The plane is
not `cvtColor(BGR2GRAY)`'s output (`decode/identity.py`'s
`DECODE_POLICY_VERSION` comment), so this is a decode *policy*, hashed through
that constant and `cache_key.source_key`'s format field, never a transparent
optimisation. Who asks for it is `pipeline/dag.py`'s `Dag.needs_chroma`
("the decode format is a property of the graph, not a setting"); this module
only obeys.
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from types import TracebackType
from typing import Any, Self

import av
import av.error
import cv2
from numpy.typing import NDArray

from sieve.core.types import ChannelSpec, Frame, FrameIndex, VideoMetadata

GRAB_FORWARD_LIMIT = 40


class VideoDecodeError(RuntimeError):
    pass


def container_rate(path: Path) -> Fraction:
    """The frame rate the container declares, as the rational it declares it as.

    OpenCV cannot answer this. `CAP_PROP_FPS` is a `double`, and the division
    that produced it has already thrown the denominator away: 30000/1001
    recovered from that double floors fifteen frames back to fourteen, in the
    first second of footage (`core/types.py`'s header carries the arithmetic).
    PyAV reads `avg_frame_rate` off the stream header — the same field OpenCV
    divides — before anything divides it.

    Metadata only. Every decoded pixel in SIEVE still comes from the
    `VideoCapture` below, so this does not make PyAV a second decoder identity;
    that is the claim `pyproject.toml`'s `av` entry makes and this is the one
    place it could quietly stop being true.

    Zero for a container that declares no rate, and zero when PyAV cannot open
    what OpenCV did — which every caller already treats as "the source has not
    said". Recovering the rational from the double with `limit_denominator` was
    the alternative: it is right for the NTSC family by luck rather than by
    construction, silently wrong for any rate whose denominator exceeds the
    limit, and a guess that is usually right is the worst kind of number to
    found a published timestamp on.
    """
    try:
        with av.open(str(path)) as container:
            streams = container.streams.video
            rate = streams[0].average_rate if streams else None
    except (av.error.FFmpegError, OSError, ValueError):
        return Fraction(0)
    return rate if rate is not None and rate > 0 else Fraction(0)


# Not thread-safe: one reader belongs to one thread. The GUI keeps its reader
# on a dedicated decode thread for exactly this reason.
class VideoReader:
    def __init__(self, path: Path | str, *, luma: bool = False) -> None:
        self._path = Path(path)
        if not self._path.is_file():
            raise VideoDecodeError(f"No such video file: {self._path}")

        self._capture = cv2.VideoCapture(str(self._path))
        if not self._capture.isOpened():
            raise VideoDecodeError(f"Could not open video: {self._path}")

        self._luma = luma
        if luma:
            # Set before the first read and never toggled after: the property
            # governs what `retrieve()` produces, and a capture that changed
            # format mid-stream would hand two shapes to one consumer.
            self._capture.set(cv2.CAP_PROP_CONVERT_RGB, 0)

        self._metadata = self._read_metadata()
        if self._metadata.frame_count <= 0:
            self._capture.release()
            raise VideoDecodeError(f"Video reports no frames: {self._path}")

        self._cursor = 0

    def _read_metadata(self) -> VideoMetadata:
        return VideoMetadata(
            path=self._path,
            width=int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            height=int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            fps=container_rate(self._path),
            frame_count=int(self._capture.get(cv2.CAP_PROP_FRAME_COUNT)),
        )

    @property
    def metadata(self) -> VideoMetadata:
        return self._metadata

    @property
    def is_open(self) -> bool:
        return self._capture.isOpened()

    @property
    def luma(self) -> bool:
        # Exposed so a caller derives a cache key from this, rather than
        # tracking its own copy of the flag that can drift from what the
        # reader actually returns.
        return self._luma

    # `max_width` is decode-side proxy media for display only — downscaled,
    # never a pipeline tool — so it must never enter the DAG or a cache key.
    def read(self, index: int | FrameIndex, max_width: int | None = None) -> Frame:
        index = int(index)
        if not 0 <= index < self._metadata.frame_count:
            raise VideoDecodeError(
                f"Frame {index} out of range 0..{self._metadata.frame_count - 1}"
            )

        self._position_at(index)
        # A failed read is always `(False, None)` — never a truthy flag with no
        # array — so the flag alone is the whole check.
        ok, data = self._capture.read()
        if not ok:
            self._cursor = -1  # Position is now unknown; force a seek next time.
            raise VideoDecodeError(f"Failed to decode frame {index} of {self._path}")
        self._cursor = index + 1

        if self._luma:
            self._check_luma_plane(data, index)

        return Frame(
            data=_downscale(data, max_width),
            index=index,
            channels=ChannelSpec.GRAY if self._luma else ChannelSpec.BGR,
        )

    # `CAP_PROP_CONVERT_RGB = 0` is a request, not a contract: the FFmpeg
    # backend can hand back something other than the Y plane — a packed
    # layout, a 10-bit source, another fallback — and says so only in a log
    # line `decode/quiet.py` drops. Unchecked, a wrong-shaped buffer treated
    # as luma renders plausible, wrong pixels nothing downstream can catch.
    # The two dimensions below are the whole test: every fallback differs in
    # at least one.
    def _check_luma_plane(self, data: NDArray[Any], index: int) -> None:
        expected = (self._metadata.height, self._metadata.width)
        if data.ndim != 2 or data.shape != expected:
            raise VideoDecodeError(
                f"Frame {index} of {self._path}: asked for the luma plane and got an array "
                f"of shape {data.shape}, not {expected}. This build's decoder does not hand "
                f"back planar luma for this source; open the reader without luma=True."
            )

    def _position_at(self, index: int) -> None:
        delta = index - self._cursor
        if delta == 0:
            return
        if 0 < delta <= GRAB_FORWARD_LIMIT:
            for _ in range(delta):
                if not self._capture.grab():
                    break
            return
        self._capture.set(cv2.CAP_PROP_POS_FRAMES, index)

    def close(self) -> None:
        self._capture.release()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


def _downscale(data: NDArray[Any], max_width: int | None) -> NDArray[Any]:
    source_height, source_width = data.shape[:2]
    if max_width is None or source_width <= max_width:
        return data
    scale = max_width / source_width
    target = (max_width, max(round(source_height * scale), 1))
    return cv2.resize(data, target, interpolation=cv2.INTER_AREA)
