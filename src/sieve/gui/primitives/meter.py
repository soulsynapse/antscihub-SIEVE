"""Bar drawn as a filled fraction of a groove; shared by card feet and table cells."""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from sieve.gui import palette
from sieve.gui.palette import ACCENT, DIM, LINE

HEIGHT = 4

WIDTH = 84
_MIN_W = 24


def draw(
    painter: QPainter,
    box: QRectF,
    full: float,
    *,
    current: bool = False,
    round_ends: bool = True,
) -> None:
    """Paint a groove across `box` and `full` of it filled."""
    full = max(0.0, min(1.0, full))
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    if round_ends:
        corner = box.height() / 2
        painter.setBrush(LINE)
        painter.drawRoundedRect(box, corner, corner)
        # IntersectClip so a caller's own clip (e.g. card corner) survives.
        painter.setClipRect(
            QRectF(box.left(), box.top(), box.width() * full, box.height()),
            Qt.ClipOperation.IntersectClip,
        )
        painter.setBrush(ACCENT if current else DIM)
        painter.drawRoundedRect(box, corner, corner)
    else:
        painter.fillRect(box, LINE)
        painter.fillRect(
            QRectF(box.left(), box.top(), box.width() * full, box.height()),
            ACCENT if current else DIM,
        )
    painter.restore()


class Meter(QWidget):
    """Free-standing fraction bar. Fixed height; no gestures."""

    def __init__(
        self,
        full: float = 0.0,
        current: bool = False,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._full = full
        self._current = current
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        # Bound method so PySide6 drops the connection when the receiver dies.
        palette.CHANGED.connect(self.update)

    def full(self) -> float:
        return self._full

    def set_full(self, full: float) -> None:
        self._full = max(0.0, min(1.0, full))
        self.update()

    def set_current(self, current: bool) -> None:
        self._current = current
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(WIDTH, HEIGHT)

    def minimumSizeHint(self) -> QSize:
        return QSize(_MIN_W, HEIGHT)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # Inset 0.5px vertically so the rounded ends aren't clipped at the edge.
        box = QRectF(self.rect()).adjusted(0, 0.5, 0, -0.5)
        draw(painter, box, self._full, current=self._current)
        painter.end()
