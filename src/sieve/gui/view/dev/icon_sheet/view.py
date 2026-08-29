"""Icon table: one row per glyph, one column per ink it must survive."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QGridLayout, QLabel, QToolButton, QWidget

from sieve.gui import icons, palette
from sieve.gui.palette import TEXT, rgb
from sieve.gui.view.dev.gallery import Gallery, Variant
from sieve.gui.view.dev.icon_sheet.sheet import INKS, Group, Ink, groups

_NAME = 150
_CELL = 48


class IconSheet(Gallery):
    """Every vendored glyph, grouped by what it is here to say."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            tuple(
                Variant(group.name, group.gloss, _Table(group)) for group in groups()
            ),
            parent,
        )


class _Table(QWidget):
    """One group's glyphs; rebuilt on palette change since pixmaps bake their colour."""

    def __init__(self, group: Group, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._group = group

        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(0)
        self._grid.setVerticalSpacing(4)
        self._grid.setColumnMinimumWidth(0, _NAME)
        self._grid.setColumnStretch(len(INKS) + 2, 1)
        self._fill()

        self._restyle()
        palette.CHANGED.connect(self._redraw)

    def _fill(self) -> None:
        self._grid.addWidget(_caption("on a button"), 0, 1)
        for column, ink in enumerate(INKS, start=2):
            self._grid.addWidget(_caption(ink.caption), 0, column)
        for row, glyph in enumerate(self._group.glyphs, start=1):
            self._grid.addWidget(_name(glyph), row, 0)
            self._grid.addWidget(
                _button(glyph, row), row, 1, Qt.AlignmentFlag.AlignCenter
            )
            for column, ink in enumerate(INKS, start=2):
                self._grid.addWidget(
                    _cell(glyph, ink), row, column, Qt.AlignmentFlag.AlignCenter
                )

    def _redraw(self) -> None:
        while (item := self._grid.takeAt(0)) is not None:
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self._fill()
        self._restyle()

    def _restyle(self) -> None:
        self.setStyleSheet(
            f"""
            #isname {{ color: {rgb(TEXT)}; }}
            QToolButton {{ border: 0; padding: 0; background: transparent; }}
            """
        )


def _caption(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("vgloss")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setFixedWidth(_CELL)
    return label


def _name(glyph: str) -> QLabel:
    label = QLabel(glyph)
    label.setObjectName("isname")
    return label


def _button(glyph: str, row: int) -> QToolButton:
    # Alternating enabled/disabled so both button states are visible per group.
    button = QToolButton()
    button.setIcon(icons.icon(glyph))
    button.setIconSize(QSize(icons.SIZE, icons.SIZE))
    button.setAutoRaise(True)
    button.setFixedWidth(_CELL)
    button.setEnabled(row % 2 == 1)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setToolTip(f'icons.icon("{glyph}")')
    return button


def _cell(glyph: str, ink: Ink) -> QLabel:
    label = QLabel()
    label.setPixmap(icons.pixmap(glyph, ink.colour, ink.size, ink.filled))
    label.setFixedWidth(_CELL)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label
