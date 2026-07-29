from __future__ import annotations

from enum import Enum, auto

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal, Slot
from PySide6.QtGui import (
    QColor,
    QFontMetricsF,
    QImage,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
)
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from sieve.core.pipeline_model import ClipRange
from sieve.core.types import VideoMetadata
from sieve.gui.document import ReplicateDocument
from sieve.gui.player import VideoPlayer
from sieve.gui.timeline_model import Geometry, ended_at_handle, moved_to, started_at


STRIP_HEIGHT = 44


_TRACK_INSET = 4.0


_EDGE_GRAB = 6.0


_HEADER_HEIGHT = 9.0


MIN_WINDOW_SECONDS = 1.0

_PLAY_GLYPH = "▶"
_PAUSE_GLYPH = "⏸"

_TRACK = QColor(30, 30, 36)
_WINDOW = QColor(90, 170, 255, 70)
_WINDOW_EDGE = QColor(90, 170, 255)
_WINDOW_HEADER = QColor(90, 170, 255, 110)
_WINDOW_HEADER_HELD = QColor(90, 170, 255, 180)
_PLAYHEAD = QColor(240, 240, 245)


_BUBBLE = QColor(18, 18, 22, 235)
_BUBBLE_EDGE = QColor(80, 84, 96)
_BUBBLE_TEXT = QColor(232, 233, 238)


_BUBBLE_PAD = (8.0, 3.0)

_EMPTY_HINT = "Open a video to begin"


class Grab(Enum):
    SCRUB = auto()

    START = auto()

    END = auto()

    BODY = auto()


def format_timecode(seconds: float) -> str:
    if seconds < 0.0:
        seconds = 0.0
    hours, remainder = divmod(int(seconds), 3600)
    minutes, whole_seconds = divmod(remainder, 60)
    milliseconds = round((seconds - int(seconds)) * 1000) % 1000
    if hours:
        return f"{hours}:{minutes:02d}:{whole_seconds:02d}.{milliseconds:03d}"
    return f"{minutes}:{whole_seconds:02d}.{milliseconds:03d}"


