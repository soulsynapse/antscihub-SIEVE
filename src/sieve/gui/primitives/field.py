"""The text field, and the labelled frame with the focus ring around it.

Lifted from `mockup/paper_primitives.py`, and lifted ahead of a view asking for
one for the reason `button.py` was: what a focused control looks like is a
decision made once for the whole application, and the first view to build a text
input would otherwise be the one making it for every view after. Emphasis was
the budget the buttons spend; focus is the one thing on screen the keyboard is
pointing at, and a tree with two answers to *where am I typing* has none.

Two claims, and the file is mostly them.

The first is that a field's edge is one step darker than a card's, and that this
is the whole of what makes it look editable. There is no `field line` role and
there should not be — nine roles is a colour every palette in `palette.py` has to
answer — so the step is taken through `palette.mix`, the same move a hover is,
held permanently rather than only under the pointer. It is a *smaller* step than
`card.py`'s hover so the two cannot be read as each other: a card answering the
pointer moves further than a field standing still, and a field inside a hovered
card is still the quieter edge of the two.

The second is that focus is painted outside the control rather than thickening
its border. A border that grows on focus moves every neighbour by a pixel, and
in the row of five crop fields this exists for that reads as the row twitching
each time Tab is pressed. A stylesheet cannot draw outside a widget's own rect,
so `Field` — the wrapper — is what paints it, and the 3px inset in its layout is
the room the ring lives in. The control also takes the accent on its own border,
which is not redundant with the ring: the ring is a glow at low alpha and says
*here*, the border says *this one*, and a field whose resting edge is already
darkened needs both to move visibly.

A wrapper is how a *styled* control gets one and not what the ring is. `EDGE`,
`RING_W`, `RING_GAP` and `ring()` are public so a widget that paints itself can
draw the same glow inside its own rect without a `Field` around it, which is
what `check.py` does; the argument for each stays here, where it is made.

`Button` recolours its border on focus and paints nothing, and that is the same
decision rather than a different one — a button's box is already the thing being
pointed at, and it is pressed and left rather than typed into.

What is missing is the mockup's invalid state, refused on `button.py`'s grounds:
its red is not one of the eight roles, and a ninth is a colour every palette has
to answer — including the two chosen so the only hue in the scheme is one an
accent-blind user can still find. So a `hint` is offered and drawn in `DIM`,
which says what the field wants; saying that what is in it is wrong waits on
that role being decided. A caller that must refuse a value today refuses it the
way `card.py` refuses a removal — the control goes disabled and the hint says
why — rather than colouring it.

Nothing here names a font family, and the numeric fields the mockup sets in mono
are right-aligned instead. A family is the tree's first, and it belongs beside
the sizes in `metrics.py` rather than invented by whichever file wanted tabular
figures first. Alignment is the half of that treatment that costs no decision.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from sieve.gui import metrics, palette
from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, PANEL_HOT, TEXT, mix, rgb

#: How far a field's edge sits off `LINE` toward the ink at rest, and how much
#: further under the pointer. The first is what "editable" is made of; it is
#: under `card.py`'s hover step on purpose, so the darker edge of a field and the
#: answer a card gives the pointer are never the same colour.
#:
#: Public, because "editable" is not this widget's look — it is the one step that
#: tells a control the user may change from the panel it stands on, and the
#: checkbox in `check.py` has to be made of the same step or the tree would have
#: two answers to it. Named here rather than in a module both import, because
#: this is where the claim is argued and a constant is best read beside its
#: argument.
EDGE = 0.14
EDGE_HOVER = 0.30

#: The ring: how wide, how far outside the control, and how much of the accent it
#: keeps. It is a glow and not a line — at full strength it would be a second
#: border around the first, which is the thickening this exists instead of. The
#: alpha is high enough to read on `panel` in a dark palette, where a fraction
#: tuned on white disappears.
#:
#: Public for the reason `EDGE` is, and more so: focus is the one thing on screen
#: the keyboard is pointing at, so a second glow tuned somewhere else would be a
#: second answer to *where am I*. A widget that paints its own ring — `check.py`
#: does, having no wrapper — draws this one at this width.
RING_W = 3
RING_GAP = 3
_RING_ALPHA = 64

#: The box around the text, and the corner on it. The corner is this file's and
#: not `metrics.radius()`, for `button.py`'s reason: that slider is *card
#: corners*, and a user squaring off their cards did not ask for square fields.
_PAD_X = 8
_PAD_Y = 4
_RADIUS = 4

#: The gap between a label, its control and its hint. Tight, because the three
#: are one thing and the space between fields is what separates them from the
#: next one.
_SPACING = 4


class LineField(QLineEdit):
    """A line of text in the tree's roles, with an optional unit beside it.

    A control and not a wrapper: it is dressed and knows nothing about a label,
    so it can stand in a row, a cell, or a `Field` without any of them being the
    one place it can go. What pressing Return means is `returnPressed` and the
    caller's, the same split every primitive here makes.
    """

    def __init__(
        self,
        text: str = "",
        *,
        numeric: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setObjectName("field")
        self._joined = False
        if numeric:
            # Right, because a number is read from its low digits and a column of
            # them lines up on those. See the module docstring on why this is the
            # whole of the numeric treatment for now.
            self.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._dress()
        # Bound methods and never lambdas, for the reason `button.py` gives:
        # PySide6 drops a connection to a bound method when the receiver goes,
        # where a lambda closing over `self` would keep a dead field subscribed.
        palette.CHANGED.connect(self._dress)
        metrics.CHANGED.connect(self._dress)

    def set_joined(self, joined: bool) -> None:
        """Square the right-hand corners, for a field a unit is butted against.

        Asked of the field rather than overridden from the widget that joins
        them, because it cannot be: Qt merges an ancestor's sheet with a
        widget's own and the widget's own wins the conflict, so a `#field` rule
        set on the holder would lose to the corner set here. The one place that
        states a field's shape is the one that has to state the exception.
        """
        self._joined = joined
        self._dress()

    def _dress(self) -> None:
        """The sheet, in the palette and at the size now in use.

        Scoped to `#field` rather than to `QLineEdit`, for the reason
        `sections.py` gives: this stands inside a card whose sheet is set on an
        ancestor, and a bare class rule would reach every line edit in the pane.

        The fill is `PANEL` and not `PANEL_HOT`. A field standing on a card is
        then the same colour as the card and told apart by its edge alone, which
        is the first claim in this module's docstring; a lighter fill would make
        it a `SUBTLE` button with a cursor in it.
        """
        right = 0 if self._joined else _RADIUS
        self.setStyleSheet(f"""
            #field {{
                background: {rgb(PANEL)};
                color: {rgb(TEXT)};
                border: 1px solid {rgb(mix(LINE, TEXT, EDGE))};
                border-top-left-radius: {_RADIUS}px;
                border-bottom-left-radius: {_RADIUS}px;
                border-top-right-radius: {right}px;
                border-bottom-right-radius: {right}px;
                padding: {_PAD_Y}px {_PAD_X}px;
                font-size: {metrics.pt("name")}pt;
                selection-background-color: {rgb(ACCENT)};
                selection-color: {rgb(PANEL)};
            }}
            #field:hover {{ border-color: {rgb(mix(LINE, TEXT, EDGE_HOVER))}; }}
            #field:focus {{ border-color: {rgb(ACCENT)}; }}
            #field:disabled {{
                background: {rgb(PANEL_HOT)};
                color: {rgb(DIM)};
                border-color: {rgb(LINE)};
            }}
        """)


class Field(QWidget):
    """A control under its label, with the focus ring painted around it.

    The ring is why this is a widget and not a function returning a layout: it
    is drawn outside the control's own rect, which nothing but a parent can do.

    Handed the control rather than building one, so a field's frame is the same
    frame whether what it holds is a `LineField`, a slider, or something a view
    brought itself — the label, the hint and the ring are the parts that should
    not differ between them.
    """

    def __init__(
        self,
        label: str,
        control: QWidget,
        hint: str = "",
        *,
        unit: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._control = control if not unit else _United(control, unit)

        self._label = QLabel(label)
        self._label.setObjectName("flabel")
        self._hint = QLabel(hint)
        self._hint.setObjectName("fhint")
        self._hint.setWordWrap(True)

        column = QVBoxLayout(self)
        # The inset on every side is the room the ring is drawn in — a wrapper
        # with no margins would clip it against its own edge, and a ring that is
        # three sides of a rectangle is a rendering fault rather than a state.
        column.setContentsMargins(RING_GAP, RING_GAP, RING_GAP, RING_GAP)
        column.setSpacing(_SPACING)
        if label:
            column.addWidget(self._label)
        column.addWidget(self._control)
        # Added whether or not there is one to say, and hidden when there is
        # not — a hidden widget is skipped by the layout and costs no height, so
        # what this buys is that `set_hint` is a field with a hint rather than a
        # field that grew a widget, and a caller need not know which it built.
        column.addWidget(self._hint)
        self._hint.setVisible(bool(hint))

        # The widget that takes focus is the control itself even when a unit has
        # wrapped it, so the ring follows the keyboard rather than the layout.
        self._focused = control
        self._focused.installEventFilter(self)

        self._dress()
        palette.CHANGED.connect(self._dress)
        metrics.CHANGED.connect(self._dress)

    def control(self) -> QWidget:
        """What was handed over, for a caller that built the field in one line
        and needs the control back to read or connect it."""
        return self._focused

    def set_hint(self, hint: str) -> None:
        """What the field wants, under it. Empty hides the line rather than
        leaving a blank one: a gap that appears and disappears walks everything
        below the field, which is the reflow the ring exists to avoid."""
        self._hint.setText(hint)
        self._hint.setVisible(bool(hint))

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Repaint when the control gains or loses focus, and never consume it.

        `False` in every case, including the two handled: the control has to go
        on receiving its own focus events, and this is watching them rather than
        answering them.
        """
        if watched is self._focused and event.type() in (
            QEvent.Type.FocusIn,
            QEvent.Type.FocusOut,
        ):
            self.update()
        return False

    def _dress(self) -> None:
        self.setStyleSheet(f"""
            #flabel, #fhint {{
                color: {rgb(DIM)};
                font-size: {metrics.pt("gloss")}pt;
            }}
        """)

    def paintEvent(self, event) -> None:
        """The ring, and nothing else — the wrapper has no fill of its own, so a
        field standing on a card shows the card through it.

        Drawn on the control's geometry rather than on this widget's: the label
        and the hint are outside the thing being pointed at, and a ring around
        all three would say the whole column is where the typing goes.
        """
        del event
        if not self._focused.hasFocus():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # Half the pen outside the control's edge and half in, so the ring abuts
        # the border rather than overlapping it — the control paints after this
        # and would take back whatever fell inside.
        inset = RING_W / 2
        box = QRectF(self._control.geometry()).adjusted(-inset, -inset, inset, inset)
        painter.setPen(QPen(ring(), RING_W))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(box, _RADIUS + inset, _RADIUS + inset)
        painter.end()


