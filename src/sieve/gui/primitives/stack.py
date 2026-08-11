"""The header and the ground under it: where a column of cards lives.

The other half of the card mock up. `card.py` took the card out of
`mockup/paper_cards.py`; this takes what the card was standing in — the band
across the top saying what the whole column comes to, and the scrolling ground
the cards are seen against. A card is only ever seen in one of these, and the two
were settled together: the card's fill is `PANEL` because the ground under it is
`STACK_BG`, and either one moved without the other is a card that has stopped
being a card on a ground.

The header is a panel band and the ground is not, which is the one thing that
makes this read as a header rather than as the first row of the column. It is the
same figure the window's own chrome cuts — a filled strip closed by a rule,
against the ground the panes leave uncovered — and it is drawn here rather than
imported from `frame/chrome.py` because that file dresses the window and this
dresses a view inside a pane: a view that reached into the frame's chrome would
be a view that could not be put in a second pane.

What it holds is a title, room in the band for whatever the view counts, a quiet
line at the far end, and cards. What it does not hold is a selection: which card
the user is standing on is the view's, for the reason `project_list/view.py`
gives — exactly one row being current is a fact about the whole column, and a
stack that owned it would be answering a question its caller has to answer
anyway when the keyboard moves. So there is no `current()` here, and
`ensure_visible` is the one thing the view asks of the scroll.

The cards are `QWidget`, not `Card`. This is the ground and not the shape on it:
the library's rows are a card of their own making (`project_list/card.py`), the
empty-library sentence stands in the same column, and a stack that took only
`Card` would have both of those reaching past it into the layout.
"""

from __future__ import annotations

from typing import Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from sieve.gui import palette
from sieve.gui.palette import DIM, LINE, PANEL, PANEL_HOT, STACK_BG, TEXT, rgb

#: The gap between cards, and it is deliberately not the margin around them. The
#: mockup's 26 is room for something to be drawn *between* two cards — the chain's
#: edges descend through it — and there is nothing to draw beyond the first and
#: the last, so the ends pay `_MARGIN` instead. That is the opposite bargain from
#: the one-number-for-both the rows inside a card make (`sections.py`), and the
#: difference is exactly that a gap here carries content and a gap there does not.
#:
#: A view with nothing between its cards passes its own smaller `gap`, which is
#: what the library does: 26px of ground between two three-line rows reads as two
#: lists rather than one.
_GAP = 26
_MARGIN = 16

#: Where the band holds its own contents off the pane's edges. The left inset is
#: the column's, so the title stands on the same x as the cards below it and the
#: whole view is read down one line.
_PAD_X = _MARGIN
_PAD_Y = 13

#: The scrollbar. Narrow, no arrows, and a handle in `LINE` that lifts to
#: `PANEL_HOT` under the pointer: the bar says where in the column the view is
#: and is not a control the eye should find before the cards.
_BAR_W = 8
_BAR_MIN = 24


def sheet() -> str:
    """The stack's own rules, for a caller that sets a sheet of its own.

    Handed out for the reason `gallery.sheet()` is: a second stylesheet set on a
    widget inside this one replaces nothing, but a sheet set on an *ancestor*
    reaches here and a view that dresses itself has to include these back. Every
    rule is scoped to an object name, never to a bare class, because the ground
    holds whatever the view put on it and a `QLabel` rule would reach into all
    of it.
    """
    return f"""
        #stack {{ background: {rgb(STACK_BG)}; }}
        #stackhead {{
            background: {rgb(PANEL)};
            border-bottom: 1px solid {rgb(LINE)};
        }}
        #stackscroll {{ background: {rgb(STACK_BG)}; border: 0; }}
        #stackground {{ background: {rgb(STACK_BG)}; }}
        #stacktitle {{ color: {rgb(TEXT)}; font-weight: 600; }}
        #stacknote {{ color: {rgb(DIM)}; }}
        QScrollBar:vertical {{
            background: {rgb(STACK_BG)};
            width: {_BAR_W}px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {rgb(LINE)};
            min-height: {_BAR_MIN}px;
        }}
        QScrollBar::handle:vertical:hover {{ background: {rgb(PANEL_HOT)}; }}
        QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
        QScrollBar::add-page, QScrollBar::sub-page {{ background: {rgb(STACK_BG)}; }}
    """


