"""The checkbox and the radio: one box, ticked or not, with its label beside it.

Lifted from `mockup/paper_primitives.py`, and the fourth control after
`button.py`, `field.py` and `slider.py`. It arrives the way the first two did
rather than the way the slider did — ahead of a view asking — and the budget it
settles is the one those two do not: what *on* looks like. Emphasis is spent by
the buttons, focus by the field, and a tick is neither; it is the mark that says
a thing the user set is set, and the first view to draw a write list would
otherwise be deciding for every list of facts after it.

The tick is painted and not styled, and that is a Qt fact rather than a taste.
`QCheckBox::indicator` takes its whole appearance from an `image:` the moment the
sheet touches it, so a tick in the accent means shipping a bitmap per state, and
a bitmap does not follow a palette the user changes mid-run — the icons in
`card.py` have to be redrawn on `palette.CHANGED` for exactly that reason, and
those are drawings a view chose rather than a shape this file knows how to make.
A painted tick is three line segments that read the live roles at the moment of
drawing and need nothing said to them at all.

The checkbox and the radio are one class with a corner as the difference,
because that is what the difference is: the same box, the same fill, the same
tick position, drawn round rather than square and with a dot in place of the
tick. Two classes would be two drawings of one thing, free to drift, and the
thing that actually differs — that a radio is one of a set and a checkbox is not
— is Qt's `autoExclusive` and is set from the same flag. Which of the two a view
wants is the question the mockup answers: a checkbox states a fact about what is
written, a radio picks one of a fixed few, and neither performs an action.

What is missing is the mockup's switch, and it is missing rather than deferred by
accident. A switch means *this takes effect the moment you flip it*, which is a
promise about what happens after the click and therefore a claim only a view
holding a live thing can make; there is no such view in this tree yet, and a
switch offered before there is one is an invitation to use it where a checkbox is
meant. When the scrubber's handles land, that is the file to add.

Three roles are borrowed rather than restated, each from where it is argued.
The resting edge is `field.EDGE` — a checkbox is a control the user may change
and takes the same step off `LINE` a field's border does, which is the whole of
what "editable" is made of in this tree. The focus ring is `field.ring()` at
`field.RING_W`: a box that is already accent-filled has nothing left to say with
its border, the reflow argument against thickening it holds here as it does
there, and this widget paints itself, so it needs no `Field` around it to get a
ring drawn outside the box. The checked fill answers the pointer by
`button.HOVER`, the step every filled thing in the tree takes.

The tick's ink is `PANEL`, derived the way `button.py` derives its filled label:
every palette commits to an accent clearing 4.5:1 against `panel`, so the panel
colour laid on the accent is legible by the same guarantee in all of them, and a
white named here would be right in most and unreadable in two.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QAbstractButton, QSizePolicy, QWidget

from sieve.gui import metrics, palette
from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, PANEL_HOT, TEXT, mix
from sieve.gui.primitives.button import HOVER
from sieve.gui.primitives.field import EDGE, EDGE_HOVER, RING_W, ring

#: The box, its corner, and the dot a radio wears instead of a tick. Fourteen is
#: the size at which the tick inside is three segments rather than a smudge, and
#: it is a fixed number and not a multiple of the text size: a box that grew with
#: the type would put a different amount of air around the same tick at every
#: size, and this is a mark rather than a letter. The corner is this file's, for
#: `button.py`'s reason — `metrics.radius()` is *card corners*, and a user
#: squaring off their cards did not ask for square checkboxes.
_BOX = 14
_RADIUS = 3
_DOT = 3.0

#: The air the ring is drawn in, on every side of the box. `field.RING_GAP` is
#: the same room taken as a layout margin by the wrapper that paints it there;
#: here it is part of this widget's own rect, since there is no wrapper.
_ROOM = RING_W

#: Between the box and the label. Wide enough that the two are a box and its
#: name rather than a box with a word jammed against it, and narrow enough that
#: a column of them still reads as one column.
_GAP = 8

#: How thick the tick is drawn. Rounded at its ends and its join, so the three
#: segments are one stroke and not a bent wire — at 14px the join is what the eye
#: actually sees.
_TICK_W = 1.8


class Check(QAbstractButton):
    """A box and its label — square and independent, or round and one of a set.

    It knows what it looks like and what it is at, and nothing about what being
    ticked means: `toggled` is the caller's, the same split every primitive here
    makes.

    A radio is exclusive among its siblings, which is Qt's own `autoExclusive`
    and so is scoped to the parent widget they share. A view wanting two
    independent sets of radios gives each set a holder, the same as it would with
    Qt's own — this file adds no group of its own, since a group that was not
    Qt's would be a second answer to a question `QButtonGroup` already has.
    """

    def __init__(
        self,
        text: str = "",
        *,
        radio: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setText(text)
        self._radio = radio
        self._hovered = False
        self.setCheckable(True)
        self.setAutoExclusive(radio)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        # Asked for explicitly, as `card.py` does: hover is something this widget
        # paints, so it has to be something this widget is told about.
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        # As wide as its label and no taller than its own row: a check stands in
        # a column of them, and one that stretched would put its box somewhere
        # other than where the box above it is.
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._resize()
        # A bound method and never a lambda, for the reason `button.py` gives:
        # PySide6 drops a connection to a bound method when the receiver goes,
        # where a lambda closing over `self` would keep a dead check subscribed.
        palette.CHANGED.connect(self.update)
        metrics.CHANGED.connect(self._resize)

    def is_radio(self) -> bool:
        """Which of the two this is, for a caller that built a row of them from
        data and has to read back what it made."""
        return self._radio

    def sizeHint(self) -> QSize:
        """The box, the gap, and the label — measured rather than guessed.

        The height is the taller of the box in its ring and the line of text, so
        a check keeps its own row whichever of the two the user's type size makes
        larger.
        """
        text = self.fontMetrics()
        width = _ROOM + _BOX + _ROOM
        if self.text():
            width += _GAP + text.horizontalAdvance(self.text())
        return QSize(width, max(_BOX + 2 * _ROOM, text.height()))

    def minimumSizeHint(self) -> QSize:
        """The box alone. A label may be elided by whatever holds this; the mark
        that carries the state may not, so it is the floor."""
        return QSize(_ROOM + _BOX + _ROOM, max(_BOX + 2 * _ROOM, self.fontMetrics().height()))

    def _resize(self) -> None:
        """The font at the size now in force, and the room that needs.

        Its own slot rather than a repaint, and that is the difference from
        `palette.CHANGED`: a colour changes what this is drawn in, where a size
        changes how much of the row it takes — so the layout has to be told, and
        `updateGeometry` is how. The text is painted here rather than set on a
        child label, so nothing else picks the size up on its own.
        """
        font = self.font()
        font.setPointSize(metrics.pt("name"))
        self.setFont(font)
        self.updateGeometry()
        self.update()

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        """Ring, box, mark, label — in that order, and none of them from a sheet.

        The ring is first because it is drawn outside the box and the box paints
        over the half of it that falls inside, which is what makes it abut the
        edge rather than sit on it — the same bargain `field.py` strikes by
        drawing the ring before the control repaints itself.
        """
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Half a pixel in on every side, for `card.py`'s reason: a 1px pen
        # straddles the path it is given, so an edge drawn on the box's own rect
        # loses its outer half and comes back looking like half a line.
        top = (self.height() - _BOX) / 2
        box = QRectF(_ROOM, top, _BOX, _BOX).adjusted(0.5, 0.5, -0.5, -0.5)
        corner = _BOX if self._radio else _RADIUS
        shape = QPainterPath()
        shape.addRoundedRect(box, corner, corner)

        if self.hasFocus():
            inset = RING_W / 2
            painter.setPen(QPen(ring(), RING_W))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(
                box.adjusted(-inset, -inset, inset, inset),
                corner + inset,
                corner + inset,
            )

        painter.fillPath(shape, self._fill())
        painter.setPen(QPen(self._edge(), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(shape)

        if self.isChecked():
            self._mark(painter, box)

        if self.text():
            painter.setPen(QPen(TEXT if self.isEnabled() else DIM))
            painter.drawText(
                QRectF(_ROOM + _BOX + _GAP, 0, self.width(), self.height()),
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                self.text(),
            )
        painter.end()

    def _mark(self, painter: QPainter, box: QRectF) -> None:
        """The tick or the dot, in the ink the fill guarantees is legible on it.

        The tick's three points are fractions of the box rather than pixels off
        its corners, so the one number above that sets the box's size is the one
        number that has to move if it is ever redrawn larger.
        """
        ink = PANEL if self.isEnabled() else DIM
        if self._radio:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(ink)
            painter.drawEllipse(box.center(), _DOT, _DOT)
            return
        side = box.width()
        tick = QPainterPath(QPointF(box.left() + side * 0.24, box.top() + side * 0.52))
        tick.lineTo(box.left() + side * 0.42, box.top() + side * 0.72)
        tick.lineTo(box.left() + side * 0.77, box.top() + side * 0.30)
        pen = QPen(ink, _TICK_W)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(tick)

    def _fill(self) -> QColor:
        """What is inside the box.

        `PANEL` when it is empty and not `PANEL_HOT`: an unticked box standing on
        a card is then the same colour as the card and told apart by its edge
        alone, which is `field.py`'s first claim about what makes a control look
        editable — a lighter fill would make it a small `SUBTLE` button.

        Off is flat, the way a disabled `Button` is: `PANEL_HOT` whether or not it
        is ticked, so a set of checks nobody may change looks like one state
        rather than two.
        """
        if not self.isEnabled():
            return PANEL_HOT
        if not self.isChecked():
            return PANEL
        return mix(ACCENT, TEXT, HOVER) if self._hovered else ACCENT

    def _edge(self) -> QColor:
        """The box's own line — the accent when it is ticked, because the fill is
        the accent and an edge in anything else would be a hairline of the old
        state around the new one."""
        if not self.isEnabled():
            return LINE
        if self.isChecked():
            return self._fill()
        return mix(LINE, TEXT, EDGE_HOVER if self._hovered else EDGE)
