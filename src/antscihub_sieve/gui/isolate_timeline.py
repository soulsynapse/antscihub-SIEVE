from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget


class IsolateTimeline(QWidget):
    frame_clicked = pyqtSignal(int)

    def __init__(self) -> None:
        super().__init__()
        self.frame_count = 0
        self.window_start = 0
        self.window_stop = 0
        self.current_frame = 0
        self._scrubbing = False
        self.setMinimumHeight(72)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

    def set_state(
        self, frame_count: int, start: int, stop: int, current: int
    ) -> None:
        self.frame_count = frame_count
        self.window_start = start
        self.window_stop = stop
        self.current_frame = current
        self.update()

    def content_rect(self) -> QRectF:
        return QRectF(8, 20, max(1, self.width() - 16), 32)

    def boundary_to_x(self, boundary: int) -> float:
        track = self.content_rect()
        if self.frame_count <= 0:
            return track.left()
        return track.left() + track.width() * boundary / self.frame_count

    def frame_to_x(self, frame: int) -> float:
        if self.frame_count <= 0:
            return self.content_rect().left()
        return self.boundary_to_x(min(self.frame_count, max(0, frame) + 0.5))

    def x_to_frame(self, x: float) -> int:
        if self.frame_count <= 0:
            return 0
        track = self.content_rect()
        fraction = (x - track.left()) / track.width()
        return min(
            self.frame_count - 1,
            max(0, int(fraction * self.frame_count)),
        )

    def window_rect(self) -> QRectF:
        track = self.content_rect()
        left = self.boundary_to_x(self.window_start)
        right = self.boundary_to_x(self.window_stop)
        return QRectF(left, track.top(), max(1, right - left), track.height())

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().window())
        track = self.content_rect()
        painter.setPen(QPen(QColor("#5b6573"), 1))
        painter.setBrush(QColor("#20252d"))
        painter.drawRoundedRect(track, 4, 4)
        if self.frame_count <= 0:
            painter.setPen(QColor("#8993a1"))
            painter.drawText(
                track, Qt.AlignmentFlag.AlignCenter, "No asset open"
            )
            return
        painter.setPen(QPen(QColor("#60a5fa"), 1))
        painter.setBrush(QColor("#2563eb"))
        painter.drawRoundedRect(self.window_rect(), 3, 3)
        cursor_x = self.frame_to_x(self.current_frame)
        painter.setPen(QPen(QColor("#fbbf24"), 2))
        painter.drawLine(
            int(cursor_x), int(track.top() - 6),
            int(cursor_x), int(track.bottom() + 6),
        )
        painter.setPen(self.palette().text().color())
        painter.drawText(8, 14, "Whole asset")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self.frame_count > 0
        ):
            self._scrubbing = True
            self.frame_clicked.emit(self.x_to_frame(event.position().x()))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._scrubbing and self.frame_count > 0:
            self.frame_clicked.emit(self.x_to_frame(event.position().x()))

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._scrubbing = False
