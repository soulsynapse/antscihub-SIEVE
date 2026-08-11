"""The ruled table: many rows of the same facts, with one of them picked out.

Lifted from `mockup/paper_primitives.py`, and the first thing here that holds
*data* rather than other widgets. A card, a stack, a section and a view are what
the work is seen in and are handed whatever a view builds; a pill and a banner
are marks the interface makes; this is neither — it is a shape the caller hands
rows to, and the rows are facts about things the user did not draw.

It arrives the way the budget controls did rather than the way the slider did.
`check.py` settled what a set state looks like on the grounds that *the first
view to draw a write list would otherwise be deciding for every list of facts
after it*, and this is that list: the write list, a run's steps and their costs,
a sheet of detections are the same picture three times, and the first of them to
invent a header, a rule and a selected row would be fixing all three.

Built from rows and not from `QTableWidget`, which is the mockup's own comment
and is a Qt fact rather than a taste. The mark that says which row is current is
drawn outside the cells — down the leading edge of the whole row, the same mark
`nav.py` wears down an entry and `segmented.py` wears along a bar's foot — and an
item delegate is handed one cell's rect and cannot paint past it. A table whose
selection had to live inside a cell would be a fourth answer to *which one is
current*, and it would be the only one that looked different.

Three of the mockup's decisions are declined, each for a reason already argued
somewhere in this folder.

The accent wash under the selected row goes, on `segmented.py`'s grounds: the
tree's answer to which of a visible few is current is the accent edge, and a
wash is a second answer. What replaces the mockup's hover literal is the same
substitution — `#fafbfc` is a colour from the light palette it was drawn in, and
a row lit with it in a dark palette is a white bar. So the fill is `PANEL_HOT`,
which is the step the pointer takes everywhere here, and the split is `nav.py`'s:
the fill is the pointer's answer and the edge is the selection's, so a hovered
row and the current row are never the same picture even when they are the same
row.

The mono numeric cells go, on `field.py`'s: nothing in this tree names a font
family, that family belongs beside the sizes in `metrics.py` when it is chosen,
and right-alignment is the half of the treatment that costs no decision. A column
is numeric because it was *declared* one and never because its text happens to be
digits — the mockup says this, and it is worth saying again about the column
rather than the cell, since `1.2 MB` and `—` land in the same column and a rule
read off each value would align them differently row by row.

The uppercase, letter-tracked header goes too, and this one is not lifted from
elsewhere. The header's job is to not read as a row of data, and it is already
told apart twice — the ink is `DIM` where a cell's is `TEXT`, and the rule under
it is `LINE` where the rules between rows are softer. Uppercasing on top of that
would be a third mark for one distinction, and it would edit the caller's word:
a column the view calls `ms` is not a column called `MS`.

The rules are two weights, and that is the one thing here with no precedent to
borrow. `LINE` separates two kinds of thing — the header from the rows, a pane
from a pane — and a whole column of it turns a list into a grid. The rules
between rows separate two of the same thing, so they take a step off `LINE`
toward the panel underneath: enough that the eye can run along one row, not so
much that thirty of them read as a cage.

There is no foot. The mockup draws one — a summary line and a primary button —
and it is the *card's* foot rather than the table's: what a run costs and whether
it may start are a view's sentence about what it is showing, and a table that
grew a primary button would be spending `button.py`'s one-per-screen budget on
behalf of whoever put it on a card. A view puts a table in a `Card` and the card
already has the verbs.
"""

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

#: How tall a row is, and the header above them. Fixed rather than grown from
#: the text, which is `metrics.py`'s own bargain: `SIZE_MAX` is set where the
#: fixed-height shapes in this tree stop fitting their rows, and it is a ceiling
#: and not a scaling rule because a list that resized itself to its type would
#: move under the user arrowing down it. The header is the shorter of the two —
#: it is a caption over the list rather than a member of it.
_ROW_H = 38
_HEAD_H = 34

#: The margin at each end of a row. The leading mark is drawn inside it, so a
#: selected row's first cell stands where an unselected one's does without the
#: mark needing room reserved for it — which is the one place `nav.py`'s reason
#: for marking every entry does not apply, since a painted mark takes no space
#: from a layout the way a border in a stylesheet does.
_PAD = 14

#: Between one column's text and the next column's. Part of the cell's own width
#: rather than the layout's spacing, so a column is as wide as the caller
#: declared it including the air after it, and two tables declared with the same
#: numbers line up.
_GAP = 12

#: How far the rule between two rows steps off `LINE` toward the panel behind
#: it. The header's rule keeps `LINE` whole: it divides two kinds of thing, and
#: these divide two of the same.
_RULE = 0.55


class Column(NamedTuple):
    """One column: what it is called, how wide it is, and which way it reads.

    The width is in pixels and is the caller's, because a column that took a
    share of the table would move every time the pane was resized, and the whole
    of a table's argument for existing is that the same fact is in the same place
    on every row.

    `numeric` is the declaration `field.py` left as the only half of the mockup's
    treatment that costs nothing: right-aligned, so a column of quantities lines
    up on its last digit rather than its first character.
    """

    name: str
    width: int
    numeric: bool = False


