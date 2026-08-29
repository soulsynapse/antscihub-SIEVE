"""Dashed-outline empty state: a title saying what is missing, a body naming the next move."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from sieve.gui import metrics, palette
from sieve.gui.palette import DIM, LINE, TEXT, rgb

_PAD = 22

_LEAD = 2

# In pen-width units (Qt dash-pattern convention).
_DASH = (4.0, 4.0)


def sheet() -> str:
    """Label rules for callers that set an ancestor sheet (which would override these)."""
    return f"""
        #emptytitle {{
            color: {rgb(TEXT)};
            background: transparent;
            border: 0;
        }}
        #emptybody {{
            color: {rgb(DIM)};
            background: transparent;
            border: 0;
        }}
    """


class Empty(QWidget):
    """Dashed-outline placeholder: title, optional body, no gestures."""

    def __init__(
        self,
        title: str = "",
        body: str = "",
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._title = QLabel(title)
        self._title.setObjectName("emptytitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setWordWrap(True)

        self._body = QLabel(body)
        self._body.setObjectName("emptybody")
        self._body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._body.setWordWrap(True)
        self._body.setVisible(bool(body))

        column = QVBoxLayout(self)
        column.setContentsMargins(_PAD, _PAD, _PAD, _PAD)
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

    def message(self) -> tuple[str, str]:
        """Return (title, body)."""
        return self._title.text(), self._body.text()

    def set_message(self, title: str, body: str = "") -> None:
        """Replace both at once to avoid a frame with mismatched title and body."""
        self._title.setText(title)
        self._body.setText(body)
        self._body.setVisible(bool(body))
        self.updateGeometry()
        self.update()

    def heightForWidth(self, width: int) -> int:
        # Layout returns -1 when nothing wraps; fall back to sizeHint.
        height = self.layout().heightForWidth(width)
        return height if height >= 0 else self.sizeHint().height()

    def _restyle(self) -> None:
        self.setStyleSheet(sheet())
        self.update()

    def _resize(self) -> None:
        title = self._title.font()
        title.setPointSize(metrics.pt("name"))
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

        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        corner = metrics.radius()
        shape = QPainterPath()
        shape.addRoundedRect(box, corner, corner)

        pen = QPen(LINE, 1)
        pen.setDashPattern(list(_DASH))
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(shape)
        painter.end()
