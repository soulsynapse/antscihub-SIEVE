"""Reflowing grid of every vendored glyph, for browsing by shape."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sieve.gui import icons, palette
from sieve.gui.palette import DIM, TEXT, rgb
from sieve.gui.view.dev.gallery import GUTTER, sheet

_GLYPH = 32

_TILE = 112
_GAP = 6


class IconGrid(QWidget):
    """Every vendored glyph, wrapped, each under its name."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("gallery")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Cached so a resize that doesn't change column count skips the rebuild.
        self._columns = 0

        self._grid = QGridLayout()
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(_GAP)
        self._grid.setVerticalSpacing(_GAP)

        column = QWidget()
        column.setObjectName("gcolumn")
        stack = QVBoxLayout(column)
        stack.setContentsMargins(GUTTER, GUTTER, GUTTER, GUTTER)
        stack.setSpacing(GUTTER)
        stack.addLayout(self._grid)
        stack.addStretch(1)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("gscroll")
        self._scroll.setWidget(column)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        body = QVBoxLayout(self)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._scroll)

        self._restyle()
        palette.CHANGED.connect(self._redraw)

    def resizeEvent(self, event: QResizeEvent) -> None:
        # Use widget width, not viewport — viewport width depends on scrollbar
        # presence which depends on row count, creating an oscillation loop.
        super().resizeEvent(event)
        self._reflow()

    def _reflow(self) -> None:
        room = self.width() - 2 * GUTTER
        columns = max(1, (room + _GAP) // (_TILE + _GAP))
        if columns == self._columns:
            return
        # QGridLayout keeps stretch per index even after contents change.
        if self._columns:
            self._grid.setColumnStretch(self._columns, 0)
        self._columns = columns
        self._fill()

    def _fill(self) -> None:
        while (item := self._grid.takeAt(0)) is not None:
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        for index, glyph in enumerate(icons.names()):
            self._grid.addWidget(
                _tile(glyph),
                index // self._columns,
                index % self._columns,
                Qt.AlignmentFlag.AlignTop,
            )
        self._grid.setColumnStretch(self._columns, 1)

    def _redraw(self) -> None:
        if self._columns:
            self._fill()
        self._restyle()

    def _restyle(self) -> None:
        self.setStyleSheet(
            sheet()
            + f"""
            #igname {{ color: {rgb(DIM)}; }}
            #igglyph {{ color: {rgb(TEXT)}; }}
            """
        )


def _tile(glyph: str) -> QWidget:
    tile = QWidget()
    tile.setFixedWidth(_TILE)

    drawing = QLabel()
    drawing.setObjectName("igglyph")
    drawing.setPixmap(icons.pixmap(glyph, DIM, _GLYPH))
    drawing.setAlignment(Qt.AlignmentFlag.AlignCenter)

    name = QLabel(glyph)
    name.setObjectName("igname")
    name.setAlignment(Qt.AlignmentFlag.AlignCenter)
    name.setWordWrap(True)
    name.setFixedWidth(_TILE)
    name.setToolTip(f'icons.icon("{glyph}")')

    stack = QVBoxLayout(tile)
    stack.setContentsMargins(0, 4, 0, 4)
    stack.setSpacing(4)
    stack.addWidget(drawing)
    stack.addWidget(name)
    return tile