class TimelineStrip(QWidget):
    pressed = Signal(int)

    scrubbed = Signal(int)

    committed = Signal(int)

    window_moved = Signal(int)

    window_resized = Signal(int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._frame_count = 0
        self._fps = 0.0
        self._window: ClipRange | None = None
        self._playhead = 0
        self._dragging = False
        self._draft: ClipRange | None = None
        self._grab: Grab | None = None
        self._grab_offset = 0
        self._hover: int | None = None
        self.setFixedHeight(STRIP_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        self.setMouseTracking(True)

    def set_source_frames(self, frame_count: int) -> None:
        self._frame_count = max(frame_count, 0)
        self.update()

    def set_timebase(self, fps: float) -> None:
        self._fps = max(fps, 0.0)

    def set_window(self, window: ClipRange | None) -> None:
        self._window = window
        self.update()

    def set_playhead(self, frame: int) -> None:
        self._playhead = frame
        self.update()

    def geometry_now(self) -> Geometry:
        return Geometry(frame_count=self._frame_count, width=float(self.width()))

    @property
    def shown_window(self) -> ClipRange | None:
        return self._draft if self._draft is not None else self._window

    @property
    def floor_frames(self) -> int:
        if self._fps <= 0.0:
            return 1
        return max(round(MIN_WINDOW_SECONDS * self._fps), 1)

    def window_rect(self) -> QRectF:
        geometry = self.geometry_now()
        window = self.shown_window
        if window is None or geometry.is_empty:
            return QRectF()
        left, right = geometry.span(window.start, window.end)
        return QRectF(
            left, _TRACK_INSET, right - left, self.height() - 2.0 * _TRACK_INSET
        )

    def header_rect(self) -> QRectF:
        window = self.window_rect()
        if window.isEmpty():
            return QRectF()
        return QRectF(window.left(), window.top(), window.width(), _HEADER_HEIGHT)

    def column_centre(self, frame: int) -> float:
        return self.geometry_now().centre_of_frame(frame)

    def playhead_x(self) -> float:
        return self.column_centre(self._playhead)

    def grab_at(self, position: QPointF) -> Grab:
        window = self.window_rect()
        if window.isEmpty():
            return Grab.SCRUB
        x = position.x()
        if abs(x - window.left()) <= _EDGE_GRAB:
            return Grab.START
        if abs(x - window.right()) <= _EDGE_GRAB:
            return Grab.END
        if self.header_rect().contains(position):
            return Grab.BODY
        return Grab.SCRUB

    @property
    def hover_frame(self) -> int | None:
        return self._hover

    def bubble_text(self) -> str:
        if self._hover is None:
            return ""
        if self._fps <= 0.0:
            return f"frame {self._hover:,}"
        return f"{format_timecode(self._hover / self._fps)}   frame {self._hover:,}"

    def bubble_rect(self) -> QRectF:
        if self._hover is None or self.geometry_now().is_empty:
            return QRectF()
        pad_x, pad_y = _BUBBLE_PAD
        metrics = QFontMetricsF(self.font())
        width = metrics.horizontalAdvance(self.bubble_text()) + 2.0 * pad_x
        height = metrics.height() + 2.0 * pad_y
        left = max(
            min(self.column_centre(self._hover) - width / 2.0, self.width() - width),
            0.0,
        )
        return QRectF(left, _TRACK_INSET + _HEADER_HEIGHT, width, height)

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        track = QRectF(self.rect()).adjusted(0.0, _TRACK_INSET, 0.0, -_TRACK_INSET)
        painter.fillRect(track, _TRACK)
        if self.geometry_now().is_empty:
            painter.setPen(QColor(120, 120, 130))
            painter.drawText(
                track.adjusted(8.0, 0.0, -8.0, 0.0),
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                _EMPTY_HINT,
            )
            painter.end()
            return
        window = self.window_rect()
        if not window.isEmpty():
            painter.fillRect(window, _WINDOW)
            held = self._grab is Grab.BODY
            painter.fillRect(
                self.header_rect(), _WINDOW_HEADER_HELD if held else _WINDOW_HEADER
            )
            edge = 2.0 if self._grab in (Grab.START, Grab.END) else 1.0
            painter.setPen(QPen(_WINDOW_EDGE, edge))
            painter.drawRect(window.adjusted(0.5, 0.5, -0.5, -0.5))
        x = self.playhead_x()
        painter.setPen(QPen(_PLAYHEAD, 1.0))
        painter.drawLine(QPointF(x, 0.0), QPointF(x, float(self.height())))
        self._paint_bubble(painter)
        painter.end()

    def _paint_bubble(self, painter: QPainter) -> None:
        box = self.bubble_rect()
        if box.isEmpty() or self._dragging or self._grab is not None:
            return
        painter.setPen(QPen(_BUBBLE_EDGE, 1.0))
        painter.setBrush(_BUBBLE)
        painter.drawRoundedRect(box, 3.0, 3.0)
        painter.setPen(_BUBBLE_TEXT)
        painter.drawText(
            box,
            int(Qt.AlignmentFlag.AlignCenter),
            self.bubble_text(),
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if (
            self.geometry_now().is_empty
            or event.button() is not Qt.MouseButton.LeftButton
        ):
            return
        grab = self.grab_at(event.position())
        if grab is Grab.SCRUB:
            self._dragging = True
            self.pressed.emit(self.geometry_now().frame_at(event.position().x()))
            return
        window = self.shown_window
        if window is None:
            return
        self._grab = grab
        self._draft = window
        self._grab_offset = (
            self.geometry_now().frame_at(event.position().x()) - window.start
        )
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        position = event.position()
        self._hover = self.geometry_now().frame_at(position.x())
        if self._dragging:
            self.scrubbed.emit(self._hover)
        elif self._grab is not None:
            self._draft = self._dragged_to(position.x())
        else:
            self._follow_cursor(position)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() is not Qt.MouseButton.LeftButton:
            return
        if self._dragging:
            self._dragging = False
            self.committed.emit(self.geometry_now().frame_at(event.position().x()))
            return
        if self._grab is None:
            return
        window = self._dragged_to(event.position().x())
        grab, self._grab, self._draft = self._grab, None, None
        self.update()
        if grab is Grab.BODY:
            self.window_moved.emit(window.start)
        else:
            self.window_resized.emit(window.start, window.end)

    def leaveEvent(self, event: QEvent) -> None:
        del event
        if self._hover is not None:
            self._hover = None
            self.update()

    def _dragged_to(self, x: float) -> ClipRange:
        window = self._draft if self._draft is not None else self._window
        frame = self.geometry_now().frame_at(x)
        if window is None:
            return ClipRange(start=0, end=max(self._frame_count, 1))
        if self._grab is Grab.START:
            return started_at(window, frame, self._frame_count, self.floor_frames)
        if self._grab is Grab.END:
            return ended_at_handle(window, frame, self._frame_count, self.floor_frames)
        return moved_to(window, frame - self._grab_offset, self._frame_count)

    def _follow_cursor(self, position: QPointF) -> None:
        self.setCursor(
            {
                Grab.START: Qt.CursorShape.SizeHorCursor,
                Grab.END: Qt.CursorShape.SizeHorCursor,
                Grab.BODY: Qt.CursorShape.OpenHandCursor,
                Grab.SCRUB: Qt.CursorShape.PointingHandCursor,
            }[self.grab_at(position)]
        )


class TimelineBar(QWidget):
    def __init__(
        self,
        player: VideoPlayer,
        document: ReplicateDocument,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._player = player
        self._document = document
        self._updating = False
        self._strip = TimelineStrip()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 4)
        layout.setSpacing(2)
        layout.addLayout(self._build_controls())
        layout.addWidget(self._strip)
        self._connect()
        self._on_source_changed()

    @property
    def strip(self) -> TimelineStrip:
        return self._strip

    @property
    def window_seconds(self) -> tuple[float, float]:
        return self._start_box.value(), self._length_box.value()

    def _build_controls(self) -> QHBoxLayout:
        self._play_button = QPushButton(_PLAY_GLYPH)
        self._play_button.setFixedWidth(40)
        self._play_button.setToolTip("Play / pause (Space)")
        self._start_box = QDoubleSpinBox()
        self._start_box.setDecimals(2)
        self._start_box.setSingleStep(1.0)
        self._start_box.setSuffix(" s")
        self._start_box.setToolTip("Where the working window starts")
        self._length_box = QDoubleSpinBox()
        self._length_box.setDecimals(2)
        self._length_box.setSingleStep(1.0)
        self._length_box.setSuffix(" s")
        self._length_box.setToolTip("How long the working window is")
        self._timecode = QLabel("—")
        self._timecode.setTextFormat(Qt.TextFormat.PlainText)
        self._timecode.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        row.addStretch(1)
        row.addWidget(self._play_button)
        row.addWidget(QLabel("Window"))
        row.addWidget(self._start_box)
        row.addWidget(QLabel("+"))
        row.addWidget(self._length_box)
        row.addWidget(self._timecode)
        return row

    def _connect(self) -> None:
        self._document.source_changed.connect(self._on_source_changed)
        self._player.frame_changed.connect(self._on_frame_changed)
        self._player.playing_changed.connect(self._on_playing_changed)
        self._play_button.clicked.connect(self._player.toggle_play)
        self._start_box.valueChanged.connect(self._on_start_typed)
        self._length_box.valueChanged.connect(self._on_length_typed)
        self._strip.pressed.connect(self._on_pressed)
        self._strip.scrubbed.connect(self._player.scrub)
        self._strip.committed.connect(self._on_committed)
        self._strip.window_moved.connect(self._document.move_window_to)
        self._strip.window_resized.connect(self._document.place_window)
        self._document.clip_changed.connect(self._on_window_changed)
        self._document.crops_changed.connect(self._on_window_changed)
        self._document.replicate_changed.connect(self._on_window_changed)

    @Slot()
    def _on_source_changed(self) -> None:
        frames = self._document.source_frames
        self._strip.set_source_frames(frames)
        self._strip.set_timebase(self._document.source_fps)
        enabled = frames > 0
        for widget in (
            self._play_button,
            self._start_box,
            self._length_box,
            self._strip,
        ):
            widget.setEnabled(enabled)
        self._on_window_changed()
        self._update_timecode(self._player.current_index if enabled else 0)

    def video_closed(self) -> None:
        self._on_source_changed()

    @Slot()
    def _on_window_changed(self) -> None:
        window = self._document.window
        self._strip.set_window(window)
        self._player.set_window(window)
        self._write_boxes(window)

    def _write_boxes(self, window: ClipRange | None) -> None:
        fps = self._document.source_fps
        frames = self._document.source_frames
        self._updating = True
        try:
            if window is None or fps <= 0.0 or frames <= 0:
                self._start_box.setRange(0.0, 0.0)
                self._length_box.setRange(0.0, 0.0)
                return
            duration = frames / fps
            self._start_box.setRange(0.0, max(duration - 1.0 / fps, 0.0))
            self._start_box.setValue(window.start / fps)
            self._length_box.setRange(1.0 / fps, duration)
            self._length_box.setValue(window.frame_count / fps)
        finally:
            self._updating = False

    @Slot(float)
    def _on_start_typed(self, seconds: float) -> None:
        if self._updating:
            return
        self._document.move_window_to(self._frames_of(seconds))

    @Slot(float)
    def _on_length_typed(self, seconds: float) -> None:
        if self._updating:
            return
        self._document.set_window_length(max(self._frames_of(seconds), 1))

    def _frames_of(self, seconds: float) -> int:
        fps = self._document.source_fps
        if fps <= 0.0:
            return 0
        return round(seconds * fps)

    @Slot(int)
    def _on_pressed(self, frame: int) -> None:
        self._document.bring_window_to(frame)
        self._player.seek(frame)

    @Slot(int)
    def _on_committed(self, frame: int) -> None:
        self._document.bring_window_to(frame)
        self._player.seek(frame)

    @Slot(int, QImage)
    def _on_frame_changed(self, index: int, image: QImage) -> None:
        del image
        self._strip.set_playhead(index)
        self._update_timecode(index)

    @Slot(bool)
    def _on_playing_changed(self, playing: bool) -> None:
        self._play_button.setText(_PAUSE_GLYPH if playing else _PLAY_GLYPH)

    def _update_timecode(self, index: int) -> None:
        metadata: VideoMetadata | None = self._player.metadata
        if metadata is None or self._document.source_frames <= 0:
            self._timecode.setText("—")
            return
        self._timecode.setText(
            f"{format_timecode(metadata.timestamp_of(index))} / "
            f"{format_timecode(metadata.duration_seconds)}   "
            f"frame {index:,} / {metadata.frame_count - 1:,}"
        )
