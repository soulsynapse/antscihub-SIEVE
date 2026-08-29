"""Ruled table with a single-row selection mark."""

from __future__ import annotations

from typing import NamedTuple, Sequence

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from sieve.gui import metrics, palette
from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, PANEL_HOT, TEXT, mix, rgb
from sieve.gui.primitives.nav import MARK_W

_ROW_H = 38
_HEAD_H = 34

# The selection mark is painted inside this margin, so cells don't shift.
_PAD = 14

# Part of cell width, not layout spacing, so same-declared tables align.
_GAP = 12

# Row rules are softer than the header rule (which keeps full LINE).
_RULE = 0.55


class Column(NamedTuple):
    """Column spec: name, fixed pixel width, and optional right-alignment."""

    name: str
    width: int
    numeric: bool = False


class Table(QWidget):
    """Header row, data rows, and a single-row selection. Starts with nothing selected."""

    chosen = Signal(int)

    def __init__(self, columns: Sequence[Column], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._columns = tuple(columns)
        self._current = -1
        self._rows: list[_Row] = []
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        self._column = QVBoxLayout(self)
        self._column.setContentsMargins(0, 0, 0, 0)
        self._column.setSpacing(0)
        self._column.addWidget(_Row(self._columns, [c.name for c in columns], header=True))

        self._dress()
        # Bound methods so PySide6 drops the connection when the receiver dies.
        palette.CHANGED.connect(self._dress)
        metrics.CHANGED.connect(self._dress)

    def set_rows(self, rows: Sequence[Sequence[object]]) -> None:
        """Replace all rows; cells may be str, QWidget, or None. Clears selection."""
        for row in self._rows:
            self._column.removeWidget(row)
            row.setParent(None)
            row.deleteLater()
        self._rows = []
        self._current = -1
        for index, cells in enumerate(rows):
            row = _Row(self._columns, cells)
            row.picked.connect(lambda index=index: self.select(index))
            self._column.addWidget(row)
            self._rows.append(row)
        self._dress()

    def current(self) -> int:
        """The row that is current, or -1 while none is."""
        return self._current

    def select(self, index: int) -> None:
        """Pick a row. Out-of-range indices are silently ignored."""
        if not 0 <= index < len(self._rows) or index == self._current:
            return
        if 0 <= self._current < len(self._rows):
            self._rows[self._current].set_selected(False)
        self._current = index
        self._rows[index].set_selected(True)
        self.chosen.emit(index)

    def step(self, delta: int) -> None:
        """Move by delta rows, clamped to ends. From no selection, opens row 0."""
        if not self._rows:
            return
        if self._current < 0:
            self.select(0)
            return
        self.select(max(0, min(len(self._rows) - 1, self._current + delta)))

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            self.step(-1 if key == Qt.Key.Key_Up else +1)
            event.accept()
            return
        super().keyPressEvent(event)

    def _dress(self) -> None:
        self.setStyleSheet(
            f"""
            #cell {{ color: {rgb(TEXT)}; font-size: {metrics.pt("name")}pt; }}
            #head {{ color: {rgb(DIM)}; font-size: {metrics.pt("gloss")}pt; }}
            """
        )


class _Row(QWidget):

    picked = Signal()

    def __init__(
        self,
        columns: Sequence[Column],
        cells: Sequence[object],
        *,
        header: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._header = header
        self._selected = False
        self._hovered = False
        self.setFixedHeight(_HEAD_H if header else _ROW_H)
        # Needed because this widget paints its own hover fill.
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        if not header:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

        row = QHBoxLayout(self)
        row.setContentsMargins(_PAD, 0, _PAD, 0)
        row.setSpacing(0)
        for column, cell in zip(columns, list(cells) + [None] * len(columns)):
            row.addWidget(self._holder(column, cell))
        row.addStretch(1)

    def _holder(self, column: Column, cell: object) -> QWidget:
        holder = QWidget()
        holder.setFixedWidth(column.width)
        inner = QHBoxLayout(holder)
        inner.setContentsMargins(0, 0, _GAP, 0)
        inner.setSpacing(0)
        if isinstance(cell, str):
            inner.addWidget(_Cell(cell, numeric=column.numeric, header=self._header))
        elif isinstance(cell, QWidget):
            inner.addWidget(cell)
            inner.addStretch(1)
        return holder

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.update()

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if not self._header and event.button() == Qt.MouseButton.LeftButton:
            self.picked.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        box = QRectF(self.rect())

        if self._hovered and not self._header:
            painter.fillRect(box, PANEL_HOT)

        # 0.5px inset so a 1px pen doesn't clip at the widget edge.
        floor = box.bottom() - 0.5
        painter.setPen(QPen(LINE if self._header else mix(LINE, PANEL, _RULE), 1))
        painter.drawLine(QPointF(box.left(), floor), QPointF(box.right(), floor))

        if self._selected:
            painter.fillRect(QRectF(0, 0, MARK_W, box.height()), ACCENT)
        painter.end()


class _Cell(QLabel):
    """Elided label that keeps the full string for re-elision on resize."""

    def __init__(self, text: str, *, numeric: bool, header: bool) -> None:
        super().__init__()
        self.setObjectName("head" if header else "cell")
        self._full = text
        self.setAlignment(
            Qt.AlignmentFlag.AlignVCenter
            | (Qt.AlignmentFlag.AlignRight if numeric else Qt.AlignmentFlag.AlignLeft)
        )
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._elide()

    def changeEvent(self, event) -> None:
        # FontChange, not metrics.CHANGED — the font arrives via ancestor
        # stylesheet, and Qt hasn't handed it down when the signal fires.
        super().changeEvent(event)
        if event.type() == QEvent.Type.FontChange:
            self._elide()

    def _elide(self) -> None:
        super().setText(
            self.fontMetrics().elidedText(self._full, Qt.TextElideMode.ElideRight, self.width())
        )
