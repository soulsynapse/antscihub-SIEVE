from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter
from PyQt6.QtWidgets import QWidget


class IsolatePlayer(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(480, 300)
        self.image: QImage | None = None
        self._frame_bytes: bytes | None = None
        self.frame_size = (1, 1)
        self.message = (
            "Open footage in Replicates or use File > Open to begin."
        )

    def set_frame(self, raw: bytes, width: int, height: int) -> None:
        image = QImage(
            raw, width, height, width * 3, QImage.Format.Format_RGB888
        )
        self._frame_bytes = raw
        self.image = image
        self.frame_size = (width, height)
        self.message = ""
        self.update()

    def clear(self, message: str = "Loading video...") -> None:
        self.image = None
        self._frame_bytes = None
        self.frame_size = (1, 1)
        self.message = message
        self.update()

    def image_rect(self) -> QRectF:
        available = QRectF(self.rect())
        width, height = self.frame_size
        scale = min(available.width() / width, available.height() / height)
        drawn_width, drawn_height = width * scale, height * scale
        return QRectF(
            (available.width() - drawn_width) / 2,
            (available.height() - drawn_height) / 2,
            drawn_width,
            drawn_height,
        )

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#12151a"))
        if self.image is None:
            painter.setPen(QColor("#aab2bf"))
            painter.drawText(
                self.rect(), Qt.AlignmentFlag.AlignCenter, self.message
            )
            return
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawImage(self.image_rect(), self.image)
