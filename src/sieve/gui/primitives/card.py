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

The dress is the one settled in `mockup/paper_cards.py`, in this tree's colour
roles rather than that file's fixed light palette: a rounded panel on the ground,
a head with no fill of its own under a rule that is measured off the title, the
body under it, and a meter closing the card at its foot. What the mockup calls
white and near-white are `PANEL` and `STACK_BG` here, so the same card is a white
one on `paper` and a dark one on `slate` without the geometry moving.

Three of those four are geometry a stylesheet cannot express, which is why this
card paints itself where the older one wore a sheet: the rule's *length* is the
width of this card's own title and no sheet can measure a sibling widget, the
meter has to be clipped by the rounded corner it sits in, and the corner is only
round because something rounds it. The sheet that is left dresses the title and
the buttons' geometry — the parts that are text and boxes, which is what a sheet
is good at.

Hover and selection are both on the card's edge here, told apart by colour, and
that is a departure from the split `project_list/card.py` and `primitives/nav.py`
make — fill for the pointer, edge for the selection. It is the mockup's own
decision and the reason is the verbs: the pointer's arrival already lights four
icons on this card and nothing else on screen, which is a louder answer than a
fill, and a card that also changed fill would be answering twice. The two states
still cannot be confused, because a hovered edge is a step off `LINE` toward the
ink and a selected one is the accent.

The verbs are hidden until the pointer arrives, through an opacity effect and not
through `setVisible`: hiding them would collapse the head's height and walk the
title's rule sideways every time the pointer left. What that costs is the old
thing hover costs — a verb nobody hovers is a verb nobody finds — and what buys
it back is that the current card keeps its verbs shown whether or not the pointer
is on it.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal, SignalInstance
from PySide6.QtGui import QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLayout,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from sieve.gui import icons, metrics, palette
from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, TEXT, rgb
from sieve.gui.primitives import meter

#: The card's corner is `metrics.radius()` and no longer a number here. The
#: argument for the 6 it defaults to is still the card's — small enough to read
#: as a cut corner rather than as a pill, which is what keeps a column of twenty
#: of them looking like a stack of cards and not a stack of buttons — but it is
#: an argument for a default rather than for the only value allowed, and it is
#: made in `metrics.py` beside the range it bounds. Read in `paintEvent` and
#: never held: see that module on why a size is asked for and a colour is not.

#: Where the head and the body hold their contents off the card's edge, and so
#: also where the rule under the head starts: the rule, the title and every knob
#: name below stand on one x, and a card is read down that x.
_INSET = 8

#: How far the rule runs past the end of the title, and how much air is left
#: between the two. The rule is the title's underline and not the head's
#: divider — it ends with the name rather than at the card's far edge, so a card
#: whose name is short is visibly a card whose name is short.
_RULE_PAST = 26
_RULE_H = 1
_RULE_PAD = 2

#: How tall the meter across the foot is, and how it is drawn — both now
#: `meter.py`'s, which is where the argument for the four pixels moved when the
#: table turned out to want the same bar in a cell. What is left here is whether
#: there is a foot at all, which is the card's.

