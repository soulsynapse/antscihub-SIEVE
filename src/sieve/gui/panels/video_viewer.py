"""Naive-seek video viewer widget (`ARCHITECTURE.md` 5.5).

[INTENT] Scope for this landing: open a file, scrub with a slider, repaint.
Every scrub is one `VideoReader.read(index)` call -- no ring buffer, no
keyframe index, no decoder thread. Section 5.5 asks for all three; NOTES.md
defers them until repaint cost is measured against this shape, because tuning
a buffering policy before there is a widget to measure it against means tuning
it against a guess.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent, QImage, QPixmap, QResizeEvent
from PySide6.QtWidgets import QLabel, QSlider, QVBoxLayout, QWidget

from sieve.io.video_read import VideoReader, VideoReadError

_BGR_CHANNELS = 3


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


class VideoViewer(QWidget):
    """Scrub a video file. Naive index-seek: one `VideoReader.read()` per move.

    Not thread-safe, for the reason `VideoReader` gives for itself: one
    reader, one handle position, one caller.
    """

    positionChanged = Signal(int)  # noqa: N815 -- Qt's signal-naming convention
    scrubError = Signal(str)  # noqa: N815 -- Qt's signal-naming convention

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._reader: VideoReader | None = None
        self._current_index: int | None = None

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

    def open(self, path: Path | str) -> None:
        """Open a file and display its first frame.

        Replaces whatever was open first: `VideoReader` holds one OS handle
        per instance, and opening a second one before releasing the first
        leaks it.
        """
        self.close_video()
        self._reader = VideoReader(path)
        frame_count = self._reader.info.frame_count
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
        self._show_frame(0)

    def close_video(self) -> None:
        if self._reader is not None:
            self._reader.close()
            self._reader = None
        self._current_index = None
        self._frame_label.setText("No video open.")
        self._frame_label.setPixmap(QPixmap())
        self._slider.setEnabled(False)

    def _on_slider_moved(self, index: int) -> None:
        self._show_frame(index)
        self.positionChanged.emit(index)

    def _show_frame(self, index: int) -> None:
        if self._reader is None:
            return
        try:
            frame = self._reader.read(index)
        except VideoReadError as exc:
            # A slot that lets this propagate takes the whole app down with
            # it -- PySide6 does not catch a Python exception raised from a
            # connected slot, it terminates. A rejected seek or an empty
            # decode (the ADR-018 failure mode `FrameReadError` names) has to
            # leave the previous frame on screen and say so, not crash the
            # scrub that triggered it.
            self.scrubError.emit(str(exc))
            return
        self._current_index = index
        self._paint(frame)

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
        # Rescales against the last decoded frame rather than re-reading it, so
        # a window resize costs a scale, not a seek.
        if self._reader is not None and self._current_index is not None:
            try:
                frame = self._reader.read(self._current_index)
            except VideoReadError as exc:
                self.scrubError.emit(str(exc))
            else:
                self._paint(frame)
        super().resizeEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 -- Qt override
        self.close_video()
        super().closeEvent(event)
