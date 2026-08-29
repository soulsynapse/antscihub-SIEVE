"""The looks laid out one under another, each shown selected and not.

Every look is drawn twice, side by side, because half of what separates these is
what selection does to the card and a gallery of one state each cannot show it —
`fill, not edge` and `flat` are arguments about that state and nothing else, and
in a single-state gallery they would look like arguments about a border. Two
states is also the only way to read `collapsed until current`, whose whole claim
is that the resting card is shorter than the current one.

The real card stands at the top, unmodified. A gallery whose baseline is a
redrawing of the thing it is compared against drifts from it silently: the
comparison keeps working, against a card the application does not have. So the
first row is `primitives/card.py` itself, and `look.py`'s `as built, redrawn` is
the second — the two sitting one above the other is what makes a drift visible
instead of hidden.

The column, the ground it is drawn on and the block each look sits in are the
bench's (`gallery.py`), which is what leaves this file holding only the pair.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from sieve.gui import palette
from sieve.gui.palette import DIM, rgb
from sieve.gui.primitives import Card
from sieve.gui.view.dev.gallery import GUTTER, Gallery, Variant
from sieve.gui.view.dev.card_mockups.look import (
    KNOBS,
    LOOKS,
    TITLE,
    Look,
    MockCard,
    line,
)

#: How wide a mock card is drawn. Fixed, so the row compares looks at one
#: width: how a title elides and how four icons crowd a head are both answers
#: to a width. Near what the right pane gives a card at an even split.
_CARD = 300


class CardMockups(Gallery):
    """Every candidate card, drawn beside the one the application has."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            (
                Variant(
                    "the card as built",
                    "`primitives/card.py` itself, not a drawing of it — every "
                    "look below is a change from this",
                    _real_pair(),
                ),
                *(
                    Variant(look.name, look.gloss, _mock_pair(look))
                    for look in LOOKS
                ),
            ),
            parent,
        )


def _row(left: QWidget, right: QWidget) -> QWidget:
    """The pair, at rest and selected, with the labels saying which is which.

    Both fixed to `_CARD` and a stretch after them rather than the two sharing
    the row: the width is part of what is being judged, and a pair that grew
    with the bench would be judged at a width no pane will ever give it.

    Height is the opposite bargain — each card keeps its own, pinned to the top
    of the row. A look whose selected card is taller than its resting one is a
    look making an argument about height, and a row that stretched the shorter
    of the two to match would erase exactly that argument.
    """
    for card in (left, right):
        card.setFixedWidth(_CARD)

    at_rest = QLabel("at rest")
    at_rest.setObjectName("vgloss")
    current = QLabel("current")
    current.setObjectName("vgloss")

    labels = QHBoxLayout()
    labels.setSpacing(GUTTER)
    labels.addWidget(at_rest, 0)
    labels.addSpacing(_CARD - at_rest.sizeHint().width())
    labels.addWidget(current, 0)
    labels.addStretch(1)

    cards = QHBoxLayout()
    cards.setSpacing(GUTTER)
    cards.addWidget(left, 0, Qt.AlignmentFlag.AlignTop)
    cards.addWidget(right, 0, Qt.AlignmentFlag.AlignTop)
    cards.addStretch(1)

    pair = QWidget()
    stack = QVBoxLayout(pair)
    stack.setContentsMargins(0, 0, 0, 0)
    stack.setSpacing(2)
    stack.addLayout(labels)
    stack.addLayout(cards)
    return pair


def _real_pair() -> QWidget:
    """The application's own card, twice, holding what the mocks hold.

    Its title and rows are what a view fills, so the gallery fills them from
    `look.py`'s own `TITLE` and `KNOBS` — a baseline showing different content
    would make every difference below ambiguous between look and content, and a
    baseline holding its own copy of the step is a baseline that can come to
    differ from the mocks by one edit nobody made twice.
    """
    return _row(_real_card(False), _real_card(True))


def _real_card(selected: bool) -> Card:
    card = Card(TITLE)
    card.set_selected(selected)
    for knob in KNOBS:
        card.add_row(_BodyLine(line(knob)))
    return card


class _BodyLine(QLabel):
    """One line of the baseline card's body, in the quiet ink.

    The real card's sheet dresses `#title` and leaves the body to the view, so
    the gallery is what says what a body line looks like — as the chain will
    have to when it fills one. A class rather than a `setStyleSheet` on a plain
    label because that sheet is a string built from a colour that changes: the
    line has to be something with a slot to hear about it.
    """

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._restyle()
        palette.CHANGED.connect(self._restyle)

    def _restyle(self) -> None:
        self.setStyleSheet(f"color: {rgb(DIM)};")


def _mock_pair(look: Look) -> QWidget:
    return _row(MockCard(look, False), MockCard(look, True))