#: How far the hovered edge moves off `LINE` toward the ink, through
#: `palette.mix` — see there for why a hover is a step between two roles rather
#: than a ninth colour. The fraction is the one the mockup's two greys sit at,
#: which is small on purpose: the pointer's real answer is the four icons
#: appearing, and the edge is only confirming it.
_HOVER_EDGE = 0.22

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
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Asked for explicitly rather than left to the `:hover` rule that used to
        # imply it: the hover state is now something this widget paints, so it
        # has to be something this widget is told about.
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self._pinned = False
        self._selected = False
        self._hovered = False
        self._meter: float | None = None

        #: The chassis takes no margins of its own — the head and the body each
        #: give themselves back the inset they want, which is what lets the rule
        #: and the meter run to the card's edges while the text does not.
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)

        self._head = QWidget()
        head = QHBoxLayout(self._head)
        head.setContentsMargins(_INSET, 6, 6, _RULE_PAD)
        head.setSpacing(4)
        self._title = QLabel(title)
        self._title.setObjectName("title")
        head.addWidget(self._title)
        # A stretch after the title rather than the title taking the row's
        # remainder: the rule is measured off the title's right edge, and a label
        # stretched to the head's width would draw it to the card's far side on
        # every card, which is the divider this rule is not.
        head.addStretch(1)

        self._open = self._button(_OPEN, "open", "Open this card's settings", self.opened)
        self._swap = self._button(_SWAP, "swap", "Swap for another tool", self.swapped)
        self._pin = self._button(_PIN, "pin", "Pin below the canvas", self.pinned)
        self._remove = self._button(_REMOVE, "remove", "Remove this", self.removed)
        self._verbs = QWidget()
        row = QHBoxLayout(self._verbs)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        for button in (self._open, self._swap, self._pin, self._remove):
            row.addWidget(button)
        head.addWidget(self._verbs)

        self._fade = QGraphicsOpacityEffect(self._verbs)
        self._fade.setOpacity(0.0)
        self._verbs.setGraphicsEffect(self._fade)
        column.addWidget(self._head)

        #: What the view fills. Rows go here rather than on the card's own
        #: layout, so the head stays the first thing in the column no matter
        #: what order a caller builds in. It carries the card's inset itself,
        #: which a card with no rows in it still pays as its bottom margin.
        self._body = QVBoxLayout()
        self._body.setContentsMargins(_INSET, 8, _INSET, 8)
        self._body.setSpacing(4)
        column.addLayout(self._body)

        self._dress()
        palette.CHANGED.connect(self._restyle)
        metrics.CHANGED.connect(self._remeasure)

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
        """The name, and with it the length of the rule under it."""
        self._title.setText(title)
        self.update()

    # -- what it wears -----------------------------------------------------

    def set_selected(self, selected: bool) -> None:
        """Wear the accent edge, and keep the verbs shown while it does.

        The current card holds its verbs whether or not the pointer is on it,
        which is what makes them reachable without a hunt: the card the user is
        acting on is the card whose actions are on offer.
        """
        self._selected = selected
        self._fade.setOpacity(1.0 if (selected or self._hovered) else 0.0)
        self.update()

    def is_selected(self) -> bool:
        return self._selected

    def set_meter(self, full: float | None) -> None:
        """How far along whatever this card holds has got, or `None` for a card
        that is not measuring anything.

        `None` is not zero, and the difference is four pixels of card: a card
        with no meter has no foot at all rather than an empty groove, so the
        cards that measure something are the only ones that look like they do.
        """
        self._meter = None if full is None else max(0.0, min(1.0, full))
        room = meter.HEIGHT if self._meter is not None else 0
        self.layout().setContentsMargins(0, 0, 0, room)
        self.update()

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
        """The half of the card a sheet can still say.

        What is left here is text and box geometry. The card's fill, its edge,
        the rule and the meter have all moved into `paintEvent`, and a rule for
        any of them left behind would read as the thing still setting them.

        The buttons take no colour here either. A stylesheet's `color:` reaches
        text and an icon is a pixmap, so what a `QToolButton:hover` rule used to
        do is three pixmaps in the one `QIcon` and Qt's own choice between them.
        """
        self.setStyleSheet(f"""
            #title {{
                color: {rgb(TEXT)};
                font-size: {metrics.pt("name")}pt;
                font-weight: 600;
            }}
            QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
        """)

    def _restyle(self) -> None:
        """The sheet again in the palette now in use, the icons drawn again with
        it, and a repaint for everything this card draws itself.

        The icons are the half a sheet cannot reach. A `QIcon` is three pixmaps
        drawn at the colours the palette held when the button was built, so a
        card that only re-set its stylesheet would come back in the new greys
        wearing the old palette's glyphs. The pin goes through `set_pinned`
        rather than being rebuilt here, because its colour is its state and only
        that verb knows both.

        What `paintEvent` uses needs no help: those are the role objects
        themselves, mutated in place, so the card has only to be asked to paint.
        """
        for button, glyph in (
            (self._open, _OPEN),
            (self._swap, _SWAP),
            (self._remove, _REMOVE),
        ):
            button.setIcon(icons.icon(glyph))
        self.set_pinned(self._pinned)
        self._dress()
        self.update()

    def _remeasure(self) -> None:
        """The sheet again at the size now in force, and a repaint for the corner.

        Its own slot rather than `_restyle`, and the difference is the icons.
        Those are pixmaps drawn at the palette's colours, so a colour change has
        to redraw all four; a size change does not touch them, and a card that
        answered both signals in one slot would redraw every icon in the tree
        each time a slider moved one point.
        """
        self._dress()
        self.update()

    # -- what it draws -----------------------------------------------------

    def paintEvent(self, event) -> None:
        """Fill, meter, rule, edge — in that order, and none of them from a sheet.

        `QFrame`'s own paint is not called: nothing in the sheet dresses `#card`
        any more, so there is nothing left for it to draw. The children paint
        after this either way, which is what keeps the head's text over the fill
        and not under it.
        """
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # Half a pixel in on every side: a 1px pen straddles the path it is given,
        # so a border drawn on the widget's own rect loses its outer half to the
        # edge of the widget and comes back looking like half a line.
        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        corner = metrics.radius()
        shape = QPainterPath()
        shape.addRoundedRect(box, corner, corner)
        painter.fillPath(shape, PANEL)

        if self._meter is not None:
            # Clipped by the shape, because the foot runs into two rounded
            # corners and a rectangle drawn there would put square ends outside
            # the card it is the foot of. Which is also why the ends are square:
            # this bar has no corner of its own, and the one it wears is the
            # card's — `meter.py` on which shape says which thing.
            painter.save()
            painter.setClipPath(shape)
            meter.draw(
                painter,
                QRectF(box.left(), box.bottom() - meter.HEIGHT, box.width(), meter.HEIGHT),
                self._meter,
                # Accent only on the current card. The accent means *this is what
                # you are acting on*, and a column of twenty cards each with an
                # accent stripe along its bottom spends that meaning on twenty
                # things at once; dim against the groove is still a readable
                # length.
                current=self._selected,
                round_ends=False,
            )
            painter.restore()

        # The rule: from the card's inset to `_RULE_PAST` past the title, and
        # never past the inset on the far side — a card narrow enough for those
        # two to cross would otherwise draw a rule running out of its own edge.
        y = self._head.geometry().bottom() + 0.5
        end = self._title.mapTo(self, self._title.rect().topRight()).x() + _RULE_PAST
        painter.setPen(QPen(LINE, _RULE_H))
        painter.drawLine(
            QPointF(_INSET, y), QPointF(min(end, box.right() - _INSET), y)
        )

        if self._selected:
            edge = ACCENT
        elif self._hovered:
            edge = palette.mix(LINE, TEXT, _HOVER_EDGE)
        else:
            edge = LINE
        painter.setPen(QPen(edge, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(shape)
        painter.end()

    # -- what the pointer does ---------------------------------------------

    def enterEvent(self, event) -> None:
        self._hovered = True
        self._fade.setOpacity(1.0)
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """The pointer left the card — which moving onto one of its own buttons
        is not: Qt sends `Leave` only up to the common ancestor of where the
        pointer was and where it now is, and for a verb on this card that
        ancestor is this card."""
        self._hovered = False
        self._fade.setOpacity(1.0 if self._selected else 0.0)
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.opened.emit()
        super().mouseDoubleClickEvent(event)
