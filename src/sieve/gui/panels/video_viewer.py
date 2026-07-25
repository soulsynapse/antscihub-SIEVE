"""Video viewer widget: buffered scrub over the decode boundary (`ARCHITECTURE.md` 5.5).

Eager head-decode paints the first frame synchronously on open, then a
background `DecoderThread` prefetches forward into a `FrameRingBuffer` and
services subsequent scrubs with latest-wins coalescing -- a fast drag replaces
its pending target rather than queuing behind it, so the display tracks where
the slider is now rather than trailing through every intermediate value. A
second background thread builds the file's `KeyframeIndex` without blocking
display. All three primitives live in `sieve.io.video_read`, Qt-free; this
module is the one place their result crosses onto the GUI thread.

[STABLE] The frame-ready crossing uses a `QObject` bridge (`_FrameReadyBridge`)
rather than a raw callback into widget state: `DecoderThread` calls it from its
own thread, and Qt queues a signal emitted across thread affinity onto the
receiver's thread automatically, which is the mechanism that makes touching
`QLabel` from a decode thread safe without an explicit lock here.
"""

from __future__ import annotations

import threading
from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QCloseEvent, QImage, QPixmap, QResizeEvent
from PySide6.QtWidgets import QLabel, QSlider, QVBoxLayout, QWidget

from sieve.io.video_read import (
    DecoderThread,
    FrameRingBuffer,
    KeyframeIndex,
    VideoReader,
    VideoReadError,
    build_keyframe_index,
)

_BGR_CHANNELS = 3

# Byte-budgeted per `FrameRingBuffer`'s own reasoning: capped at 128 MB or 32
# frames' worth of the open file, whichever is smaller, so an HD source (~6.2
# MB/frame) does not silently grow the cache past a modest fraction of RAM.
_RING_BUDGET_CAP_BYTES: int = 128 * 1024 * 1024
_RING_BUDGET_FRAMES: int = 32
_PREFETCH_LOOKAHEAD: int = 8


def _frame_to_pixmap(frame: np.ndarray) -> QPixmap:
    """BGR uint8, ADR-018's delivered format, to a paintable QPixmap.

    `QPixmap.fromImage` copies, which matters here: `QImage` does not copy its
    buffer by default, so it would otherwise point into `frame` after this
    function returns it to a caller who is free to let `frame` go.
    """
    frame = np.ascontiguousarray(frame)
    height, width, channels = frame.shape
    if channels != _BGR_CHANNELS:
        raise ValueError(f"Expected a {_BGR_CHANNELS}-channel BGR frame, got shape {frame.shape}.")
    image = QImage(frame.data, width, height, frame.strides[0], QImage.Format.Format_BGR888)
    return QPixmap.fromImage(image)


class _FrameReadyBridge(QObject):
    """Crosses `DecoderThread`'s callback thread onto the GUI thread.

    `DecoderThread` and `KeyframeIndex` building are plain-callback,
    Qt-free code in `sieve.io.video_read` by design (`bench/` set the
    precedent NOTES.md records for keeping non-`gui/` layers free of Qt).
    This is the one object on the GUI side of that boundary: emitting a
    signal from a foreign thread is safe in Qt, and a direct (default
    auto) connection to a receiver living on the GUI thread queues the slot
    call onto that thread's event loop instead of running it inline.
    """

    frameReady = Signal(int, object)  # noqa: N815 -- Qt's signal-naming convention
    frameError = Signal(int, str)  # noqa: N815 -- Qt's signal-naming convention
    keyframeIndexReady = Signal(object)  # noqa: N815 -- Qt's signal-naming convention

    def notify_frame(self, index: int, frame: np.ndarray) -> None:
        self.frameReady.emit(index, frame)

    def notify_error(self, index: int, message: str) -> None:
        self.frameError.emit(index, message)

    def notify_keyframe_index(self, index: KeyframeIndex) -> None:
        self.keyframeIndexReady.emit(index)


def _ring_budget_bytes(width: int, height: int) -> int:
    frame_bytes = width * height * _BGR_CHANNELS
    return min(_RING_BUDGET_CAP_BYTES, frame_bytes * _RING_BUDGET_FRAMES)


