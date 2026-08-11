"""The card: a titled panel with the four verbs that act on what it holds.

The four are the mockup's chain card, lifted out of it — open its settings, swap
what stands here, pin it below the canvas, drop it. They are in that order on
every card and in that order whether or not the card can take them, because the
position of an icon is how it is found on the twentieth card as much as the
first: a card that cannot be removed offers a disabled ✕ with a tooltip saying
why, rather than a gap that shifts the other three left.

The card emits and does not act. `removed` says the user asked; what a removal
does to the chain, the library, or the disk is the view's, which is what lets
the same widget stand in a list of projects and in a stack of steps.

Selection is an accent edge down the leading side rather than a fill, so a card
that is current and a card that is hovered are never the same picture — the fill
is the pointer's answer and the edge is the selection's, and both can be true at
once (`project_list/card.py` and `primitives/nav.py` make the same split).

The card paints nothing itself and wears a stylesheet scoped to its own widget,
so the rules reach the labels and buttons inside it and nothing outside.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal, SignalInstance
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from sieve.gui import icons
from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, PANEL_HOT, TEXT, rgb

#: How wide the selected card's leading edge is. Wide enough to read from the
#: far side of the pane without the card's contents moving when it appears —
#: which is why the edge is on every card and only its colour changes.
_EDGE = 3

#: Which lucide icon each verb wears, pinned to the names the card knows them by
#: rather than spelled at each use. `pin` appears once and not twice: pinned is
#: the same shape with its inside filled, so the two states cannot drift apart
#: into two drawings of one thing.
_OPEN = "arrow-right"
_SWAP = "arrow-right-left"
_PIN = "pin"
_REMOVE = "x"


class Card(QFrame):
    """A panel with a title, four icons, and room under them for anything.

    Handed its title and its body rather than building either: what a card is
    about is the view's, and a card that reached for a step or a project would
    be the one file where two views' contents met.
    """

    #: The card was chosen — clicked, or arrowed onto. Selection belongs to
    #: whatever holds the cards, since only that knows there is exactly one, so
    #: the card asks rather than marking itself.
    selected = Signal()

    #: Take the selection forward into this card's settings: the → , or the
    #: second click of a double. Same verb from both.
    opened = Signal()

    #: Offer what else could stand where this stands. The card does not know the
    #: shortlist and does not open the box that shows it.
    swapped = Signal()

    #: Pin this card's output below the canvas. Emitted only when it is not
    #: already pinned — the pinned card's ◆ is disabled, so the signal always
    #: means a change.
    pinned = Signal()

    #: Drop what this card holds. Emitted only when the card is removable.
    removed = Signal()

    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pinned = False
        self._selected = False

        column = QVBoxLayout(self)
        column.setContentsMargins(8, 6, 8, 8)
        column.setSpacing(4)

        self._title = QLabel(title)
        self._title.setObjectName("title")

        head = QHBoxLayout()
        head.setSpacing(4)
        head.addWidget(self._title)
        head.addStretch(1)
        self._open = self._button(_OPEN, "open", "Open this card's settings", self.opened)
        self._swap = self._button(_SWAP, "swap", "Swap for another tool", self.swapped)
        self._pin = self._button(_PIN, "pin", "Pin below the canvas", self.pinned)
        self._remove = self._button(_REMOVE, "remove", "Remove this", self.removed)
        for button in (self._open, self._swap, self._pin, self._remove):
            head.addWidget(button)
        column.addLayout(head)

        #: What the view fills. Rows go here rather than on the card's own
        #: layout, so the head stays the first thing in the column no matter
        #: what order a caller builds in.
        self._body = QVBoxLayout()
        self._body.setSpacing(4)
        column.addLayout(self._body)

        self._dress()

    def _button(
        self, glyph: str, name: str, tip: str, signal: SignalInstance
    ) -> QToolButton:
        button = QToolButton()
        button.setObjectName(name)
        button.setIcon(icons.icon(glyph))
        button.setIconSize(QSize(icons.SIZE, icons.SIZE))
        button.setAutoRaise(True)
        button.setToolTip(tip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        # The icons act on what the card holds, not on the selection, so a click
        # on one is not also a click that selects — `mousePressEvent` never sees
        # it, and a user who pins the third card is still standing on the first.
        button.clicked.connect(signal)
        return button

    # -- what it holds -----------------------------------------------------

    def body(self) -> QVBoxLayout:
        """The room under the head, for the caller to fill."""
        return self._body

    def add_row(self, row: QWidget | QLayout) -> None:
        """One more line in the body, widget or layout — a knob row is usually
        the second and the card should not make the caller know which."""
        if isinstance(row, QLayout):
            self._body.addLayout(row)
        else:
            self._body.addWidget(row)

    def set_title(self, title: str) -> None:
        self._title.setText(title)

    # -- what it wears -----------------------------------------------------

    def set_selected(self, selected: bool) -> None:
        """Wear the accent edge, or give it back."""
        self._selected = selected
        self._dress()

    def is_selected(self) -> bool:
        return self._selected

    def set_pinned(self, pinned: bool) -> None:
        """Filled and accented when pinned, and disabled with it: the button is
        the pin's state as well as the way to set it, and a pinned card that
        still offered the click would be offering a no-op.

        Which is why the pinned icon hands the accent to `disabled` as well as
        to `normal`. A disabled button is drawn in `Disabled` mode and nowhere
        else, so a pin that only accented its `normal` pixmap would go grey at
        the moment it became the pinned one — the state saying least where it
        matters most.
        """
        self._pinned = pinned
        ink = ACCENT if pinned else DIM
        self._pin.setIcon(
            icons.icon(_PIN, normal=ink, disabled=ink if pinned else LINE, filled=pinned)
        )
        self._pin.setEnabled(not pinned)
        self._pin.setToolTip(
            "Already pinned below the canvas" if pinned else "Pin below the canvas"
        )
        self._dress()

    def is_pinned(self) -> bool:
        return self._pinned

    def set_removable(self, removable: bool, reason: str = "") -> None:
        """Offer the ✕ or refuse it in place. `reason` is what the refusal says —
        a disabled button with the tooltip it had when it worked tells the user
        what it would do and not why it will not."""
        self._remove.setEnabled(removable)
        self._remove.setToolTip("Remove this" if removable else reason)

    def set_swappable(self, swappable: bool, reason: str = "") -> None:
        """Same bargain as `set_removable`, for ⇄."""
        self._swap.setEnabled(swappable)
        self._swap.setToolTip("Swap for another tool" if swappable else reason)

    def _dress(self) -> None:
        """Re-set the sheet rather than toggling a dynamic property: a property
        would need an unpolish/polish pair to take, and this is one string on
        one widget.

        The buttons take no colour here. A stylesheet's `color:` reaches text
        and an icon is a pixmap, so what a `QToolButton:hover` rule used to do
        is now three pixmaps in the one `QIcon` and Qt's own choice between
        them; leaving a dead rule behind would read as the thing still setting
        the colour. The sheet keeps their geometry, which is still its.
        """
        edge = ACCENT if self._selected else PANEL
        self.setStyleSheet(f"""
            #card {{
                background: {rgb(PANEL)};
                border: 1px solid {rgb(LINE)};
                border-left: {_EDGE}px solid {rgb(edge)};
            }}
            #card:hover {{ background: {rgb(PANEL_HOT)}; }}
            #title {{ color: {rgb(TEXT)}; font-weight: 600; }}
            QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
        """)

    # -- what the pointer does ---------------------------------------------

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.opened.emit()
        super().mouseDoubleClickEvent(event)