class Table(QWidget):
    """A header, a run of rows under it, and at most one of them current.

    The table holds the selection and the rows do not, for `nav.py`'s reason:
    the one thing true of the whole list — that exactly one row is picked, or
    none is — would otherwise be spread across every row, each needing to hear
    about the others to stop being it.

    Which row is current when a list arrives is the caller's question and not
    this widget's. The library has a current project and a write list has
    nothing selected until something is picked, so `set_rows` selects nothing
    and a view that wants the first row open says `select(0)`.
    """

    #: Which row is current. Emitted on every move, the pointer's and the
    #: keyboard's alike, so whatever draws the row's contents elsewhere follows
    #: both without either knowing about the other.
    chosen = Signal(int)

    def __init__(self, columns: Sequence[Column], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._columns = tuple(columns)
        self._current = -1
        self._rows: list[_Row] = []
        # It answers ↑/↓, so it has to be reachable by tabbing as well as by
        # clicking — the same floor `nav.py` puts under a surface that moves
        # under the keyboard.
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        self._column = QVBoxLayout(self)
        self._column.setContentsMargins(0, 0, 0, 0)
        self._column.setSpacing(0)
        self._column.addWidget(_Row(self._columns, [c.name for c in columns], header=True))

        self._dress()
        # Bound methods and never lambdas, for `button.py`'s reason: PySide6
        # drops a connection to a bound method when the receiver goes, where a
        # lambda closing over `self` would keep a dead table subscribed.
        palette.CHANGED.connect(self._dress)
        metrics.CHANGED.connect(self._dress)

    def set_rows(self, rows: Sequence[Sequence[object]]) -> None:
        """Replace what is listed. A cell is a string, or a widget the caller
        built, or `None` for a column this row has nothing in.

        The selection is dropped rather than carried over: the row that was
        third is not the new third row, and a table that kept the index would be
        claiming it was.
        """
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
        """Pick a row. Out of range is nothing, so a caller may hand this the
        result of an arithmetic without checking the ends first."""
        if not 0 <= index < len(self._rows) or index == self._current:
            return
        if 0 <= self._current < len(self._rows):
            self._rows[self._current].set_selected(False)
        self._current = index
        self._rows[index].set_selected(True)
        self.chosen.emit(index)

    def step(self, delta: int) -> None:
        """Move `delta` rows, stopping at the ends rather than wrapping — a held
        key comes to rest at the last row instead of reappearing at the first.

        From nothing selected, either direction opens the first row: the gesture
        means *start reading this list*, and which end it starts at is a question
        only a list that was already being read has an answer to.
        """
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
        # Escape among them: it is the overlay's, and an accepted key here is
        # one the thing on top never sees.
        super().keyPressEvent(event)

    def _dress(self) -> None:
        """One sheet for the whole table, in whatever the palette and the sizes
        are now.

        Held on the table rather than on each row, since every row is dressed
        the same and a sheet per row is the same string built once per row on
        every palette change. It reaches the cells by object name and so leaves
        a widget a caller put in one alone — a `Button` or a `Check` in a cell
        keeps the dress its own file gave it.
        """
        self.setStyleSheet(
            f"""
            #cell {{ color: {rgb(TEXT)}; font-size: {metrics.pt("name")}pt; }}
            #head {{ color: {rgb(DIM)}; font-size: {metrics.pt("gloss")}pt; }}
            """
        )


class _Row(QWidget):
    """One row on the surface, or the header over them.

    It reports being picked and marks nothing: the fill and the mark it paints
    are what it was told it is, never what it decided when it was clicked.
    """

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
        # Asked for explicitly, as `card.py` and `check.py` do: hover is
        # something this widget paints, so it has to be something this widget is
        # told about.
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        if not header:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

        row = QHBoxLayout(self)
        row.setContentsMargins(_PAD, 0, _PAD, 0)
        row.setSpacing(0)
        for column, cell in zip(columns, list(cells) + [None] * len(columns)):
            row.addWidget(self._holder(column, cell))
        # Last, and what keeps the declared columns at their declared widths
        # instead of spread across whatever width the row ends up with.
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
        """Fill, rule, mark — and nothing at rest.

        A row at rest paints no ground at all, so the table takes the colour of
        whatever it was put on. A card's fill and a stack's ground are one
        decision made in `card.py`, and a row that filled itself `PANEL` would be
        that decision made a second time by a widget that cannot see which of
        the two it is standing on.
        """
        del event
        painter = QPainter(self)
        box = QRectF(self.rect())

        if self._hovered and not self._header:
            painter.fillRect(box, PANEL_HOT)

        # Half a pixel up, for `card.py`'s reason: a 1px pen straddles the line
        # it is given, so a rule on the row's own bottom edge loses half of
        # itself past the widget and comes back looking like half a line.
        floor = box.bottom() - 0.5
        painter.setPen(QPen(LINE if self._header else mix(LINE, PANEL, _RULE), 1))
        painter.drawLine(QPointF(box.left(), floor), QPointF(box.right(), floor))

        if self._selected:
            painter.fillRect(QRectF(0, 0, MARK_W, box.height()), ACCENT)
        painter.end()


class _Cell(QLabel):
    """A cell's text, kept whole and drawn as much of as there is room for.

    Elided rather than clipped or wrapped: a column is as wide as the caller
    declared it, one long name in a list of short ones is the ordinary case, and
    a wrapped cell would make one row taller than the row above it — which is
    the thing a table exists to prevent. The full string is held, so a column
    widened later comes back rather than having been thrown away.
    """

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
        """The type size moved, so the same string needs a different cut.

        `FontChange` and not `metrics.CHANGED` directly: the size arrives here as
        a font on an ancestor's stylesheet, and Qt tells a widget when the font
        it inherits has been replaced. Subscribing to the signal instead would
        mean re-eliding against the font Qt has not handed down yet.
        """
        super().changeEvent(event)
        if event.type() == QEvent.Type.FontChange:
            self._elide()

    def _elide(self) -> None:
        super().setText(
            self.fontMetrics().elidedText(self._full, Qt.TextElideMode.ElideRight, self.width())
        )