class VideoViewer(QWidget):
    """Scrub a video file against a buffered, decoder-thread-backed source.

    The first frame paints synchronously on open (eager head-decode). Every
    scrub after that goes through `DecoderThread`: a `FrameRingBuffer` hit
    paints immediately, a miss requests an async decode and leaves the
    previous frame on screen until it (or a later, superseding request)
    arrives. `VideoReader` itself stays single-caller; the decoder thread and
    the keyframe-index builder each own a private reader over the same path.
    """

    positionChanged = Signal(int)  # noqa: N815 -- Qt's signal-naming convention
    scrubError = Signal(str)  # noqa: N815 -- Qt's signal-naming convention

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._reader: VideoReader | None = None
        self._current_index: int | None = None
        self._current_frame: np.ndarray | None = None
        self._ring: FrameRingBuffer | None = None
        self._decoder_thread: DecoderThread | None = None
        self._keyframe_index: KeyframeIndex | None = None
        self._keyframe_cancel = threading.Event()
        self._keyframe_thread: threading.Thread | None = None

        self._bridge = _FrameReadyBridge()
        self._bridge.frameReady.connect(self._on_frame_ready)
        self._bridge.frameError.connect(self._on_frame_error)
        self._bridge.keyframeIndexReady.connect(self._on_keyframe_index_ready)

        self._frame_label = QLabel("No video open.")
        self._frame_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._frame_label.setMinimumSize(320, 180)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setEnabled(False)
        self._slider.valueChanged.connect(self._on_slider_moved)

        layout = QVBoxLayout(self)
        layout.addWidget(self._frame_label)
        layout.addWidget(self._slider)

    @property
    def reader(self) -> VideoReader | None:
        return self._reader

    @property
    def keyframe_index(self) -> KeyframeIndex | None:
        """`None` until the background build finishes; see ARCHITECTURE.md 5.5."""
        return self._keyframe_index

    def open(self, path: Path | str) -> None:
        """Open a file, paint its first frame, and start background buffering.

        Replaces whatever was open first: `VideoReader` holds one OS handle
        per instance, and opening a second one before releasing the first
        leaks it.
        """
        self.close_video()
        self._reader = VideoReader(path)
        info = self._reader.info
        frame_count = info.frame_count
        self._slider.blockSignals(True)
        if frame_count is not None and frame_count > 0:
            self._slider.setRange(0, frame_count - 1)
            self._slider.setEnabled(True)
        else:
            # SourceInfo already documents an unknown frame count as
            # sequential-only; index-based scrubbing has nothing to scrub.
            self._slider.setRange(0, 0)
            self._slider.setEnabled(False)
        self._slider.setValue(0)
        self._slider.blockSignals(False)

        self._ring = FrameRingBuffer(_ring_budget_bytes(info.width, info.height))
        try:
            frame = self._reader.read(0)
        except VideoReadError as exc:
            self.scrubError.emit(str(exc))
        else:
            self._current_index = 0
            self._current_frame = frame
            self._ring.put(0, frame)
            self._paint(frame)

        if frame_count is not None and frame_count > 0:
            self._decoder_thread = DecoderThread(
                path,
                self._ring,
                on_frame=self._bridge.notify_frame,
                on_error=self._bridge.notify_error,
                lookahead=_PREFETCH_LOOKAHEAD,
            )
            self._decoder_thread.start()

            self._keyframe_cancel.clear()
            self._keyframe_thread = threading.Thread(
                target=self._build_keyframe_index,
                args=(path,),
                name="sieve-keyframe-index",
                daemon=True,
            )
            self._keyframe_thread.start()

    def _build_keyframe_index(self, path: Path | str) -> None:
        index = build_keyframe_index(path, cancelled=self._keyframe_cancel.is_set)
        if index is not None:
            self._bridge.notify_keyframe_index(index)

    def close_video(self) -> None:
        if self._decoder_thread is not None:
            self._decoder_thread.stop()
            self._decoder_thread = None
        self._keyframe_cancel.set()
        if self._keyframe_thread is not None:
            self._keyframe_thread.join(timeout=2.0)
            self._keyframe_thread = None
        self._keyframe_index = None
        if self._reader is not None:
            self._reader.close()
            self._reader = None
        self._ring = None
        self._current_index = None
        self._current_frame = None
        self._frame_label.setText("No video open.")
        self._frame_label.setPixmap(QPixmap())
        self._slider.setEnabled(False)

    def _on_slider_moved(self, index: int) -> None:
        if self._ring is not None:
            cached = self._ring.get(index)
            if cached is not None:
                self._current_index = index
                self._current_frame = cached
                self._paint(cached)
        if self._decoder_thread is not None:
            self._decoder_thread.request(index)
        self.positionChanged.emit(index)

    def _on_frame_ready(self, index: int, frame: np.ndarray) -> None:
        # Latest-wins on the receiving side too: a decode for a target the
        # slider has since moved past is dropped rather than painted, which
        # is what keeps a fast drag from visibly rewinding to a stale frame.
        if index != self._slider.value():
            return
        self._current_index = index
        self._current_frame = frame
        self._paint(frame)

    def _on_frame_error(self, index: int, message: str) -> None:
        if index != self._slider.value():
            return
        self.scrubError.emit(message)

    def _on_keyframe_index_ready(self, index: KeyframeIndex) -> None:
        self._keyframe_index = index

    def _paint(self, frame: np.ndarray) -> None:
        pixmap = _frame_to_pixmap(frame)
        self._frame_label.setPixmap(
            pixmap.scaled(
                self._frame_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 -- Qt override
        # Rescales against the last decoded frame instead of re-reading it, so
        # a window drag costs a scale per event, not a decode.
        if self._current_frame is not None:
            self._paint(self._current_frame)
        super().resizeEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 -- Qt override
        self.close_video()
        super().closeEvent(event)
