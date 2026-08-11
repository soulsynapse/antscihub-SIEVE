"""All icons: every vendored glyph laid out to be looked through, nothing else.

The sheet a section away is a table, and a table answers *does this shape survive
the inks it has to be drawn in* — a comparison along a row, with the row's
subject fixed before you start reading. This section answers the question you
have when you do not yet know which glyph you want: what is in here. That is
browsing, and browsing wants the drawings adjacent and the same size, wrapped to
whatever width the bench has, with everything else off the screen.

So the two overlap in their contents and in nothing else, and neither is the
other with a flag. Merging them would mean one surface where the eye is asked to
scan across five inks and down forty names at once, which is the layout that
serves neither question.

One file rather than the two `icon_sheet` and `card_mockups` each have, because
there is no second half to split off: what there is to draw is `icons.names()`,
which is the folder, and this file is only the arrangement. There is nothing here
to say about a glyph — saying what a glyph is *for* is `icon_sheet/sheet.py`'s,
and a second opinion on that stored here is the pair that can disagree.

The tiles reflow: the grid is rebuilt when the width admits a different number of
columns. A fixed column count would either leave the bench half empty or push a
scroll sideways, and a horizontal scrollbar on a surface whose whole purpose is
*see what is there* hides part of the answer behind a gesture.
"""

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

#: How big a glyph is drawn here. Not `icons.SIZE`: at 16 a line icon is a mark
#: you recognise once you know what it is, and this is the surface for the case
#: where you do not. 32 is the size the sheet's last column already draws, so the
#: two sections agree about what large means.
_GLYPH = 32

#: How wide a tile is, and therefore how many fit. Wide enough for the longest
#: name vendored so far to sit on one line, with a longer one wrapping rather
#: than being cut — a browse grid whose labels elide is one where the names have
#: to be guessed from the pictures, the failure `icon_sheet` leads each row with
#: a name to avoid. Every tile is held to it, so the columns are the same width
#: whatever is in them: a grid whose columns are sized by their longest name puts
#: the glyphs at irregular intervals, and the eye scanning for a shape is then
#: also tracking where the next one starts.
_TILE = 112

#: The gap between tiles. Smaller than the gallery's gutter on purpose: these are
#: one set being scanned, and tiles spaced like blocks read as separate things.
_GAP = 6


class IconGrid(QWidget):
    """Every vendored glyph, wrapped, each under its name.

    Rebuilt rather than restyled when the palette moves, for the reason the sheet
    is: each tile holds a pixmap tinted when it was made, and no rule reaches
    inside one.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("gallery")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        #: How many tiles a row currently holds. Held so a resize that does not
        #: change it costs nothing — a resize is continuous while a window edge
        #: is dragged, and rebuilding a grid of pixmaps per pixel is the one way
        #: this surface could be slow.
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
        # Last, so a short set sits at the top rather than spreading its rows
        # down the whole bench.
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
        """Lay the tiles out again if the new width holds a different number.

        The count is computed from this widget's width rather than the scroll's
        viewport, because the viewport's width depends on whether a vertical
        scrollbar is showing, which depends on how many rows there are, which is
        what is being computed — asking the viewport makes the layout a fixed
        point and it oscillates by one column at the widths where the bar comes
        and goes.
        """
        super().resizeEvent(event)
        self._reflow()

    def _reflow(self) -> None:
        """The grid again, at whatever column count the width now admits."""
        room = self.width() - 2 * GUTTER
        columns = max(1, (room + _GAP) // (_TILE + _GAP))
        if columns == self._columns:
            return
        # The stretch is taken off the column it was put on before the count
        # moves. A `QGridLayout` keeps a stretch factor per index whether or not
        # anything stands there, so a widening left alone would have the old
        # trailing column — now a column of tiles — absorbing the slack and
        # spacing that one tile away from its row.
        if self._columns:
            self._grid.setColumnStretch(self._columns, 0)
        self._columns = columns
        self._fill()

    def _fill(self) -> None:
        """Empty the grid and lay every vendored glyph into it, in name order.

        `names()` and not a list held here: the folder is the only authority on
        what is vendored, and this section's whole claim is that it shows all of
        it.
        """
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
        # An empty column past the last tile takes the remainder, so a row that
        # does not divide evenly stays a grid instead of spreading its tiles to
        # the width of the pane.
        self._grid.setColumnStretch(self._columns, 1)

    def _redraw(self) -> None:
        """Every tile drawn again in the palette now in force, and the ground
        and scrollbar restated with it.

        Nothing to redraw before the first resize, and that is not a corner: the
        bench is built when the frame is and the palette is chosen on the card
        beside this one, so a change arriving at a section that has never been
        shown is the ordinary case. The tiles it would draw are the ones the
        first resize will draw anyway.
        """
        if self._columns:
            self._fill()
        self._restyle()

    def _restyle(self) -> None:
        """The gallery's ground and scrollbar, plus this grid's own two names.

        The gallery's sheet is borrowed rather than reimplemented: this section
        does not stand inside a `Gallery` — it is not a column of alternatives —
        but it is a scrolling surface on the same bench, and a second answer to
        what the bench's ground and scrollbar look like is the pair that comes to
        differ.
        """
        self.setStyleSheet(
            sheet()
            + f"""
            #igname {{ color: {rgb(DIM)}; }}
            #igglyph {{ color: {rgb(TEXT)}; }}
            """
        )


def _tile(glyph: str) -> QWidget:
    """One glyph over the string `icon()` takes for it.

    Drawn on labels and not on a button, for `icon_sheet`'s reason turned around:
    there the button column exists to show Qt switching modes, and here every
    tile is the rest ink so that scanning the grid is a comparison of shapes
    rather than of states.
    """
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
