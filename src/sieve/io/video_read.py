"""The sole decode boundary (ADR-018).

OpenCV VideoCapture is the pinned v1 decoder. It was the only backend in the
`sieve.bench.decoder_benchmark` corpus with no mismatched random seeks on any
codec, and it is the only candidate that discards source bit depth. ADR-018
takes that trade deliberately: a scrub that lands on the wrong frame is a
correctness failure the user cannot see, and depth loss is a bounded one that
this module reports.

Two obligations from the ADR are met here rather than by convention:

- The delivered representation and the source's native depth are separate
  fields on `SourceInfo`, so a caller can tell a user at open time that a
  10-bit file is being delivered as uint8.
- `DecoderIdentity` names the library, version, and resolved backend, because
  `ARCHITECTURE.md` section 12 puts the decoder inside the code-version hash
  that contributes to cache keys. Recording it while there is one decoder is
  what makes adding a second one a clean invalidation.

[INTENT] Scope is seek, decode, and metadata. `ARCHITECTURE.md` section 5.5
also asks this module for a keyframe index, a ring buffer, and eager
head-decode on open. Those exist to keep a widget fed, no widget exists, and
building a buffering policy before there is a consumer to tune it against
means tuning it against a guess. They land with the video viewer.
"""

from __future__ import annotations

import importlib.metadata
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Final

import cv2
import numpy as np

__all__ = [
    "DELIVERED_DTYPE",
    "DELIVERED_LAYOUT",
    "DecoderIdentity",
    "FrameReadError",
    "SourceInfo",
    "VideoOpenError",
    "VideoReadError",
    "VideoReader",
    "decoder_identity",
]

# ADR-018 pins these. OpenCV delivers 8-bit BGR whatever the source is, and the
# constants exist so a caller reads the contract from the boundary that owns it
# rather than restating it.
DELIVERED_DTYPE: Final = "uint8"
DELIVERED_LAYOUT: Final = "BGR"
DELIVERED_BIT_DEPTH: Final = 8

_DISTRIBUTION: Final = "opencv-python-headless"

# FFmpeg's planar-YUV raw tags carry subsampling and bit depth in the third and
# fourth bytes -- MKTAG('Y', '3', 11, 10) is yuv420p10le. The 8-bit formats use
# ordinary readable fourccs instead, so they are listed rather than derived.
# Verified against the generated corpus: I420 for the 8-bit encodes,
# ('Y', '3', 11, 10) for 10-bit H.264, ('Y', '3', 10, 10) for ProRes 422 HQ.
_PLANAR_YUV_PREFIX: Final = b"Y3"
_EIGHT_BIT_TAGS: Final = frozenset({"I420", "IYUV", "YV12", "NV12", "YUY2", "UYVY", "BGR3", "RGB3"})
_FOURCC_BYTES: Final = 4
_BIT_DEPTH_BYTE: Final = 3
_PRINTABLE = range(32, 127)


class VideoReadError(RuntimeError):
    """Base for every failure at the decode boundary."""


class VideoOpenError(VideoReadError):
    """A file could not be opened, or opened without usable metadata."""


class FrameReadError(VideoReadError):
    """A seek was rejected, or a decode returned nothing.

    [STABLE] Separate from `VideoOpenError` because the two have different
    meanings for a caller: an open failure is a file the user cannot use at
    all, and a read failure on an opened file is the seek-accuracy property
    ADR-018 turns on giving way.
    """


@dataclass(frozen=True)
class DecoderIdentity:
    """What decoded a frame, at the granularity section 12 hashes.

    `backend` is the implementation VideoCapture resolved to (FFMPEG, MSMF,
    GSTREAMER). It belongs here because the same OpenCV version produces
    different seek behaviour through different backends, so a version alone
    does not identify the decoder that produced a cached result.
    """

    library: str
    version: str
    backend: str

    def as_hash_input(self) -> str:
        """A stable string for the code-version hash (`ARCHITECTURE.md` 12).

        Ordered and delimited rather than derived from `repr`, because a cache
        key that changes when a dataclass gains a field invalidates every
        cached result for a reason that has nothing to do with decoding.
        """
        return f"{self.library}=={self.version}@{self.backend}"


