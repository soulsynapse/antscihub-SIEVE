"""Full-width status block: mark, stripe, title, and optional body."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from sieve.gui import metrics, palette
from sieve.gui.palette import ACCENT, DIM, LINE, PANEL_HOT, TEXT, rgb

NOTE = "note"
WARN = "warn"
FAIL = "fail"
DONE = "done"

# Distinct from nav.MARK_W — selection vs. status; the two move independently.
_STRIPE = 3

_PAD_X = 12
_PAD_Y = 10

# Fixed, not font-relative — air around the mark stays constant at every size.
_MARK = 14
_MARK_GAP = 10

_STROKE = 1.6
_INSET = 0.26

_LEAD = 2


def sheet() -> str:
    """Label rules for callers that set an ancestor sheet (which would override these)."""
    return f"""
        #bannertitle {{
            color: {rgb(TEXT)};
            background: transparent;
            border: 0;
        }}
        #bannerbody {{
            color: {rgb(DIM)};
            background: transparent;
            border: 0;
        }}
    """


class Banner(QWidget):
    """Painted status block: stripe, mark, title, and optional body. No gestures."""

    def __init__(
        self,
        title: str = "",
        body: str = "",
        kind: str = NOTE,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._kind = kind
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._title = QLabel(title)
        self._title.setObjectName("bannertitle")
        self._title.setWordWrap(False)

        self._body = QLabel(body)
        self._body.setObjectName("bannerbody")
        self._body.setWordWrap(True)
        self._body.setVisible(bool(body))

        column = QVBoxLayout(self)
        column.setContentsMargins(
            _STRIPE + _PAD_X + _MARK + _MARK_GAP,
            _PAD_Y,
            _PAD_X,
            _PAD_Y,
        )
        column.setSpacing(_LEAD)
        column.addWidget(self._title)
        column.addWidget(self._body)

        policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)

        self._resize()
        self.setStyleSheet(sheet())
        # Bound methods so PySide6 drops the connection when the receiver dies.
        palette.CHANGED.connect(self._restyle)
        metrics.CHANGED.connect(self._resize)

    def state(self) -> tuple[str, str, str]:
        """Return (title, body, kind)."""
        return self._title.text(), self._body.text(), self._kind

    def set_message(self, title: str, body: str, kind: str) -> None:
        """Replace all three at once to avoid a frame with mismatched mark."""
        self._title.setText(title)
        self._body.setText(body)
        self._body.setVisible(bool(body))
        self._kind = kind
        self.updateGeometry()
        self.update()

    def heightForWidth(self, width: int) -> int:
        # Layout returns -1 (no opinion) when there's no wrapping body; fall
        # back to sizeHint so a bare-title banner still gets a positive height.
        height = self.layout().heightForWidth(width)
        return height if height >= 0 else self.sizeHint().height()

    def _restyle(self) -> None:
        self.setStyleSheet(sheet())
        self.update()

    def _resize(self) -> None:
        title = self._title.font()
        title.setPointSize(metrics.pt("name"))
        title.setBold(True)
        self._title.setFont(title)

        body = self._body.font()
        body.setPointSize(metrics.pt("gloss"))
        self._body.setFont(body)

        self.updateGeometry()
        self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Inset 0.5px so a 1px pen doesn't clip at the widget edge.
        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        corner = metrics.radius()
        shape = QPainterPath()
        shape.addRoundedRect(box, corner, corner)

        painter.fillPath(shape, PANEL_HOT)

        painter.save()
        painter.setClipPath(shape)
        painter.fillRect(
            QRectF(box.left(), box.top(), _STRIPE, box.height()),
            self._signal(),
        )
        painter.restore()

        painter.setPen(QPen(LINE, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(shape)

        self._draw_mark(painter)
        painter.end()

    def _draw_mark(self, painter: QPainter) -> None:
        left = _STRIPE + _PAD_X
        top = self._title.geometry().center().y() - _MARK / 2
        box = QRectF(left, top, _MARK, _MARK).adjusted(0.5, 0.5, -0.5, -0.5)
        ink = self._signal()

        pen = QPen(ink, _STROKE)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if self._kind == WARN:
            painter.drawPath(_triangle(box))
        else:
            painter.drawEllipse(box)

        side = box.width()
        near = box.left() + side * _INSET
        far = box.left() + side * (1 - _INSET)

        if self._kind == DONE:
            tick = QPainterPath(QPointF(near, box.top() + side * 0.52))
            tick.lineTo(box.left() + side * 0.44, box.top() + side * 0.72)
            tick.lineTo(far, box.top() + side * 0.32)
            painter.drawPath(tick)
        elif self._kind == FAIL:
            painter.drawLine(
                QPointF(near, box.top() + side * _INSET),
                QPointF(far, box.bottom() - side * _INSET),
            )
            painter.drawLine(
                QPointF(far, box.top() + side * _INSET),
                QPointF(near, box.bottom() - side * _INSET),
            )
        elif self._kind == WARN:
            painter.drawLine(
                QPointF(box.center().x(), box.top() + side * 0.42),
                QPointF(box.center().x(), box.top() + side * 0.66),
            )
            painter.drawPoint(QPointF(box.center().x(), box.bottom() - side * 0.14))
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(ink)
            painter.drawEllipse(box.center(), _STROKE, _STROKE)

    def _signal(self) -> QColor:
        return ACCENT if self._kind in (WARN, FAIL) else DIM


def _triangle(box: QRectF) -> QPainterPath:
    # Inset at the foot so the triangle carries the same visual weight as
    # a circle in the same box.
    path = QPainterPath(QPointF(box.center().x(), box.top()))
    path.lineTo(box.right(), box.bottom() - box.height() * 0.08)
    path.lineTo(box.left(), box.bottom() - box.height() * 0.08)
    path.closeSubpath()
    return path
