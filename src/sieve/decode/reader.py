"""OpenCV `VideoCapture` wrapper with a seek strategy tuned by measurement.

DECISION: seek accuracy is chosen over source bit-depth preservation. Frames
come back as 8-bit BGR because that is what `VideoCapture` gives us and what
the cache key assumes; a high-bit-depth path would be a separate reader.

The seek strategy exists because of a lopsided cost profile, measured on a
5312x2988 59.94 fps H.264 source:

    grab()                     ~1.3 ms   (demux + decode, no colour convert)
    retrieve()                ~29 ms     (YUV -> BGR convert and copy)
    CAP_PROP_POS_FRAMES seek  ~50 ms     (before any retrieve)

Almost all the per-frame cost is the colour conversion, and stepping forward
without converting is nearly free. So a short forward jump is served by
grabbing through the gap rather than seeking: below `GRAB_FORWARD_LIMIT`
frames that is strictly cheaper than asking the container to seek, and it also
avoids the keyframe-rounding errors that make `POS_FRAMES` unreliable on some
codecs.
"""

from __future__ import annotations

from pathlib import Path
from types import TracebackType
from typing import Any, Self

import cv2
import numpy as np
from numpy.typing import NDArray

from sieve.core.types import ChannelSpec, Frame, VideoMetadata

#: Forward jumps shorter than this are served by grabbing through the gap.
#: Derived from measurement: seek cost / grab cost on the reference source.
GRAB_FORWARD_LIMIT = 40


class VideoDecodeError(RuntimeError):
    """Raised when a video cannot be opened, or a requested frame cannot be read."""


class VideoReader:
    """Random-access frame reader over a single video file.

    Not thread-safe: one reader belongs to one thread. The GUI keeps its
    reader on a dedicated decode thread for exactly this reason.
    """

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        if not self._path.is_file():
            raise VideoDecodeError(f"No such video file: {self._path}")

        self._capture = cv2.VideoCapture(str(self._path))
        if not self._capture.isOpened():
            raise VideoDecodeError(f"Could not open video: {self._path}")

        self._metadata = self._read_metadata()
        if self._metadata.frame_count <= 0:
            self._capture.release()
            raise VideoDecodeError(f"Video reports no frames: {self._path}")

        # Index of the frame the capture will return next.
        self._cursor = 0

    def _read_metadata(self) -> VideoMetadata:
        return VideoMetadata(
            path=self._path,
            width=int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            height=int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            fps=float(self._capture.get(cv2.CAP_PROP_FPS)),
            frame_count=int(self._capture.get(cv2.CAP_PROP_FRAME_COUNT)),
        )

    @property
    def metadata(self) -> VideoMetadata:
        """Container-reported properties of the open file."""
        return self._metadata

    @property
    def is_open(self) -> bool:
        """Whether the underlying capture is still usable."""
        return self._capture.isOpened()

    def read(self, index: int, max_width: int | None = None) -> Frame:
        """Decode the frame at `index`.

        `max_width` requests a proxy: the frame is downscaled on the way out if
        it is wider than the limit. This is decode-side proxy media in the
        video-editor sense — a cheaper representation of the *same* frame for
        display — not a downsampling filter. Filters that trade resolution for
        economy are pipeline nodes and record themselves in the DAG; this does
        not, and must never feed anything but a viewport.

        Raises:
            VideoDecodeError: if the frame cannot be read.
        """
        if not 0 <= index < self._metadata.frame_count:
            raise VideoDecodeError(
                f"Frame {index} out of range 0..{self._metadata.frame_count - 1}"
            )

        self._position_at(index)
        ok, data = self._capture.read()
        if not ok or data is None:
            self._cursor = -1  # Position is now unknown; force a seek next time.
            raise VideoDecodeError(f"Failed to decode frame {index} of {self._path}")
        self._cursor = index + 1

        return Frame(
            data=_downscale(data, max_width),
            index=index,
            channels=ChannelSpec.BGR,
        )

    def _position_at(self, index: int) -> None:
        """Make the capture's next read return frame `index`."""
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
        """Release the capture. Idempotent."""
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


def _downscale(data: NDArray[Any], max_width: int | None) -> NDArray[np.uint8]:
    """Area-resample `data` down to `max_width` if it is wider. Never upscales."""
    source_height, source_width = data.shape[:2]
    if max_width is None or source_width <= max_width:
        return data
    scale = max_width / source_width
    target = (max_width, max(round(source_height * scale), 1))
    return cv2.resize(data, target, interpolation=cv2.INTER_AREA)