@dataclass(frozen=True)
class SourceInfo:
    """What the decoder reports about a file, including what it is discarding.

    `source_bit_depth` is `None` when the pixel-format tag is not one this
    module recognizes. [ASSUMPTION] Unknown is reported as unknown rather than
    defaulted to 8: the whole point of the field is to warn a user that depth
    is being dropped, and a field that quietly says "8" when it does not know
    is a warning that fails silently in exactly the case it exists for.
    """

    path: Path
    width: int
    height: int
    frame_count: int | None
    fps: float | None
    codec: str
    pixel_format: str
    source_bit_depth: int | None
    decoder: DecoderIdentity
    delivered_dtype: str = DELIVERED_DTYPE
    delivered_layout: str = DELIVERED_LAYOUT

    @property
    def bit_depth_reduced(self) -> bool | None:
        """Whether decode is delivering fewer bits than the source carries.

        `None` propagates the unknown from `source_bit_depth` rather than
        resolving it to `False`.
        """
        if self.source_bit_depth is None:
            return None
        return self.source_bit_depth > DELIVERED_BIT_DEPTH

    def describe_reduction(self) -> str | None:
        """A sentence for the user at open time, or `None` when nothing is lost.

        ADR-018 requires the reduction to be reported "at the point of opening
        rather than in a document". The wording lives here so the GUI and the
        CLI report the same thing.
        """
        if self.bit_depth_reduced is None:
            return (
                f"{self.path.name}: the decoder does not report this file's pixel format "
                f"({self.pixel_format!r}), so whether decode is reducing bit depth is unknown. "
                f"Frames are delivered as {self.delivered_dtype} {self.delivered_layout}."
            )
        if not self.bit_depth_reduced:
            return None
        return (
            f"{self.path.name} is {self.source_bit_depth}-bit; decode delivers "
            f"{self.delivered_dtype} {self.delivered_layout}, so input precision is "
            f"reduced to 8 bits (ADR-018)."
        )


def _fourcc_to_bytes(value: int) -> bytes:
    return bytes((value >> (8 * i)) & 0xFF for i in range(_FOURCC_BYTES))


def _describe_fourcc(value: int) -> str:
    """A readable tag, falling back to the integer when the bytes are not text.

    The planar-YUV tags are deliberately not text -- two of their four bytes
    are small integers -- so a printable-only rule would render exactly the
    formats whose depth matters as unprintable garbage.
    """
    if value <= 0:
        return str(value)
    raw = _fourcc_to_bytes(value)
    if all(byte in _PRINTABLE for byte in raw):
        return raw.decode("ascii")
    return "".join(chr(byte) if byte in _PRINTABLE else f"\\x{byte:02x}" for byte in raw)


def _source_bit_depth(pixel_format: int) -> int | None:
    """Bit depth from the codec pixel-format tag, or `None` when unrecognized.

    [STALE WHEN] A source appears whose tag is neither an 8-bit fourcc in
    `_EIGHT_BIT_TAGS` nor an FFmpeg planar-YUV tag. The failure mode is a
    reported unknown rather than a wrong number, which is why the table is
    allowed to be incomplete.
    """
    if pixel_format <= 0:
        return None
    raw = _fourcc_to_bytes(pixel_format)
    if raw.startswith(_PLANAR_YUV_PREFIX):
        depth = raw[_BIT_DEPTH_BYTE]
        return depth if depth > 0 else None
    try:
        tag = raw.decode("ascii")
    except UnicodeDecodeError:
        return None
    return 8 if tag in _EIGHT_BIT_TAGS else None


def decoder_identity(capture: cv2.VideoCapture | None = None) -> DecoderIdentity:
    """The pinned decoder's identity, for cache keys and provenance.

    Without a capture the backend is reported as `unresolved`: VideoCapture
    picks its backend per file, so there is no process-wide answer, and
    inventing one would put a value in a cache key that no decode produced.
    """
    try:
        version = importlib.metadata.version(_DISTRIBUTION)
    except importlib.metadata.PackageNotFoundError:
        # The import worked, so a decoder is present under some other
        # distribution name (`opencv-python`, a system build). The runtime
        # version is the honest answer; the distribution name is not.
        version = cv2.__version__
    backend = capture.getBackendName() if capture is not None else "unresolved"
    return DecoderIdentity(library=_DISTRIBUTION, version=version, backend=backend)


