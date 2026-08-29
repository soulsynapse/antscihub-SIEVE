"""Dot-and-word state indicator, painted inside a rounded outline."""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from sieve.gui import metrics, palette
from sieve.gui.palette import ACCENT, DIM, LINE, TEXT

LIVE = "live"
IDLE = "idle"
OFF = "off"

_DOT = 3.0
_GAP = 6

_PAD_X = 9
_PAD_Y = 3


class Pill(QWidget):
    """Dot-and-word state badge. No gestures."""

    def __init__(
        self,
        text: str = "",
        kind: str = IDLE,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._text = text
        self._kind = kind
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._resize()
        # Bound methods so PySide6 drops the connection when the receiver dies.
        palette.CHANGED.connect(self.update)
        metrics.CHANGED.connect(self._resize)

    def state(self) -> tuple[str, str]:
        """Return (text, kind)."""
        return self._text, self._kind

    def set_state(self, text: str, kind: str) -> None:
        """Replace both at once to avoid a frame with mismatched dot."""
        self._text = text
        self._kind = kind
        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QSize:
        text = self.fontMetrics()
        width = _PAD_X + 2 * _DOT + _PAD_X
        if self._text:
            width += _GAP + text.horizontalAdvance(self._text)
        return QSize(int(width), text.height() + 2 * _PAD_Y)

    def minimumSizeHint(self) -> QSize:
        # The dot alone carries almost no meaning; the text is the mark.
        return self.sizeHint()

    def _resize(self) -> None:
        font = self.font()
        font.setPointSize(metrics.pt("gloss"))
        self.setFont(font)
        self.updateGeometry()
        self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Inset 0.5px so a 1px pen doesn't clip at the widget edge.
        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        corner = box.height() / 2
        painter.setPen(QPen(LINE, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(box, corner, corner)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._dot())
        painter.drawEllipse(
            QRectF(box.left() + _PAD_X, box.center().y() - _DOT, 2 * _DOT, 2 * _DOT).center(),
            _DOT,
            _DOT,
        )

        if self._text:
            painter.setPen(QPen(DIM))
            painter.drawText(
                QRectF(
                    box.left() + _PAD_X + 2 * _DOT + _GAP,
                    box.top(),
                    box.width(),
                    box.height(),
                ),
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                self._text,
            )
        painter.end()

    def _dot(self) -> QColor:
        if self._kind == LIVE:
            return ACCENT
        if self._kind == OFF:
            return DIM
        return TEXT