class CardStack(QWidget):
    """A titled band, and under it a scrolling column of cards on the ground.

    Handed its title and its cards rather than knowing either: what a stack is a
    stack *of* is the view's, and a stack that reached for a project or a step
    would be the one file where two views' contents met — the same bargain
    `card.py` makes one level down.

    It scrolls unconditionally. Any column of these outgrows the pane before the
    work does, and a stack that scrolled only when it had to would change its own
    width at the moment a card was added — walking every card's right edge, and
    with it every rule measured off a title.
    """

    def __init__(
        self,
        title: str = "",
        cards: Iterable[QWidget] = (),
        gap: int = _GAP,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("stack")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._title = QLabel(title)
        self._title.setObjectName("stacktitle")
        self._note = QLabel()
        self._note.setObjectName("stacknote")

        self._band = QWidget()
        self._band.setObjectName("stackhead")
        self._head = QHBoxLayout(self._band)
        self._head.setContentsMargins(_PAD_X, _PAD_Y, _PAD_X, _PAD_Y)
        self._head.setSpacing(12)
        self._head.addWidget(self._title)
        # The stretch is what the caller's own figures land before, and the note
        # is what they land after — see `head()`. Both indices are read off the
        # layout rather than remembered, so neither moves when the other fills.
        self._head.addStretch(1)
        self._head.addWidget(self._note)

        self._ground = QWidget()
        self._ground.setObjectName("stackground")
        self._column = QVBoxLayout(self._ground)
        self._column.setContentsMargins(_MARGIN, _MARGIN, _MARGIN, _MARGIN)
        self._column.setSpacing(gap)
        # Last for good, so a short column sits under the band rather than spread
        # down the pane: cards go in before it, and the stretch is the one item
        # this layout is guaranteed to still end with.
        self._column.addStretch(1)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("stackscroll")
        self._scroll.setWidget(self._ground)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        # Never sideways. The cards take the column's width, so a horizontal bar
        # could only ever appear because something inside one refused to be
        # narrowed — and scrolling a card half out of the pane hides the verbs at
        # its right end, which is the half the pointer came for.
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        body = QVBoxLayout(self)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._band)
        body.addWidget(self._scroll, 1)

        for card in cards:
            self.add_card(card)

        # Last, because the sheet is set on a widget whose children have to exist
        # for the rules naming them to land on anything.
        self._restyle()
        # A bound method and never a lambda: PySide6 holds a receiver's bound
        # method weakly and drops the connection when the widget goes, where a
        # lambda closing over `self` would keep a dead stack subscribed.
        palette.CHANGED.connect(self._restyle)

    # -- the band ----------------------------------------------------------

    def set_title(self, title: str) -> None:
        self._title.setText(title)

    def set_note(self, note: str) -> None:
        """The quiet line at the band's far end — how many there are, how many
        are recomputing. Empty is the honest blank: a note that fell back to a
        dash would be a figure the view never claimed."""
        self._note.setText(note)

    def head(self) -> QHBoxLayout:
        """The band's row, for a view with something to count.

        The mockup's is two figures and their labels — what the chain costs a
        frame, and what that is in frames per second — and those are the view's
        because only it knows what is being measured. Insert at
        `head().count() - 2` to sit beside the title, which is before the stretch
        and before the note.
        """
        return self._head

    # -- the ground --------------------------------------------------------

    def add_card(self, card: QWidget) -> None:
        """One more card at the foot of the column, above the stretch."""
        self.insert_card(len(self.cards()), card)

    def insert_card(self, index: int, card: QWidget) -> None:
        """A card at a position in the column. Out of range is clamped to the
        ends, so a caller may hand this the result of an arithmetic."""
        self._column.insertWidget(max(0, min(len(self.cards()), index)), card)

    def cards(self) -> tuple[QWidget, ...]:
        """The cards in the column, in the order they stand in.

        Read off the layout rather than kept in a list beside it. The layout is
        already the answer to *what is in this column and in what order*, and a
        second list saying the same is a second thing a subclass has to keep true
        — the more so because a view over this keeps a list of its own rows, and
        two attributes of one name on one object is exactly the collision a
        primitive should not be able to cause.

        Every item but the last, which is the stretch: see `__init__`.
        """
        return tuple(
            self._column.itemAt(i).widget() for i in range(self._column.count() - 1)
        )

    def clear(self) -> None:
        """Drop every card. Deleted and not merely taken out of the layout: a
        card removed from the column is still a child of the ground, and a child
        with no layout to place it keeps painting itself at whatever geometry it
        last had."""
        for card in self.cards():
            self._column.removeWidget(card)
            card.deleteLater()

    def ensure_visible(self, card: QWidget) -> None:
        """Scroll until this card is in the pane. The one thing the view asks of
        the scroll, because the view is what moved the selection."""
        self._scroll.ensureWidgetVisible(card)

    def _restyle(self) -> None:
        """This stack's sheet again in the palette now in use.

        The cards are not touched. Each is subscribed to `CHANGED` itself, which
        is what lets a stack rebuild its column without redressing anything — a
        stack that dressed its children would have to do it again on every
        rebuild, and would be dressing widgets it does not know the shape of.
        """
        self.setStyleSheet(sheet())
