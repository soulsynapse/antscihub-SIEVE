"""Text field with labelled frame and focus ring."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from sieve.gui import metrics, palette
from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, PANEL_HOT, TEXT, mix, rgb

# Public — check.py reuses these for the same "editable" look.
EDGE = 0.14
EDGE_HOVER = 0.30

# Public — check.py draws the same ring without a Field wrapper.
RING_W = 3
RING_GAP = 3
_RING_ALPHA = 64

# RADIUS is independent of metrics.radius() (card corners); public because
# the ring and select.py size themselves off it.
_PAD_X = 8
_PAD_Y = 4
RADIUS = 4

_SPACING = 4


class LineField(QLineEdit):
    """Styled single-line text input."""

    def __init__(
        self,
        text: str = "",
        *,
        numeric: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setObjectName("field")
        self._joined = False
        if numeric:
            self.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._dress()
        # Bound methods so PySide6 drops the connection when the receiver dies.
        palette.CHANGED.connect(self._dress)
        metrics.CHANGED.connect(self._dress)

    def set_joined(self, joined: bool) -> None:
        """Square right corners for abutting a unit suffix."""
        self._joined = joined
        self._dress()

    def _dress(self) -> None:
        right = 0 if self._joined else RADIUS
        self.setStyleSheet(f"""
            #field {{
                background: {rgb(PANEL)};
                color: {rgb(TEXT)};
                border: 1px solid {rgb(mix(LINE, TEXT, EDGE))};
                border-top-left-radius: {RADIUS}px;
                border-bottom-left-radius: {RADIUS}px;
                border-top-right-radius: {right}px;
                border-bottom-right-radius: {right}px;
                padding: {_PAD_Y}px {_PAD_X}px;
                font-size: {metrics.pt("name")}pt;
                selection-background-color: {rgb(ACCENT)};
                selection-color: {rgb(PANEL)};
            }}
            #field:hover {{ border-color: {rgb(mix(LINE, TEXT, EDGE_HOVER))}; }}
            #field:focus {{ border-color: {rgb(ACCENT)}; }}
            #field:disabled {{
                background: {rgb(PANEL_HOT)};
                color: {rgb(DIM)};
                border-color: {rgb(LINE)};
            }}
        """)


class Field(QWidget):
    """Label + hint wrapper that paints the focus ring around any control."""

    def __init__(
        self,
        label: str,
        control: QWidget,
        hint: str = "",
        *,
        unit: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._control = control if not unit else _United(control, unit)

        self._label = QLabel(label)
        self._label.setObjectName("flabel")
        self._hint = QLabel(hint)
        self._hint.setObjectName("fhint")
        self._hint.setWordWrap(True)

        column = QVBoxLayout(self)
        # Margins reserve room for the focus ring.
        column.setContentsMargins(RING_GAP, RING_GAP, RING_GAP, RING_GAP)
        column.setSpacing(_SPACING)
        if label:
            column.addWidget(self._label)
        column.addWidget(self._control)
        column.addWidget(self._hint)
        self._hint.setVisible(bool(hint))

        self._focused = control
        self._focused.installEventFilter(self)

        self._dress()
        palette.CHANGED.connect(self._dress)
        metrics.CHANGED.connect(self._dress)

    def control(self) -> QWidget:
        """Return the inner control widget."""
        return self._focused

    def set_hint(self, hint: str) -> None:
        """Show or hide the hint line below the control."""
        self._hint.setText(hint)
        self._hint.setVisible(bool(hint))

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self._focused and event.type() in (
            QEvent.Type.FocusIn,
            QEvent.Type.FocusOut,
        ):
            self.update()
        return False

    def _dress(self) -> None:
        self.setStyleSheet(f"""
            #flabel, #fhint {{
                color: {rgb(DIM)};
                font-size: {metrics.pt("gloss")}pt;
            }}
        """)

    def paintEvent(self, event) -> None:
        del event
        if not self._focused.hasFocus():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        inset = RING_W / 2
        box = QRectF(self._control.geometry()).adjusted(-inset, -inset, inset, inset)
        painter.setPen(QPen(ring(), RING_W))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(box, RADIUS + inset, RADIUS + inset)
        painter.end()


def ring() -> QColor:
    """Accent at glow alpha — call at draw time, never cache (roles mutate in place)."""
    return QColor(ACCENT.red(), ACCENT.green(), ACCENT.blue(), _RING_ALPHA)


class _United(QWidget):
    """Control + unit suffix butted into one box (e.g. 240 *frames*)."""

    def __init__(self, control: QWidget, unit: str) -> None:
        super().__init__()
        if isinstance(control, LineField):
            control.set_joined(True)
        self._suffix = QLabel(unit)
        self._suffix.setObjectName("funit")

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        row.addWidget(control)
        row.addWidget(self._suffix)

        self._dress()
        palette.CHANGED.connect(self._dress)
        metrics.CHANGED.connect(self._dress)

    def _dress(self) -> None:
        self.setStyleSheet(f"""
            #funit {{
                background: {rgb(PANEL_HOT)};
                color: {rgb(DIM)};
                border: 1px solid {rgb(mix(LINE, TEXT, EDGE))};
                border-left: 0;
                border-top-right-radius: {RADIUS}px;
                border-bottom-right-radius: {RADIUS}px;
                padding: {_PAD_Y}px {_PAD_X}px;
                font-size: {metrics.pt("gloss")}pt;
            }}
        """)
