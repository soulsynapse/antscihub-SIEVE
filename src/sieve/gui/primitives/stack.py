"""Scrolling column of cards on a ground, under a View head."""

from __future__ import annotations

from typing import Iterable

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QFrame,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sieve.gui.palette import LINE, PANEL_HOT, STACK_BG, rgb
from sieve.gui.primitives.view import PAD_X, View
from sieve.gui.primitives.view import sheet as head_sheet

# Margin reuses the head's left inset so cards align with the title.
_GAP = 26
_MARGIN = PAD_X

_BAR_W = 8
_BAR_MIN = 24


def sheet() -> str:
    """Rules for callers that set an ancestor sheet (which would override these)."""
    return head_sheet() + f"""
        #stackscroll {{ background: {rgb(STACK_BG)}; border: 0; }}
        #stackground {{ background: {rgb(STACK_BG)}; }}
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


class _Ground(QWidget):
    """The column the cards stand in, and whatever the stack draws under them.

    It fills its own background rather than taking the sheet's. A stylesheet
    background reaches plain `QWidget` and not a subclass that overrides
    `paintEvent`, and the ground has to be a subclass for anything to be drawn
    between the cards — so the fill is done here, from the same role the sheet
    names. Children paint after their parent, so what is drawn here lands
    behind the cards and shows in the gaps, which is where the chain's edges
    live.
    """

    def __init__(self, stack: "CardStack") -> None:
        super().__init__()
        self._stack = stack

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), STACK_BG)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self._stack.paint_ground(painter)
        painter.end()


class CardStack(View):
    """View holding a scrolling column of cards on a coloured ground."""

    def __init__(
        self,
        title: str = "",
        cards: Iterable[QWidget] = (),
        gap: int = _GAP,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, parent)

        self._ground = _Ground(self)
        self._ground.setObjectName("stackground")
        self._column = QVBoxLayout(self._ground)
        self._column.setContentsMargins(_MARGIN, _MARGIN, _MARGIN, _MARGIN)
        self._column.setSpacing(gap)
        # Stretch stays last; cards insert before it.
        self._column.addStretch(1)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("stackscroll")
        self._scroll.setWidget(self._ground)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.body().addWidget(self._scroll, 1)

        for card in cards:
            self.add_card(card)

        # Re-set after children exist so object-name rules land.
        self._restyle()

    # -- the ground --------------------------------------------------------

    def add_card(self, card: QWidget) -> None:
        """One more card at the foot of the column, above the stretch."""
        self.insert_card(len(self.cards()), card)

    def insert_card(self, index: int, card: QWidget) -> None:
        """Insert a card at *index*, clamped to bounds."""
        self._column.insertWidget(max(0, min(len(self.cards()), index)), card)
        self._ground.update()

    def paint_ground(self, painter: QPainter) -> None:
        """Draw under the cards. Nothing by default; a chain draws its edges."""

    def cards(self) -> tuple[QWidget, ...]:
        """Cards in column order (excludes the trailing stretch)."""
        return tuple(
            self._column.itemAt(i).widget() for i in range(self._column.count() - 1)
        )

    def clear(self) -> None:
        # deleteLater, not just removeWidget — an unplaced child still paints.
        for card in self.cards():
            self._column.removeWidget(card)
            card.deleteLater()
        self._ground.update()

    def ensure_visible(self, card: QWidget) -> None:
        self._scroll.ensureWidgetVisible(card)

    def _sheet(self) -> str:
        return sheet()
