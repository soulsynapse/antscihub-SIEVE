"""What a rebuilt stack carries over from the pane it replaces.

Both stacks — the shelf and the chain — are rebuilt whole on every move, because
the selection is drawn into the cards rather than pushed onto them
(`project_select.py`, `chain_stack.py`). So anything the pane knows that the
document does not dies with the widget, and the scroll offset is the whole of
that: a stack that says nothing about where it was leaves a long library at the
top of the list after every arrow key, with the accent it just moved somewhere
below the fold.

Two handles rather than a rebuild that mutates in place. Which cards a stack has
and which of them is current are the window's answers and arrive by
construction; where the user had scrolled to is the pane's own, and these are
what the window carries across the swap (`control.py`) and what it aims once the
new pane is laid out.

Re-homed from the referent's `_StackPane` (`mockup/mockup.py`), which
`adr/a-position-is-asked-for-in-the-chain.md` makes binding on how the surface
responds — the aim below is its decision rather than one taken here.

A pane with no current card is not one of these. The step position is one node's
form and has no selection to bring into view, so it is replaced without either
handle rather than given ones that would only ever answer `None`.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QScrollArea, QWidget

#: Left above and below a card brought into view, so what comes into view with
#: it is the gap the edges are drawn in rather than the neighbour's border
#: exactly. A revealed card that ended flush with the viewport would read as the
#: end of the stack.
_REVEAL_MARGIN = 20


class StackPane(QWidget):
    """A position whose body is a scrolling stack of cards, one of them current.

    Both are set by the subclass once its scroll area and its cards are built,
    for `ChainColumn.cards`' reason: what this reads is where they landed, and it
    has no part in putting them there.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.scroll: QScrollArea | None = None
        self.current_card: QWidget | None = None

    def offset(self) -> int:
        """Where this pane is scrolled to, or the top for a pane with no scroll."""
        return 0 if self.scroll is None else self.scroll.verticalScrollBar().value()

    def scroll_to(self, value: int) -> None:
        """Where the pane this one replaces was.

        Clamped by the bar itself, which is what makes a rebuild that shortened
        the stack — a step removed, a library rescanned — land legally without
        this knowing either happened.
        """
        if self.scroll is not None:
            self.scroll.verticalScrollBar().setValue(value)

    def reveal_current(self) -> None:
        """Bring the selected card into view, moving as little as possible.

        Not `ensureWidgetVisible`: a card taller than the viewport is centred by
        that, and a card is read from its head — the number, the title and the
        buttons are all in the first line, and the accent edge only says which
        card is current if the card is recognisable. So a card that cannot fit is
        aligned to its top, and one that fits is scrolled to whichever edge it is
        past. A card already in view moves nothing, which is what keeps a click on
        a visible card from scrolling the stack under the pointer.
        """
        if self.scroll is None or self.current_card is None:
            return
        bar = self.scroll.verticalScrollBar()
        top = self.current_card.mapTo(self.scroll.widget(), QPoint(0, 0)).y()
        height = self.current_card.height()
        view = self.scroll.viewport().height()
        if height + 2 * _REVEAL_MARGIN >= view or top - _REVEAL_MARGIN < bar.value():
            bar.setValue(top - _REVEAL_MARGIN)
        elif top + height + _REVEAL_MARGIN > bar.value() + view:
            bar.setValue(top + height + _REVEAL_MARGIN - view)
