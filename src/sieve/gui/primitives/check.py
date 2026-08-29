"""Painted checkbox and radio — one class, distinguished by corner shape."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QAbstractButton, QSizePolicy, QWidget

from sieve.gui import metrics, palette
from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, PANEL_HOT, TEXT, mix
from sieve.gui.primitives.button import HOVER
from sieve.gui.primitives.field import EDGE, EDGE_HOVER, RING_W, ring

# Fixed, not font-relative; own radius, not metrics.radius() (that's card corners).
_BOX = 14
_RADIUS = 3
_DOT = 3.0

_ROOM = RING_W

_GAP = 8

_TICK_W = 1.8


class Check(QAbstractButton):
    """Painted box with label — square checkbox or round radio (via `autoExclusive`)."""

    def __init__(
        self,
        text: str = "",
        *,
        radio: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setText(text)
        self._radio = radio
        self._hovered = False
        self.setCheckable(True)
        self.setAutoExclusive(radio)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._resize()
        # Bound methods so PySide6 drops the connection when the receiver dies.
        palette.CHANGED.connect(self.update)
        metrics.CHANGED.connect(self._resize)

    def is_radio(self) -> bool:
        return self._radio

    def sizeHint(self) -> QSize:
        text = self.fontMetrics()
        width = _ROOM + _BOX + _ROOM
        if self.text():
            width += _GAP + text.horizontalAdvance(self.text())
        return QSize(width, max(_BOX + 2 * _ROOM, text.height()))

    def minimumSizeHint(self) -> QSize:
        return QSize(_ROOM + _BOX + _ROOM, max(_BOX + 2 * _ROOM, self.fontMetrics().height()))

    def _resize(self) -> None:
        font = self.font()
        font.setPointSize(metrics.pt("name"))
        self.setFont(font)
        self.updateGeometry()
        self.update()

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Inset 0.5px so a 1px pen doesn't clip at the widget edge.
        top = (self.height() - _BOX) / 2
        box = QRectF(_ROOM, top, _BOX, _BOX).adjusted(0.5, 0.5, -0.5, -0.5)
        corner = _BOX if self._radio else _RADIUS
        shape = QPainterPath()
        shape.addRoundedRect(box, corner, corner)

        if self.hasFocus():
            inset = RING_W / 2
            painter.setPen(QPen(ring(), RING_W))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(
                box.adjusted(-inset, -inset, inset, inset),
                corner + inset,
                corner + inset,
            )

        painter.fillPath(shape, self._fill())
        painter.setPen(QPen(self._edge(), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(shape)

        if self.isChecked():
            self._mark(painter, box)

        if self.text():
            painter.setPen(QPen(TEXT if self.isEnabled() else DIM))
            painter.drawText(
                QRectF(_ROOM + _BOX + _GAP, 0, self.width(), self.height()),
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                self.text(),
            )
        painter.end()

    def _mark(self, painter: QPainter, box: QRectF) -> None:
        ink = PANEL if self.isEnabled() else DIM
        if self._radio:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(ink)
            painter.drawEllipse(box.center(), _DOT, _DOT)
            return
        side = box.width()
        tick = QPainterPath(QPointF(box.left() + side * 0.24, box.top() + side * 0.52))
        tick.lineTo(box.left() + side * 0.42, box.top() + side * 0.72)
        tick.lineTo(box.left() + side * 0.77, box.top() + side * 0.30)
        pen = QPen(ink, _TICK_W)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(tick)

    def _fill(self) -> QColor:
        if not self.isEnabled():
            return PANEL_HOT
        if not self.isChecked():
            return PANEL
        return mix(ACCENT, TEXT, HOVER) if self._hovered else ACCENT

    def _edge(self) -> QColor:
        if not self.isEnabled():
            return LINE
        if self.isChecked():
            return self._fill()
        return mix(LINE, TEXT, EDGE_HOVER if self._hovered else EDGE)
