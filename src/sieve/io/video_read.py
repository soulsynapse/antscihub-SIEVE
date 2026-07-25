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

The keyframe index, the ring buffer, and the decoder thread that
`ARCHITECTURE.md` section 5.5 asks this module for land here too, tuned
against the video viewer's measured repaint cost (`tests/gui/measure_repaint.py`,
`DECODE_SHARE` in `tests/bench/test_decode_seek.py`) rather than a guess.
"""

from __future__ import annotations

import bisect
import importlib.metadata
import threading
from collections import OrderedDict
from collections.abc import Callable
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
    "DecoderThread",
    "FrameReadError",
    "FrameRingBuffer",
    "KeyframeIndex",
    "SourceInfo",
    "VideoOpenError",
    "VideoReadError",
    "VideoReader",
    "build_keyframe_index",
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

    def last_frame_type(self) -> int:
        """ASCII code of the most recently decoded frame's type.

        Valid immediately after `read` or `read_next`. `cv2.CAP_PROP_FRAME_TYPE`
        reports it as a bare ASCII code (`I` = 73, `P` = 80, `B` = 66) rather
        than as an enum -- confirmed by probing the corpus, since OpenCV's
        `VideoCapture` documents no dedicated keyframe flag.
        `build_keyframe_index` is the caller: it is what makes a keyframe
        index constructible through the pinned ADR-018 decoder without a
        second decode dependency.
        """
        return int(self._active().get(cv2.CAP_PROP_FRAME_TYPE))

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


_KEYFRAME_TYPE: Final = ord("I")


@dataclass(frozen=True)
class KeyframeIndex:
    """Which frame indices are keyframes, ascending, always including 0.

    Answers "nearest keyframe at or before N" -- the piece `ARCHITECTURE.md`
    5.5's "scrub hits the nearest keyframe plus a short forward decode"
    describes, and the input a prefetcher can use to judge whether a target is
    a cheap or an expensive decode.
    """

    frame_count: int
    keyframes: tuple[int, ...]

    def nearest_at_or_before(self, index: int) -> int:
        position = bisect.bisect_right(self.keyframes, index) - 1
        return self.keyframes[max(position, 0)]


def build_keyframe_index(
    path: Path | str, *, cancelled: Callable[[], bool] | None = None
) -> KeyframeIndex | None:
    """Sequentially decode `path` once, recording which indices are keyframes.

    Opens its own `VideoReader` rather than taking one from the caller: this
    walks every frame in the file, and sharing a handle with a live scrub means
    two callers racing the one position `VideoReader` documents itself as not
    safe for. Meant to run off the GUI thread -- `ARCHITECTURE.md` 5.5 asks for
    the full index "in the background without blocking display" -- so
    `cancelled` is polled between frames rather than the caller having to kill
    a thread. Returns `None` on a file with no reported frame count (nothing to
    index) or on cancellation (a partial index would silently mis-answer the
    frames it never reached).
    """
    with VideoReader(path) as reader:
        total = reader.info.frame_count
        if total is None:
            return None
        keyframes: list[int] = []
        for index in range(total):
            if cancelled is not None and cancelled():
                return None
            reader.read_next()
            if reader.last_frame_type() == _KEYFRAME_TYPE:
                keyframes.append(index)
        if not keyframes or keyframes[0] != 0:
            keyframes.insert(0, 0)
        return KeyframeIndex(frame_count=total, keyframes=tuple(keyframes))


class FrameRingBuffer:
    """A byte-budgeted, not frame-budgeted, LRU cache of decoded frames.

    [ASSUMPTION] Sized in bytes because a frame-count budget is a fiction
    across sources: the corpus clips this repo measures against are 640x360
    (~0.7 MB/frame uncompressed BGR), but HD footage is ~6.2 MB/frame -- a
    16-frame budget is 11 MB on one and 100 MB on the other. Eviction is a
    plain `OrderedDict` least-recently-used drop, deliberately: this backs a
    50 ms scrub budget, not a general cache, and a smarter policy is
    complexity this session's measured headroom does not ask for.
    """

    def __init__(self, max_bytes: int) -> None:
        self._max_bytes = max_bytes
        self._frames: OrderedDict[int, np.ndarray] = OrderedDict()
        self._bytes = 0
        self._lock = threading.Lock()

    def get(self, index: int) -> np.ndarray | None:
        with self._lock:
            frame = self._frames.get(index)
            if frame is not None:
                self._frames.move_to_end(index)
            return frame

    def put(self, index: int, frame: np.ndarray) -> None:
        with self._lock:
            existing = self._frames.pop(index, None)
            if existing is not None:
                self._bytes -= existing.nbytes
            self._frames[index] = frame
            self._bytes += frame.nbytes
            while self._bytes > self._max_bytes and self._frames:
                _, evicted = self._frames.popitem(last=False)
                self._bytes -= evicted.nbytes

    def clear(self) -> None:
        with self._lock:
            self._frames.clear()
            self._bytes = 0

    def __contains__(self, index: int) -> bool:
        with self._lock:
            return index in self._frames

    def __len__(self) -> int:
        with self._lock:
            return len(self._frames)


class DecoderThread:
    """Background decode-ahead with latest-wins coalescing, one file, one thread.

    [INTENT] Owns a private `VideoReader` over the same path rather than
    sharing the caller's: `VideoReader` documents itself as not thread-safe
    because one `VideoCapture` handle has one position, and a second reader is
    the mechanism `ARCHITECTURE.md` 5.5 names for the decoder thread, not a
    lock on the first one.

    [INTENT] "Latest-wins" is the part that makes a fast slider drag feel
    live rather than laggy. At an ~8.8 ms measured decode, a drag that emits
    many `valueChanged` events faster than that queues a backlog on whichever
    thread processes them; queuing every intermediate target makes the image
    trail the mouse by however many stale frames are still pending. `request`
    replaces the pending target instead of enqueuing alongside it, so the
    thread is always working toward wherever the slider is now, and a frame
    for an abandoned target is dropped by the caller rather than painted late.
    """

    def __init__(
        self,
        path: Path | str,
        ring: FrameRingBuffer,
        *,
        on_frame: Callable[[int, np.ndarray], None] | None = None,
        on_error: Callable[[int, str], None] | None = None,
        lookahead: int = 8,
    ) -> None:
        self._path = path
        self._ring = ring
        self._on_frame = on_frame
        self._on_error = on_error
        self._lookahead = lookahead
        self._target: int | None = None
        self._stop = threading.Event()
        self._wake = threading.Condition()
        self._thread = threading.Thread(target=self._run, name="sieve-decoder", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def request(self, index: int) -> None:
        """Replace the pending target. Does not block, does not queue."""
        with self._wake:
            self._target = index
            self._wake.notify()

    def stop(self, *, timeout: float | None = 2.0) -> None:
        self._stop.set()
        with self._wake:
            self._wake.notify()
        self._thread.join(timeout=timeout)

    def _take_target(self) -> int | None:
        with self._wake:
            while self._target is None and not self._stop.is_set():
                self._wake.wait()
            index = self._target
            self._target = None
            return index

    def _target_changed(self) -> bool:
        with self._wake:
            return self._target is not None

    def _run(self) -> None:
        try:
            reader = VideoReader(self._path)
        except VideoOpenError:
            return
        try:
            while not self._stop.is_set():
                index = self._take_target()
                if index is None or self._stop.is_set():
                    continue
                frame = self._ring.get(index)
                if frame is None:
                    try:
                        frame = reader.read(index)
                    except VideoReadError as exc:
                        if self._on_error is not None:
                            self._on_error(index, str(exc))
                        continue
                    self._ring.put(index, frame)
                if self._on_frame is not None:
                    self._on_frame(index, frame)
                self._prefetch_forward(reader, index)
        finally:
            reader.close()

    def _prefetch_forward(self, reader: VideoReader, from_index: int) -> None:
        """Opportunistic read-ahead, abandoned the instant a new target arrives.

        This is the ring buffer's fill path for the adjacent-scrub and
        playback cases: a slow drag or a play command requests frames the
        prefetch already reached, which is a `FrameRingBuffer.get` hit instead
        of a decode.
        """
        for offset in range(1, self._lookahead + 1):
            if self._target_changed() or self._stop.is_set():
                return
            next_index = from_index + offset
            if next_index in self._ring:
                continue
            try:
                frame = reader.read(next_index)
            except VideoReadError:
                return
            self._ring.put(next_index, frame)