def ring() -> QColor:
    """The accent at the alpha a glow wears, built at the moment of drawing.

    Never held, for the reason `palette.mix` gives: the roles are mutated in
    place when the palette changes, and a colour copied off one and kept would
    be the one thing on screen still wearing the old accent.
    """
    return QColor(ACCENT.red(), ACCENT.green(), ACCENT.blue(), _RING_ALPHA)


class _United(QWidget):
    """A control and the unit it is in, butted together so the pair reads as one
    box — 240 *frames*, 16 *px*, 9.8 *ms*.

    The suffix is a label and not a second field: it is not editable, and an
    editable edge around it would offer a click that does nothing. The two
    corners they share are squared and the outer two are not, which is what
    makes the seam between them a seam rather than two controls that happen to
    be touching — and squaring the control's half is the control's own to do,
    for the reason `LineField.set_joined` gives.
    """

    def __init__(self, control: QWidget, unit: str) -> None:
        super().__init__()
        if isinstance(control, LineField):
            control.set_joined(True)
        self._suffix = QLabel(unit)
        self._suffix.setObjectName("funit")

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        row.addWidget(control)
        row.addWidget(self._suffix)

        self._dress()
        palette.CHANGED.connect(self._dress)
        metrics.CHANGED.connect(self._dress)

    def _dress(self) -> None:
        """The suffix, in the field's own resting edge and one step off its fill.

        `PANEL_HOT` and `DIM`, which is the pair a disabled `Button` wears, and
        deliberately: what the two have in common is that neither is a thing to
        press, and a unit that looked live would be the only unpressable box in
        the tree that did.
        """
        self.setStyleSheet(f"""
            #funit {{
                background: {rgb(PANEL_HOT)};
                color: {rgb(DIM)};
                border: 1px solid {rgb(mix(LINE, TEXT, EDGE))};
                border-left: 0;
                border-top-right-radius: {_RADIUS}px;
                border-bottom-right-radius: {_RADIUS}px;
                padding: {_PAD_Y}px {_PAD_X}px;
                font-size: {metrics.pt("gloss")}pt;
            }}
        """)
