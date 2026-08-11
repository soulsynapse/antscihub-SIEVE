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

The column scrolls, since the looks will outgrow any card the bench stands in
long before the list of them is finished, and a section that fixed its own
height would be a section that decided how many alternatives are allowed.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sieve.gui.palette import DIM, LINE, PANEL, PANEL_HOT, STACK_BG, TEXT, rgb
from sieve.gui.primitives import Card
from sieve.gui.view.dev.card_mockups.look import (
    KNOBS,
    LOOKS,
    TITLE,
    Look,
    MockCard,
    line,
)

#: The gap between looks and the margin around the column, one number for both,
#: for the reason the project list uses one.
_GUTTER = 10

#: How wide a mock card is drawn. Fixed rather than sharing the row's width,
#: because how a title elides and how four icons crowd a head are the things
#: being compared and both are answers to a width — two cards of different
#: widths in one row would be comparing looks and widths at once. Near what the
#: right pane gives a card at an even split, which is where these will be seen.
_CARD = 300


def _sheet() -> str:
    """Scoped to this section's own objects. It is standing inside a card whose
    own sheet is already set on an ancestor, so a bare-class rule here would be
    the second stylesheet reaching the same labels.

    The column is `STACK_BG` and not the panel fill the rest of the bench wears,
    because that is the ground a card is really seen on — the project list
    already stacks its cards on it. Drawn on a panel instead, a look whose
    selected state *is* a panel fill would vanish into the background and the
    gallery would be showing a fault the pane does not have.
    """
    return f"""
        #gallery {{ background: {rgb(STACK_BG)}; border: 1px solid {rgb(LINE)}; }}
        #gscroll {{ background: {rgb(STACK_BG)}; border: 0; }}
        #gcolumn {{ background: {rgb(STACK_BG)}; }}
        #vname {{ color: {rgb(TEXT)}; font-weight: 600; }}
        #vgloss {{ color: {rgb(DIM)}; }}
        #vrule {{ background: {rgb(LINE)}; }}
        QScrollBar:vertical {{
            background: {rgb(STACK_BG)};
            width: 8px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {rgb(LINE)};
            min-height: 24px;
        }}
        QScrollBar::handle:vertical:hover {{ background: {rgb(PANEL_HOT)}; }}
        QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
        QScrollBar::add-page, QScrollBar::sub-page {{ background: {rgb(PANEL)}; }}
    """


class CardMockups(QWidget):
    """Every candidate card, drawn beside the one the application has."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("gallery")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(_sheet())

        column = QWidget()
        column.setObjectName("gcolumn")
        stack = QVBoxLayout(column)
        stack.setContentsMargins(_GUTTER, _GUTTER, _GUTTER, _GUTTER)
        stack.setSpacing(_GUTTER)

        stack.addWidget(
            _variant(
                "the card as built",
                "`primitives/card.py` itself, not a drawing of it — every look "
                "below is a change from this",
                _real_pair(),
            )
        )
        for look in LOOKS:
            stack.addWidget(_variant(look.name, look.gloss, _mock_pair(look)))
        # Last, so a short list sits at the top of the panel rather than spread
        # down whatever height the bench ends up with.
        stack.addStretch(1)

        scroll = QScrollArea()
        scroll.setObjectName("gscroll")
        scroll.setWidget(column)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        body = QVBoxLayout(self)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(scroll)


def _variant(name: str, gloss: str, cards: QWidget) -> QWidget:
    """One look's block: what it is called, what it costs, and the pair."""
    block = QWidget()

    title = QLabel(name)
    title.setObjectName("vname")
    note = QLabel(gloss)
    note.setObjectName("vgloss")
    note.setWordWrap(True)

    rule = QFrame()
    rule.setObjectName("vrule")
    rule.setFixedHeight(1)

    stack = QVBoxLayout(block)
    stack.setContentsMargins(0, 0, 0, 0)
    stack.setSpacing(4)
    stack.addWidget(title)
    stack.addWidget(note)
    stack.addWidget(cards)
    stack.addSpacing(2)
    stack.addWidget(rule)
    return block


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
    labels.setSpacing(_GUTTER)
    labels.addWidget(at_rest, 0)
    labels.addSpacing(_CARD - at_rest.sizeHint().width())
    labels.addWidget(current, 0)
    labels.addStretch(1)

    cards = QHBoxLayout()
    cards.setSpacing(_GUTTER)
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
        label = QLabel(line(knob))
        # The real card's sheet dresses `#title` and leaves the body to the
        # view, so the gallery says what a body line looks like — as the chain
        # will have to when it fills one.
        label.setStyleSheet(f"color: {rgb(DIM)};")
        card.add_row(label)
    return card


def _mock_pair(look: Look) -> QWidget:
    return _row(MockCard(look, False), MockCard(look, True))
