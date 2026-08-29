"""The glyphs as a table: one row per icon, one column per way it is drawn.

A table and not a wall of icons, because what is being checked is not which
glyph is prettiest — it is whether a shape survives the inks it has to be legible
in. That is a comparison along a row, and a grid of pictures has nowhere to put
it.

Each row leads with the string `icon()` is called with, which is the other half
of what the sheet is for: the name is the API, and a glyph whose name has to be
guessed from a picture is a glyph that gets vendored twice.

The columns are fixed widths rather than shared out, so the groups line up down
the page — the sheet is read as one table interrupted by headings, and three
grids each sizing to its own longest name would be three tables.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QGridLayout, QLabel, QToolButton, QWidget

from sieve.gui import icons, palette
from sieve.gui.palette import TEXT, rgb
from sieve.gui.view.dev.gallery import Gallery, Variant
from sieve.gui.view.dev.icon_sheet.sheet import INKS, Group, Ink, groups

#: How much of a row the names take. Wide enough for the longest name vendored
#: so far with room for a longer one, so every row keeps the height of the rows
#: around it.
_NAME = 150

#: How wide a drawing's column is: the largest glyph on the sheet plus enough
#: air that neighbouring cells read as separate things.
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
    """One group's glyphs, with the column captions above them.

    A widget with a rebuild rather than a function returning a grid, for the
    reason the card mocks are one: the cells are pixmaps, a pixmap is drawn in
    the colour in force when it was made, and no stylesheet reaches inside one.
    Everything on the sheet is therefore built again when the palette moves —
    which on this section is not an incidental cost but the point, since a bench
    that kept showing the old greys would be lying about the palette just picked.
    """

    def __init__(self, group: Group, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._group = group

        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(0)
        self._grid.setVerticalSpacing(4)
        self._grid.setColumnMinimumWidth(0, _NAME)
        # An empty column after the last cell takes whatever width is left, so
        # the drawings stay in a block at the left and the row stays readable as
        # a comparison at any bench width.
        self._grid.setColumnStretch(len(INKS) + 2, 1)
        self._fill()

        self._restyle()
        palette.CHANGED.connect(self._redraw)

    def _fill(self) -> None:
        """The caption row, then one row per glyph.

        The captions are repeated per group rather than written once at the top
        of the section. A column heading is only useful within about a screen of
        the thing it names, and the whole shape of the bench is a column that
        scrolls past the top.
        """
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
        """The sheet again, and every cell in it drawn again in the new inks."""
        while (item := self._grid.takeAt(0)) is not None:
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self._fill()
        self._restyle()

    def _restyle(self) -> None:
        """The rules the table's own object names need.

        Scoped to those names and to the tool buttons under this widget: the
        gallery's sheet is set on an ancestor and supplies everything else the
        block is drawn in, and a rule here for anything broader would reach the
        drawings and quietly become the bench's answer to what a label looks
        like.
        """
        self.setStyleSheet(
            f"""
            #isname {{ color: {rgb(TEXT)}; }}
            QToolButton {{ border: 0; padding: 0; background: transparent; }}
            """
        )


def _caption(text: str) -> QLabel:
    """A column heading, in the gallery's own quiet ink and centred over its
    cells — except the first, which is over the names and is not a drawing."""
    label = QLabel(text)
    label.setObjectName("vgloss")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setFixedWidth(_CELL)
    return label


def _name(glyph: str) -> QLabel:
    """The string `icon()` takes, which is the row's subject."""
    label = QLabel(glyph)
    label.setObjectName("isname")
    return label


def _button(glyph: str, row: int) -> QToolButton:
    """The glyph on the widget it will really be on: hoverable, and refused on
    every other row.

    Alternating rather than every button enabled, because the three inks beside
    it are swatches and this column is the only place the sheet shows Qt actually
    switching between them — an enabled row shows the rest ink becoming the hover
    ink under the pointer and the `autoRaise` frame arriving with it, and a
    disabled one shows what a refused verb looks like on a real button rather
    than as a colour. Which row gets which is arbitrary: what is being checked is
    the button, and both states are on screen in every group.

    Inert on purpose. A bench button that did something would be the one thing
    on the sheet that is not a drawing.
    """
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
    """One glyph drawn one way, on a label.

    A label and not a button: these are swatches of a state, and a swatch that
    lit up under the pointer would be showing a different state than the one it
    is labelled with.
    """
    label = QLabel()
    label.setPixmap(icons.pixmap(glyph, ink.colour, ink.size, ink.filled))
    label.setFixedWidth(_CELL)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label