class VideoReader:
    """Seek-accurate, index-based frame access over one file.

    Not thread-safe, and deliberately not made so. One VideoCapture handle has
    one position, so sharing a reader between a scrub and a background decode
    means two callers racing over that position. `ARCHITECTURE.md` 5.5 puts
    the decoder thread behind the viewer; a second reader on the same path is
    the mechanism, not a lock on this one.
    """

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        if not self._path.is_file():
            raise VideoOpenError(f"No such video file: {self._path}")
        capture = cv2.VideoCapture(str(self._path))
        if not capture.isOpened():
            raise VideoOpenError(
                f"OpenCV could not open {self._path}. The file may use a codec this "
                f"build does not carry, or may not be a video."
            )
        self._capture: cv2.VideoCapture | None = capture
        self._info = self._probe(capture)
        # Mirrors the handle's position so a sequential read can skip the seek.
        # `CAP_PROP_POS_FRAMES` is readable, but it is a property query per
        # frame inside the 50 ms scrub budget for a value already known here.
        self._position = 0

    def _probe(self, capture: cv2.VideoCapture) -> SourceInfo:
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if width <= 0 or height <= 0:
            capture.release()
            raise VideoOpenError(
                f"OpenCV opened {self._path} but reports a {width}x{height} frame size, "
                f"so there is nothing to decode."
            )
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        pixel_format = int(capture.get(cv2.CAP_PROP_CODEC_PIXEL_FORMAT))
        return SourceInfo(
            path=self._path,
            width=width,
            height=height,
            # A container without a frame count is usable for sequential reads
            # and not for index-based scrubbing. Reported as unknown so the
            # caller decides, rather than raising at open on a file the user
            # may only want to play.
            frame_count=frame_count if frame_count > 0 else None,
            fps=fps if fps > 0 else None,
            codec=_describe_fourcc(int(capture.get(cv2.CAP_PROP_FOURCC))),
            pixel_format=_describe_fourcc(pixel_format),
            source_bit_depth=_source_bit_depth(pixel_format),
            decoder=decoder_identity(capture),
        )

    @property
    def info(self) -> SourceInfo:
        return self._info

    @property
    def position(self) -> int:
        """The index the next `read_next` returns."""
        return self._position

    @property
    def closed(self) -> bool:
        return self._capture is None

    def _active(self) -> cv2.VideoCapture:
        if self._capture is None:
            raise VideoReadError(f"This reader for {self._path} is closed.")
        return self._capture

    def read(self, index: int) -> np.ndarray:
        """Decode the frame at `index`.

        [STABLE] The seek is skipped when the handle already sits at `index`.
        A forward scrub is a sequence of adjacent reads, and seeking to the
        current position discards decoder state that the next frame needs --
        it is the difference between a keyframe-relative decode and a decode
        that already has its reference frames.
        """
        if index < 0:
            raise FrameReadError(f"Frame index {index} is negative.")
        total = self._info.frame_count
        if total is not None and index >= total:
            raise FrameReadError(
                f"Frame index {index} is past the end of {self._path.name}, "
                f"which reports {total} frames."
            )
        if index != self._position:
            self._seek(index)
        return self._decode(index)

    def _seek(self, index: int) -> None:
        """Reposition the handle. Separate from `read` so that "did this read
        seek?" is an observable question rather than an inference from timing.
        """
        capture = self._active()
        if not capture.set(cv2.CAP_PROP_POS_FRAMES, index):
            raise FrameReadError(f"OpenCV rejected a seek to frame {index} of {self._path.name}.")
        self._position = index

    def read_next(self) -> np.ndarray:
        """Decode the frame at `position` and advance.

        The short forward decode after a keyframe seek that `ARCHITECTURE.md`
        5.5 describes is this called in a loop.
        """
        return self._decode(self._position)

    def _decode(self, index: int) -> np.ndarray:
        capture = self._active()
        ok, frame = capture.read()
        if not ok or frame is None:
            raise FrameReadError(
                f"OpenCV decoded nothing at frame {index} of {self._path.name}. "
                f"A seek that succeeds and a decode that fails is the seek-accuracy "
                f"failure mode ADR-018 pins this decoder to avoid."
            )
        self._position = index + 1
        return frame

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def __enter__(self) -> VideoReader:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def __repr__(self) -> str:
        state = "closed" if self.closed else f"at frame {self._position}"
        return f"<VideoReader {self._path.name} {self._info.width}x{self._info.height} {state}>"
