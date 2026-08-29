"""Drop-down select: one of many, from a list that is not standing open."""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QComboBox, QStyledItemDelegate, QWidget

from sieve.gui import metrics, palette
from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, PANEL_HOT, TEXT, mix, rgb
from sieve.gui.primitives.field import EDGE, EDGE_HOVER, RADIUS

_PAD_X = 8
_PAD_Y = 4
_PAD_RIGHT = 24

_MARK_W = 8.0
_MARK_H = 3.5
_MARK_PEN = 1.4
_MARK_INSET = 9.0

# Explicit because a sheet that touches the view at all takes over its metrics.
_ITEM_PAD_X = 10
_ITEM_PAD_Y = 5


class Select(QComboBox):
    """Styled combo box with a painted chevron."""

    def __init__(
        self,
        options: list[str] | None = None,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("select")
        self._hovered = False
        if options:
            self.addItems(options)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Painted chevron needs hover state explicitly.
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        # Without the styled delegate, ::item rules don't reach popup rows.
        self.setItemDelegate(QStyledItemDelegate(self))
        self._dress()
        # Bound methods so PySide6 drops the connection when the receiver dies.
        palette.CHANGED.connect(self._dress)
        metrics.CHANGED.connect(self._dress)

    def _dress(self) -> None:
        self.setStyleSheet(f"""
            #select {{
                background: {rgb(PANEL)};
                color: {rgb(TEXT)};
                border: 1px solid {rgb(mix(LINE, TEXT, EDGE))};
                border-radius: {RADIUS}px;
                padding: {_PAD_Y}px {_PAD_RIGHT}px {_PAD_Y}px {_PAD_X}px;
                font-size: {metrics.pt("name")}pt;
            }}
            #select:hover {{ border-color: {rgb(mix(LINE, TEXT, EDGE_HOVER))}; }}
            #select:focus {{ border-color: {rgb(ACCENT)}; }}
            #select:disabled {{
                background: {rgb(PANEL_HOT)};
                color: {rgb(DIM)};
                border-color: {rgb(LINE)};
            }}
            #select::drop-down {{ border: 0; width: 0; background: transparent; }}
            #select::down-arrow {{ image: none; width: 0; height: 0; }}

            /* The dropped list, in the dress `menu.py` gives a menu. */
            #select QAbstractItemView {{
                background: {rgb(PANEL)};
                color: {rgb(TEXT)};
                border: 1px solid {rgb(LINE)};
                outline: 0;
                selection-background-color: {rgb(PANEL_HOT)};
                selection-color: {rgb(TEXT)};
            }}
            #select QAbstractItemView::item {{
                padding: {_ITEM_PAD_Y}px {_ITEM_PAD_X}px;
            }}
        """)

    def wheelEvent(self, event) -> None:
        # Ignore (not swallow) when unfocused so the scroll reaches the parent.
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        right = self.width() - _MARK_INSET
        middle = self.height() / 2
        mark = QPainterPath(QPointF(right - _MARK_W, middle - _MARK_H / 2))
        mark.lineTo(right - _MARK_W / 2, middle + _MARK_H / 2)
        mark.lineTo(right, middle - _MARK_H / 2)
        if not self.isEnabled():
            ink = DIM
        else:
            ink = TEXT if (self._hovered or self.hasFocus()) else DIM
        pen = QPen(ink, _MARK_PEN)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(mark)
        painter.end()
