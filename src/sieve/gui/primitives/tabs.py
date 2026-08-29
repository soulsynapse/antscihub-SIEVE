"""Horizontal tab row: section names across the top, one open at a time."""

from __future__ import annotations

from typing import Sequence

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from sieve.gui import metrics, palette
from sieve.gui.palette import ACCENT, DIM, LINE, TEXT
from sieve.gui.primitives.field import RADIUS, RING_W, ring
from sieve.gui.primitives.nav import MARK_W

_PAD_X = 12
_PAD_Y = 8
_GAP = 2


class Tabs(QWidget):
    """Row of section names; emits which one is open. Presentation only."""

    chosen = Signal(int)

    def __init__(
        self,
        names: Sequence[str],
        current: int = 0,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("tabs")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)

        self._names = list(names)
        self._current = max(0, min(len(self._names) - 1, current)) if self._names else -1
        self._hover = -1

        self._refont()
        # Bound methods so PySide6 drops the connection when the receiver dies.
        palette.CHANGED.connect(self.update)
        metrics.CHANGED.connect(self._refont)

    def current(self) -> int:
        """The section open, or -1 while there are none."""
        return self._current

    def select(self, index: int) -> None:
        """Open a section; out-of-range indices are silently ignored."""
        if not 0 <= index < len(self._names) or index == self._current:
            return
        self._current = index
        self.update()
        self.chosen.emit(index)

    def step(self, delta: int) -> None:
        """Move `delta` tabs, clamped to the ends (no wrap)."""
        if not self._names:
            return
        self.select(max(0, min(len(self._names) - 1, self._current + delta)))

    def sizeHint(self) -> QSize:
        spans = self._spans()
        width = int(spans[-1][0] + spans[-1][1]) if spans else 0
        return QSize(width, self._row_height())

    def minimumSizeHint(self) -> QSize:
        return QSize(0, self._row_height())

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            self.step(-1 if key == Qt.Key.Key_Left else +1)
            event.accept()
            return
        super().keyPressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        self._set_hover(self._at(event.position().x()))
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self._set_hover(-1)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            index = self._at(event.position().x())
            if index >= 0:
                self.select(index)
                event.accept()
                return
        super().mousePressEvent(event)

    def _set_hover(self, index: int) -> None:
        if index == self._hover:
            return
        self._hover = index
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if index >= 0 else Qt.CursorShape.ArrowCursor
        )
        self.update()

    def _refont(self) -> None:
        font = self.font()
        font.setPointSize(metrics.pt("name"))
        self.setFont(font)
        self.setFixedHeight(self._row_height())
        self.updateGeometry()
        self.update()

    def _row_height(self) -> int:
        # Mark space is always reserved so labels don't shift on selection change.
        return self.fontMetrics().height() + 2 * _PAD_Y + MARK_W

    def _spans(self) -> list[tuple[float, float]]:
        text = self.fontMetrics()
        spans: list[tuple[float, float]] = []
        x = 0.0
        for name in self._names:
            width = text.horizontalAdvance(name) + 2 * _PAD_X
            spans.append((x, width))
            x += width + _GAP
        return spans

    def _at(self, x: float) -> int:
        for index, (left, width) in enumerate(self._spans()):
            if left <= x <= left + width:
                return index
        return -1

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setFont(self.font())

        floor = self.height() - MARK_W / 2
        painter.setPen(QPen(LINE, MARK_W))
        painter.drawLine(QPointF(0, floor), QPointF(self.width(), floor))

        for index, (left, width) in enumerate(self._spans()):
            box = QRectF(left, 0, width, self.height() - MARK_W)
            lit = index == self._current
            painter.setPen(QPen(TEXT if lit or index == self._hover else DIM))
            painter.drawText(box, int(Qt.AlignmentFlag.AlignCenter), self._names[index])
            if not lit:
                continue
            painter.setPen(QPen(ACCENT, MARK_W))
            painter.drawLine(QPointF(left, floor), QPointF(left + width, floor))
            if self.hasFocus():
                inset = RING_W / 2
                painter.setPen(QPen(ring(), RING_W))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(
                    box.adjusted(inset, inset, -inset, -inset), RADIUS, RADIUS
                )
        painter.end()
