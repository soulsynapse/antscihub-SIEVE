"""The empty state: a room with nothing in it, saying what would put something there.

Lifted from `mockup/paper_primitives.py`, where it stands in the transient set
beside the banners. It is the second thing here that arrived because the tree was
already paying for not having it — `menu.py` is the first — and the debt is
further along than that one's was. There are three copies, not two.
`view/project_list/view.py` writes *no projects yet* as a centred dim label
dropped into the column; `sections.py`'s `_Placeholder` ends on *nothing here
yet*; `view/canvas/view.py` paints *nothing on the canvas* into the middle of its
stage. Three views independently decided that a list with nothing in it says so
in words, which is the right decision made three times, and the fourth view to
have nothing to show would have made it a fourth.

What the mockup has that none of the three do is the second line. *No steps yet*
is the fact; *Add the first one to start the chain* is the reason the fact is
worth a box rather than a blank pane — an empty list and a list that failed to
load look identical, and the sentence that tells them apart is the one that names
the move the user has not made yet. So the body is where the next step goes, and
that is the whole of what this shape is over the dim sentence it replaces. A
title alone compiles, because a view may honestly have no next step to name; a
view that has one and leaves it off has thrown away the reason to build this.

The edge is dashed, and it is the only dashed line in the tree. Everything else
drawn in `LINE` is the boundary of something that is there — a card's edge, a
table's rule, a bar's box — and a solid hairline around this would say the same,
which is exactly the wrong thing: what is being drawn is room that is reserved
and not yet filled. A broken line is the cheapest way to say *this is an
outline, not a thing*, and it costs no role at all, which is the argument
`banner.py` makes for shape over hue held on the other axis.

There is no fill, and that is the one place this departs from the mockup, which
lays a near-white wash inside the box. The tree has no role for *a hair off the
panel*: the fills are `PANEL`, `PANEL_HOT` and `STACK_BG`, and each is already
spoken for. `PANEL_HOT` is what a control wears when the pointer is on it — the
reading `banner.py` takes at rest and `check.py` takes for a disabled box — and
an absence that lit up like a hovered control would be the loudest quiet thing on
the screen. `PANEL` is invisible on the panel this usually stands on. So the box
is empty in the literal sense, and what is inside it is whatever it is standing
on, which is the truthful drawing: a column of cards with a hole at the end.

The two inks are the tree's `name` and `gloss` pair, from the same place
`banner.py` takes them and for the same reason — a name with a quiet line under
it is written one way here. What is *not* borrowed is the bold. A banner bolds
its title because it is a report about something that just happened and wants the
user; this reports that nothing has happened yet, which is the least urgent thing
the interface can say, and weight spent on it is weight taken from whatever the
user should actually be looking at. Same pair, one step quieter, which is a
distinction the two files can each state rather than a number either of them
invents.

The corner is `metrics.radius()`, on `banner.py`'s grounds and more directly:
that file argues a full-width block on a ground is a card in everything but the
verbs, and this one stands in the exact place a card would have. One that kept a
corner of its own would be the shape in the column not moving when the user moved
the column.

There is no verb on it. The mockup has none, and the reason to keep it that way
is `button.py`'s budget: one filled button per screen, and a screen whose only
button is on the thing saying there is nothing here has spent it on an absence.
The verb that fills the room lives where it lives when the room is full — in the
head of the pane, or in the menu over it — and a second copy inside the box would
be the same action in two places, one of which disappears the moment it works.

Two of the three copies are left alone, and the reasons are worth writing down
because they are what stops this from being a fourth answer rather than the one.
`sections.py`'s placeholder is not this shape: it retells the *name and gloss of
the section the nav is standing on* and says *nothing here yet* under them, which
is three lines about a specific section rather than two about a room, and folding
it in would either lose the retelling or push a third slot into this file for one
caller. The canvas paints its sentence inside a stage rect it computes in its own
`paintEvent`, with no child widgets at all and a placement that follows the
aspect on every resize; a widget dropped in there would have to be laid out
against a rectangle that is not the pane's, which is the canvas's arithmetic and
not a primitive's. The library's is the copy that is exactly this, so that is the
one that takes it.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from sieve.gui import metrics, palette
from sieve.gui.palette import DIM, LINE, TEXT, rgb

#: The air inside the box, and it is generous on purpose. A card's inset is
#: measured against a rule and a row of verbs; this is measured against a
#: sentence, and the room is what makes an empty box read as room. The mockup's
#: 22 is a single number for both axes and stays one here, which keeps the two
#: centred lines centred on both.
_PAD = 22

#: Between the fact and the move. The same tight lead `banner.py` sets between a
#: title and its body, and for that file's reason: the two are one message.
_LEAD = 2

#: The broken edge: pixels drawn, then pixels skipped, in units of the pen's own
#: width, which is Qt's arithmetic for a dash pattern. Even, so the line reads as
#: a rhythm, and long enough that a corner at the tree's largest radius still
#: carries a dash.
_DASH = (4.0, 4.0)


def sheet() -> str:
    """The rules for the two labels, for a caller that sets a sheet of its own.

    Handed out for `banner.sheet()`'s reason, which is `stack.sheet()`'s: a sheet
    set on an *ancestor* reaches in here, so a view that dresses itself has to be
    able to put these back. Scoped to object names and never to a bare `QLabel`,
    since a rule on the class would reach every label the view holds.
    """
    return f"""
        #emptytitle {{
            color: {rgb(TEXT)};
            background: transparent;
            border: 0;
        }}
        #emptybody {{
            color: {rgb(DIM)};
            background: transparent;
            border: 0;
        }}
    """


class Empty(QWidget):
    """An outlined box saying there is nothing here, and what would change that.

    It knows what it looks like and what it was told to say, and nothing about
    why the room is empty — the same split every primitive here makes. Like
    `Banner` it offers no gesture at all: no focus, no cursor, no answer to the
    pointer, because the thing worth clicking is whatever fills the room and that
    is somewhere else on the screen.

    It is as wide as it is given and as tall as its words and its air need, which
    is `Banner`'s policy and not a pane-filling one. The two rooms it stands in
    are a column of cards and a whole pane; a shape that grew to fill whatever it
    was handed would be a different size in each, and the same sentence at two
    sizes is two objects. A caller wanting it centred in a pane puts a stretch
    either side of it, which is the layout's job and reads as one where this
    file's arithmetic would not.
    """

    def __init__(
        self,
        title: str = "",
        body: str = "",
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._title = QLabel(title)
        self._title.setObjectName("emptytitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Wrapped, unlike a banner's title, which stands in a row beside a mark.
        # Nothing stands beside these words, so a long fact in a narrow column
        # folds inside the box drawn around it.
        self._title.setWordWrap(True)

        self._body = QLabel(body)
        self._body.setObjectName("emptybody")
        self._body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._body.setWordWrap(True)
        self._body.setVisible(bool(body))

        column = QVBoxLayout(self)
        column.setContentsMargins(_PAD, _PAD, _PAD, _PAD)
        column.setSpacing(_LEAD)
        column.addWidget(self._title)
        column.addWidget(self._body)

        # As wide as it is given and no taller than its words: the height it
        # wants at a given width is the wrapped body's, which `heightForWidth`
        # answers and which the policy has to be told to ask for.
        policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)

        self._resize()
        self.setStyleSheet(sheet())
        # Bound methods: PySide6 drops a connection to a bound method when the
        # receiver goes, where a lambda closing over `self` keeps a dead
        # widget subscribed for the life of the run.
        palette.CHANGED.connect(self._restyle)
        metrics.CHANGED.connect(self._resize)

    def message(self) -> tuple[str, str]:
        """The fact and the move, for a caller that built one out of what it
        found and has to read back what it made."""
        return self._title.text(), self._body.text()

    def set_message(self, title: str, body: str = "") -> None:
        """Say something else.

        Both together and not one setter each, for `Banner.set_message`'s reason:
        the fact and the move that answers it change together, and two calls would
        put a frame on screen pairing the new fact with the old move. Whether
        there is a second line at all decides the height, so this asks the layout
        again rather than only repainting.
        """
        self._title.setText(title)
        self._body.setText(body)
        self._body.setVisible(bool(body))
        self.updateGeometry()
        self.update()

    def heightForWidth(self, width: int) -> int:
        """How tall this has to be to hold its words at that width.

        Delegated to the layout rather than measured here, for `banner.py`'s
        reason: the wrap is the labels' own arithmetic, and a second measurement
        in this file would be this widget's idea of its height disagreeing with
        where its labels actually landed. A layout with nothing in it that wraps
        answers -1 — Qt's *no opinion*, which is true of the layout and not of
        this widget — so the hint stands in, and a column holding one of these
        beside a taller one lays both out the same way.
        """
        height = self.layout().heightForWidth(width)
        return height if height >= 0 else self.sizeHint().height()

    def _restyle(self) -> None:
        """The two inks again, at the palette now in force. A sheet is a string
        built out of colours as they were, which is the obligation
        `palette.CHANGED` carries and the reason the painted edge needs nothing
        said to it."""
        self.setStyleSheet(sheet())
        self.update()

    def _resize(self) -> None:
        """The two fonts at the sizes now in force, and the room they need.

        `name` and `gloss`, which is the pair the sheet's two colours belong to,
        and neither is bolded — see the module docstring on why this is the same
        pair as a banner's one step quieter. Its own slot rather than a repaint,
        for `check.py`'s reason: a size changes how much of the column this takes,
        so the layout has to be told and `updateGeometry` is how.
        """
        title = self._title.font()
        title.setPointSize(metrics.pt("name"))
        self._title.setFont(title)

        body = self._body.font()
        body.setPointSize(metrics.pt("gloss"))
        self._body.setFont(body)

        self.updateGeometry()
        self.update()

    def paintEvent(self, event) -> None:
        """The broken edge, and nothing else — no fill, on the grounds the module
        docstring gives.

        Half a pixel in on every side, for `card.py`'s reason: a 1px pen straddles
        the path it is given, so an edge drawn on the widget's own rect loses its
        outer half and comes back looking like half a line. Antialiased, because a
        dashed corner is where a hairline is least forgiving.
        """
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        corner = metrics.radius()
        shape = QPainterPath()
        shape.addRoundedRect(box, corner, corner)

        pen = QPen(LINE, 1)
        pen.setDashPattern(list(_DASH))
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(shape)
        painter.end()
