"""Card-look gallery: each look drawn at rest and selected, side by side."""

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
    return _row(_real_card(False), _real_card(True))


def _real_card(selected: bool) -> Card:
    card = Card(TITLE)
    card.set_selected(selected)
    for knob in KNOBS:
        card.add_row(_BodyLine(line(knob)))
    return card


class _BodyLine(QLabel):
    """Body label that reskins on palette change (card sheet only dresses #title)."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._restyle()
        palette.CHANGED.connect(self._restyle)

    def _restyle(self) -> None:
        self.setStyleSheet(f"color: {rgb(DIM)};")


def _mock_pair(look: Look) -> QWidget:
    return _row(MockCard(look, False), MockCard(look, True))
