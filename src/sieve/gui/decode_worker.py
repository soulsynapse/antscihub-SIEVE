"""The decode thread: a `VideoReader` that never blocks the event loop.

Decoding one frame of the reference source costs ~29 ms and a random seek
~80 ms. Doing that on the GUI thread would stall repaints, input, and the
undo stack for the duration — the scrub budget is 50 ms, so a blocking reader
misses it on the first frame and every frame after.

So the reader lives here, on a thread of its own, and hands finished
`QImage`s back by queued signal. Colour frames are BGR888 because that is what
OpenCV produces and Qt renders natively; luma frames are Grayscale8 for the
same reason — the reader hands back the Y plane as-is, Qt paints it as-is,
and there is no colour conversion anywhere in the path. (The item that added
the luma path assumed a GRAY2BGR on the way out; `Format_Grayscale8` is the
same result with the convert deleted, and `cv2` stays out of `gui/` as the
import contract requires.)

The format is a property of the *reader*, fixed at capture construction
(`decode/reader.py` says why it is never toggled mid-stream), so `set_luma`
reopens the capture rather than flipping a flag. The caller owns everything
that follows from that: dropping its cache of old-format frames and
re-requesting the frame on screen so the pane never blanks.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QImage

from sieve.core.types import ChannelSpec, VideoMetadata
from sieve.decode.reader import VideoDecodeError, VideoReader

#: Starting proxy width, used until a preference arrives. 1280 is wide enough
#: that the viewport, not the proxy, is the limit on what a user can see, and
#: narrow enough that the resample stays under a millisecond or two. The user
#: can change it; see `gui/preferences.py`.
PROXY_WIDTH = 1280


class DecodeWorker(QObject):
    """Lives on the decode thread. Every slot here runs off the GUI thread."""

    opened = Signal(VideoMetadata)
    failed = Signal(str)
    frame_ready = Signal(int, QImage)

    def __init__(self) -> None:
        super().__init__()
        self._reader: VideoReader | None = None
        self._proxy_width = PROXY_WIDTH
        self._luma = False
        self._path: Path | None = None

    @Slot(int)
    def set_proxy_width(self, width: int) -> None:
        """Change the display decode width. Takes effect on the next frame.

        Frames already delivered keep the width they were decoded at, so the
        caller is responsible for discarding anything it cached.
        """
        self._proxy_width = max(width, 1)

    @Slot(bool)
    def set_luma(self, enabled: bool) -> None:
        """Switch the decode format, reopening the reader if one is open.

        Idempotent, because the caller re-applies preferences wholesale and a
        reopen is one capture's worth of work that must not happen for free.
        `opened` is deliberately not re-emitted — the source did not change,
        and a second `opened` would reset transport state the user still has.
        The caller re-requests the current frame; frames already delivered
        keep the format they were decoded in, exactly as with a width change.
        """
        if enabled == self._luma:
            return
        self._luma = enabled
        if self._reader is None:
            return
        path = self._path
        self._reader.close()
        self._reader = None
        if path is None:
            return
        try:
            self._reader = VideoReader(path, luma=enabled)
        except VideoDecodeError as error:
            self.failed.emit(str(error))

    @Slot(str)
    def open(self, path: str) -> None:
        """Open a video and emit its metadata, or `failed` with the reason."""
        self.close()
        try:
            self._reader = VideoReader(Path(path), luma=self._luma)
        except VideoDecodeError as error:
            self.failed.emit(str(error))
            return
        self._path = Path(path)
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
            frame = reader.read(index, max_width=self._proxy_width)
        except VideoDecodeError as error:
            self.failed.emit(str(error))
            return

        data = frame.data
        if frame.channels is ChannelSpec.GRAY:
            image = QImage(
                data.tobytes(),
                frame.width,
                frame.height,
                frame.width,
                QImage.Format.Format_Grayscale8,
            )
        else:
            image = QImage(
                data.tobytes(),
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
        self._path = None
