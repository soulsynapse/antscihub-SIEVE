"""Corner-radius and text-size sliders, live-previewed on the card they sit in."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from sieve.gui import metrics, palette
from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, PANEL_HOT, STACK_BG, TEXT, rgb
from sieve.gui.primitives import Slider

_GUTTER = 8

# String, not px — measured in the current font since these rows change that font.
_WIDEST = "+00 px"


def _sheet() -> str:
    return f"""
        #mvpanel {{
            background: {rgb(PANEL_HOT)};
            border: 1px solid {rgb(LINE)};
        }}
        #mvscroll {{ background: {rgb(PANEL_HOT)}; border: 0; }}
        #mvcolumn {{ background: {rgb(PANEL_HOT)}; }}
        #mvgroup {{
            color: {rgb(DIM)};
            font-size: {metrics.pt("gloss")}pt;
            font-weight: 600;
        }}
        #mvrow {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(LINE)};
        }}
        #mvname {{
            color: {rgb(TEXT)};
            font-size: {metrics.pt("name")}pt;
            font-weight: 600;
        }}
        #mvgloss {{ color: {rgb(DIM)}; font-size: {metrics.pt("gloss")}pt; }}
        #mvvalue {{ color: {rgb(ACCENT)}; font-size: {metrics.pt("name")}pt; }}
        QScrollBar:vertical {{
            background: {rgb(PANEL_HOT)};
            width: 8px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {rgb(LINE)};
            min-height: 24px;
        }}
        QScrollBar::handle:vertical:hover {{ background: {rgb(STACK_BG)}; }}
        QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
        QScrollBar::add-page, QScrollBar::sub-page {{ background: {rgb(PANEL_HOT)}; }}
    """


class MinorVisuals(QWidget):
    """Scrollable column of corner-radius and text-size sliders."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("mvpanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._rows: list[_Row] = []

        column = QWidget()
        column.setObjectName("mvcolumn")
        stack = QVBoxLayout(column)
        stack.setContentsMargins(_GUTTER, _GUTTER, _GUTTER, _GUTTER)
        stack.setSpacing(_GUTTER)

        stack.addWidget(_heading("corners"))
        corner = _Row(
            "card corners",
            "how far the corner of a card is cut — 0 leaves it square",
            metrics.RADIUS_MIN,
            metrics.RADIUS_MAX,
            "px",
        )
        corner.moved.connect(metrics.use_radius)
        corner.reads(metrics.radius)
        stack.addWidget(corner)
        self._rows.append(corner)

        stack.addSpacing(_GUTTER)
        stack.addWidget(_heading("text size"))
        base = _Row(
            "everything",
            "the size the application is set in, and what the three below are off",
            metrics.SIZE_MIN,
            metrics.SIZE_MAX,
            "pt",
        )
        base.moved.connect(metrics.use_size)
        base.reads(metrics.size)
        stack.addWidget(base)
        self._rows.append(base)

        for text in metrics.TEXTS:
            # Slider moves in trim units; readout shows resolved points.
            row = _Row(
                text.label,
                text.gloss,
                metrics.TRIM_MIN,
                metrics.TRIM_MAX,
                "pt",
                shown=lambda role=text.key: metrics.pt(role),
            )
            row.moved.connect(lambda points, role=text.key: metrics.use_text(role, points))
            row.reads(lambda role=text.key: metrics.trim(role))
            stack.addWidget(row)
            self._rows.append(row)

        stack.addStretch(1)

        scroll = QScrollArea()
        scroll.setObjectName("mvscroll")
        scroll.setWidget(column)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        body = QVBoxLayout(self)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(scroll)

        self._restyle()
        palette.CHANGED.connect(self._restyle)
        # Moving the base changes all trim readouts, so every row refreshes.
        metrics.CHANGED.connect(self._refresh)

    def _restyle(self) -> None:
        # Refresh too — readout widths depend on the font this sheet sets.
        self.setStyleSheet(_sheet())
        self._refresh()

    def _refresh(self) -> None:
        for row in self._rows:
            row.refresh()


def _heading(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("mvgroup")
    return label


class _Row(QFrame):
    """One labelled slider that reports where it was dragged; sets nothing itself."""

    moved = Signal(int)

    def __init__(
        self,
        name: str,
        gloss: str,
        low: int,
        high: int,
        unit: str,
        shown=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("mvrow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        self._unit = unit
        self._held = lambda: low
        self._shown = shown

        title = QLabel(name)
        title.setObjectName("mvname")

        self._value = QLabel()
        self._value.setObjectName("mvvalue")
        self._value.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(_GUTTER)
        head.addWidget(title, 1)
        head.addWidget(self._value)

        note = QLabel(gloss)
        note.setObjectName("mvgloss")
        note.setWordWrap(True)

        self._slider = Slider(low, high)
        self._slider.valueChanged.connect(self.moved)

        column = QVBoxLayout(self)
        column.setContentsMargins(8, 6, 8, 6)
        column.setSpacing(2)
        column.addLayout(head)
        column.addWidget(note)
        column.addSpacing(2)
        column.addWidget(self._slider)

    def reads(self, held) -> None:
        """Bind a callable returning the current slider position."""
        self._held = held
        self.refresh()

    def refresh(self) -> None:
        self._slider.show_value(self._held())
        shown = self._shown() if self._shown is not None else self._held()
        self._value.setText(f"{shown} {self._unit}")
        self._value.setFixedWidth(self._value.fontMetrics().horizontalAdvance(_WIDEST))
