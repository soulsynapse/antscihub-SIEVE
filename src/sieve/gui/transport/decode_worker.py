"""The decode thread: a `VideoReader` that never blocks the event loop.

Decoding one frame of the reference source costs tens of milliseconds and a
random seek more; doing that on the GUI thread would stall repaints and input
for the duration, and the scrub budget (`bench/budgets.scrub_to_repaint`) is
missed on the first frame and every frame after.

So the reader lives here, on a thread of its own, and hands finished `QImage`s
back by queued signal. Frames are BGR888 because that is what OpenCV produces
and Qt renders natively, so there is no colour conversion anywhere in the path.

The proxy width is fixed at the constant below. v2 made it a preference and
reopened the reader to switch the decode format; both belong with the surfaces
that set them, and neither exists yet — what does exist is the discipline those
switches obeyed, which the player states where it clears its cache.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QImage

from sieve.core.types import VideoMetadata
from sieve.decode.reader import VideoDecodeError, VideoReader

#: Display decode width. 1280 is wide enough that the viewport, not the proxy,
#: is the limit on what a user can see, and narrow enough that the resample
#: stays under a millisecond or two.
PROXY_WIDTH = 1280


class DecodeWorker(QObject):
    """Lives on the decode thread. Every slot here runs off the GUI thread."""

    opened = Signal(VideoMetadata)
    failed = Signal(str)
    frame_ready = Signal(int, QImage)

    def __init__(self) -> None:
        super().__init__()
        self._reader: VideoReader | None = None

    @Slot(str)
    def open(self, path: str) -> None:
        """Open a video and emit its metadata, or `failed` with the reason."""
        self.close()
        try:
            self._reader = VideoReader(Path(path))
        except VideoDecodeError as error:
            self.failed.emit(str(error))
            return
        self.opened.emit(self._reader.metadata)

    @Slot(int)
    def request_frame(self, index: int) -> None:
        """Decode one frame and emit it.

        The caller is responsible for coalescing: this slot services every
        request it receives, so a scrub that queues faster than decode can
        drain would build an unbounded backlog. `VideoPlayer` keeps at most
        one request in flight for that reason.
        """
        reader = self._reader
        if reader is None:
            return
        try:
            frame = reader.read(index, max_width=PROXY_WIDTH)
        except VideoDecodeError as error:
            self.failed.emit(str(error))
            return

        image = QImage(
            frame.data.tobytes(),
            frame.width,
            frame.height,
            frame.width * 3,
            QImage.Format.Format_BGR888,
        )
        # QImage does not take ownership of the buffer it was handed; copy so
        # the image outlives the numpy array it was built from.
        self.frame_ready.emit(index, image.copy())

    @Slot()
    def close(self) -> None:
        """Release the reader if one is open."""
        if self._reader is not None:
            self._reader.close()
            self._reader = None
