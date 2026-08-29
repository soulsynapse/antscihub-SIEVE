"""The banner: what the application has to say about something it just did.

Lifted from `mockup/paper_primitives.py`, and the second thing here that is
neither a surface nor a control. `pill.py` is the first, and this is the half of
that argument it declined to make: a pill says what state a thing is *in* and is
the size of a word, and there is no way to say *why* in one. A failed run, a
missing input, a chain recomputing in the background and two files written are
four things the interface has to report and none of them fit beside a name.

It arrives ahead of a view asking, the way the budget controls did, and for the
reason `pill.py` gives about states: what a failure looks like is spent across
every view that can fail — which is all of them — and the first view to draw a
red strip would be fixing it for the rest. Settling it before there is one is
what keeps *this is what the application tells you* a decision rather than a
description of whichever pane happened to fail first.

The hue is the whole problem, and it is the one `pill.py` handed here. The
mockup lights four kinds in four colours — blue for information, amber for a
warning, red for an error, green for done — and three of those are hues past the
one every palette commits to (`palette.py`: the accent is the only hue, and two
of the palettes are chosen so that an accent-blind reader still finds it). Four
roles would be four colours every palette below has to answer, which is what
`button.py` refuses for danger and `pill.py` refuses for failure. So the kinds
are told apart by *shape* — a painted mark per kind — and the colour axis is cut
down to the one question the tree can honestly ask: does this want you now.

That is why the stripe has two values and not four. `WARN` and `FAIL` are the
accent, which is the tree's one answer to *this is the one you are acting on*;
`NOTE` and `DONE` are `DIM`, because a thing that is finished and a thing that is
merely true are both reports and neither is a summons. The mark takes the same
colour from the same function, so it is one decision drawn twice rather than two
that can disagree.

What that buys is redundancy the mockup only half had. The redundant-encoding
claim is the one Okabe and Ito make about categorical colour (*Color Universal
Design*, 2008) and that `palette.py` already leans on for its safe pair: a reader
who sees none of a hue has to be able to read the same fact off something else.
Here every kind is carried three times — by the mark's shape, by the stripe, and
by the words, which are the only part that is unambiguous and are therefore never
optional. A banner with no title does not compile into anything worth looking at,
so the title is the required argument and the body is not.

Where it is honestly weaker is at the silhouette. `WARN` is a triangle and is
findable across a pane; `NOTE`, `DONE` and `FAIL` are all a 14px circle and
differ only by what is inside them — a dot, a tick, a cross. At arm's length
those three are one shape, and the stripe does not separate them either, since
`FAIL` shares the accent with `WARN` and `NOTE` shares `DIM` with `DONE`. What
tells them apart at that distance is the title, which is the argument for the
title being what it is: *Nothing to write* and *Wrote 2 files* are the mark, and
the drawing is the confirmation.

There is no dismiss. The mockup has none either, and the reason to keep it that
way is what a banner is: it reports a state something else is holding, so a
banner the user can close is a banner whose view no longer knows whether it is up
— and the next thing that recomputed would put it back, which reads as the close
button not working. Whatever raised one takes it down, the same way whatever set
a `Pill` sets it again.

Painted rather than styled for the surface and the stripe, and styled for the
text — the split `card.py` makes, and here for the same two reasons. The stripe
runs into two rounded corners and has to be clipped by them, which is the meter's
problem at the card's foot and has the same answer; the mark is a drawing and not
a glyph, so it is the same drawing on a machine with a different face installed.
The title and the body are text in a column that wraps, which is what a sheet and
a layout are actually good at.

The corner is `metrics.radius()`, and this is the first thing in `primitives/`
besides the card itself to follow that slider rather than decline it. Every
control here declines on the same grounds — the slider is *card corners*, and a
user squaring off their cards did not ask for square buttons — but this is not a
control. It is a full-width block with a title on a ground, which is a card in
everything except the four verbs, and one that kept a corner of its own would be
the one shape in a stack not moving when the user moved the stack.

The fill is `PANEL_HOT`, which is that role's third job and the first that is not
about the pointer. It is `panel_hot` because a banner stands wherever the thing
it is reporting on stands — on a card, on the ground between cards, in a pane —
and `PANEL` would be invisible on the first of those. The role is documented as
the lighter one a control wears against the panel, and hover is a *transition*
into it rather than the meaning of the value; `check.py` already takes it at
rest for a disabled box on the same reading.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from sieve.gui import metrics, palette
from sieve.gui.palette import ACCENT, DIM, LINE, PANEL_HOT, TEXT, rgb

#: The kinds, four because the mockup found four things to say. Strings and not
#: an enum, for `button.py`'s and `pill.py`'s reason: they are what a caller
#: writes, `Banner("Nothing to write", ..., FAIL)` reads as the sentence it is,
#: and the constants exist so the spelling is checked somewhere.
#:
#: The split that matters is two ways: `WARN` and `FAIL` want the user, `NOTE`
#: and `DONE` do not. That is the distinction the tree has a colour for — see the
#: module docstring — and the mark carries the rest.
NOTE = "note"
WARN = "warn"
FAIL = "fail"
DONE = "done"

#: The stripe down the leading edge. Three pixels, and its own constant rather
#: than `nav.MARK_W`: the nav's mark is a selection, saying *this is the one you
#: are on*, where this says *there is something here*. The two move for
#: unrelated reasons.
_STRIPE = 3

#: The air inside the block. Wider than a card's `_INSET`, which is measured
#: against a rule and a row of verbs where this is measured against a paragraph.
_PAD_X = 12
_PAD_Y = 10

#: The mark, and the room between it and the words. Fourteen is `check.py`'s box
#: for the same reason: it is the size at which a drawn glyph is three segments
#: and not a smudge. Fixed rather than a multiple of the type size, so the air
#: around the mark is the same at every size.
_MARK = 14
_MARK_GAP = 10

#: How thick the mark is stroked, and how far its two-line kinds are inset from
#: the box. Rounded at the ends and the joins, so at 14px a tick reads as one
#: stroke.
_STROKE = 1.6
_INSET = 0.26

#: Between the title and the body. Tight, because the two are one message; the
#: gap that separates a banner from what is under it is the layout's.
_LEAD = 2


def sheet() -> str:
    """The rules for the two labels, for a caller that sets a sheet of its own.

    Handed out for the reason `stack.sheet()` is: a sheet set on an *ancestor*
    reaches in here, so a view that dresses itself has to be able to put these
    back. Scoped to object names and never to a bare `QLabel`, since a rule on
    the class would reach every label the view holds.

    The two colours are the pair `sections.py` and the cards draw a name and its
    gloss in, and they are that pair on purpose: a banner is a name with a quiet
    line under it, and one that invented its own two inks would be a second
    answer to how the tree writes that.
    """
    return f"""
        #bannertitle {{
            color: {rgb(TEXT)};
            background: transparent;
            border: 0;
        }}
        #bannerbody {{
            color: {rgb(DIM)};
            background: transparent;
            border: 0;
        }}
    """


class Banner(QWidget):
    """A marked block saying what happened, with a title and a line under it.

    It knows what it looks like and what it was told to say, and nothing about
    what put it there — the same split every primitive here makes, and like
    `Pill` with no signal on this end of it. A banner offers no gesture: it takes
    no focus, changes no cursor, and answers neither the pointer nor the
    keyboard, because the thing worth clicking is whatever the banner is about
    and that is somewhere else on the screen.

    It is as wide as it is given and as tall as its words need, which is the
    opposite of the pill beside it: a pill stands at the end of a row and a
    banner spans the column, so the body wraps and the height follows the width.
    """

    def __init__(
        self,
        title: str = "",
        body: str = "",
        kind: str = NOTE,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._kind = kind
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._title = QLabel(title)
        self._title.setObjectName("bannertitle")
        # Not wrapped, unlike the body: a title is the one line that has to read
        # at a glance from across the pane, and it holds the mark beside it on
        # one line — the mark is centred on the title, so a long body leaves the
        # drawing where it is.
        self._title.setWordWrap(False)

        self._body = QLabel(body)
        self._body.setObjectName("bannerbody")
        self._body.setWordWrap(True)
        self._body.setVisible(bool(body))

        column = QVBoxLayout(self)
        column.setContentsMargins(
            _STRIPE + _PAD_X + _MARK + _MARK_GAP,
            _PAD_Y,
            _PAD_X,
            _PAD_Y,
        )
        column.setSpacing(_LEAD)
        column.addWidget(self._title)
        column.addWidget(self._body)

        # As wide as it is given and no taller than its words: a banner takes its
        # column's width, and the height it wants at that width is the wrapped
        # body's, which the policy has to be told to ask `heightForWidth` for.
        policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)

        self._resize()
        self.setStyleSheet(sheet())
        # Bound methods: PySide6 drops a connection to a bound method when the
        # receiver goes, where a lambda closing over `self` keeps a dead banner
        # subscribed for the life of the run.
        palette.CHANGED.connect(self._restyle)
        metrics.CHANGED.connect(self._resize)

    def state(self) -> tuple[str, str, str]:
        """The title, the body and the kind, for a caller that built one from
        what came back off a run and has to read back what it made."""
        return self._title.text(), self._body.text(), self._kind

    def set_message(self, title: str, body: str, kind: str) -> None:
        """Say something else.

        All three together and not one setter each, for `Pill.set_state`'s
        reason and more sharply: a banner going from *Recomputing* to *Nothing to
        write* changes every one of them, and three calls would put two frames on
        screen showing a title against the wrong mark. The body's presence
        decides whether there is a second line at all, so this asks the layout
        again rather than only repainting.
        """
        self._title.setText(title)
        self._body.setText(body)
        self._body.setVisible(bool(body))
        self._kind = kind
        self.updateGeometry()
        self.update()

    def heightForWidth(self, width: int) -> int:
        """How tall this has to be to hold its words at that width.

        Delegated to the layout rather than measured here: the wrap is the body
        label's own arithmetic, and a second measurement in this file would be
        this widget's idea of its height disagreeing with where its labels
        actually land.

        A banner with no body has nothing in it that wraps, so the layout answers
        -1 — Qt's "no opinion", which is true of the layout and not of this
        widget. The hint is that answer: a title in its paddings is the same
        height at every width, and handing the caller a negative would make a
        column of banners lay the one with a bare title out differently from the
        rest.
        """
        height = self.layout().heightForWidth(width)
        return height if height >= 0 else self.sizeHint().height()

    def _restyle(self) -> None:
        """The two inks again, at the palette now in force. A sheet is a string
        built out of colours as they were, which is the obligation
        `palette.CHANGED` carries and the reason a painted surface needs nothing
        said to it."""
        self.setStyleSheet(sheet())
        self.update()

    def _resize(self) -> None:
        """The two fonts at the sizes now in force, and the room they need.

        `name` and `gloss`, which is the pair the sheet's two colours belong to:
        the title is the name of what happened and the body is the quiet line
        saying what it means, which is exactly what those two roles are for. Its
        own slot rather than a repaint, for `check.py`'s reason — a size changes
        how much of the column this takes, so the layout has to be told and
        `updateGeometry` is how.
        """
        title = self._title.font()
        title.setPointSize(metrics.pt("name"))
        title.setBold(True)
        self._title.setFont(title)

        body = self._body.font()
        body.setPointSize(metrics.pt("gloss"))
        self._body.setFont(body)

        self.updateGeometry()
        self.update()

    def paintEvent(self, event) -> None:
        """Fill, stripe, edge, mark — in that order, and none of them from a
        sheet.

        The stripe is drawn under the edge rather than over it, so the hairline
        closes the block on all four sides and the stripe is inside it. Drawing
        it after would leave three borders and a coloured gap where the fourth
        should be, which reads as a card that has come apart at one edge.
        """
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Half a pixel in on every side, for `card.py`'s reason: a 1px pen
        # straddles the path it is given, so the widget's own rect would lose the
        # pen's outer half.
        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        corner = metrics.radius()
        shape = QPainterPath()
        shape.addRoundedRect(box, corner, corner)

        painter.fillPath(shape, PANEL_HOT)

        # Clipped by the block's own shape, because the stripe runs into two
        # rounded corners — the meter's problem at the card's foot, with the same
        # answer: the corner stays the block's and the bar carries no radius.
        painter.save()
        painter.setClipPath(shape)
        painter.fillRect(
            QRectF(box.left(), box.top(), _STRIPE, box.height()),
            self._signal(),
        )
        painter.restore()

        painter.setPen(QPen(LINE, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(shape)

        self._draw_mark(painter)
        painter.end()

    def _draw_mark(self, painter: QPainter) -> None:
        """The drawing that says which of the four this is.

        Centred on the title's own line rather than on the block, which is what
        keeps a two-word banner and a five-line one looking like the same object:
        the mark and the title are one row, and the body hangs under both. The
        title's geometry is asked for rather than computed off the paddings — the
        layout is already the answer to where that line landed, and a second
        arithmetic here would be a mark that drifts the moment a margin moves.
        """
        left = _STRIPE + _PAD_X
        top = self._title.geometry().center().y() - _MARK / 2
        box = QRectF(left, top, _MARK, _MARK).adjusted(0.5, 0.5, -0.5, -0.5)
        ink = self._signal()

        pen = QPen(ink, _STROKE)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if self._kind == WARN:
            painter.drawPath(_triangle(box))
        else:
            painter.drawEllipse(box)

        side = box.width()
        near = box.left() + side * _INSET
        far = box.left() + side * (1 - _INSET)

        if self._kind == DONE:
            tick = QPainterPath(QPointF(near, box.top() + side * 0.52))
            tick.lineTo(box.left() + side * 0.44, box.top() + side * 0.72)
            tick.lineTo(far, box.top() + side * 0.32)
            painter.drawPath(tick)
        elif self._kind == FAIL:
            painter.drawLine(
                QPointF(near, box.top() + side * _INSET),
                QPointF(far, box.bottom() - side * _INSET),
            )
            painter.drawLine(
                QPointF(far, box.top() + side * _INSET),
                QPointF(near, box.bottom() - side * _INSET),
            )
        elif self._kind == WARN:
            # Inside a triangle rather than a circle, so the bar is dropped and
            # shortened to the room under the apex.
            painter.drawLine(
                QPointF(box.center().x(), box.top() + side * 0.42),
                QPointF(box.center().x(), box.top() + side * 0.66),
            )
            painter.drawPoint(QPointF(box.center().x(), box.bottom() - side * 0.14))
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(ink)
            painter.drawEllipse(box.center(), _STROKE, _STROKE)

    def _signal(self) -> QColor:
        """The one colour in the block, worn by the stripe and the mark together.

        Two values and not four — see the module docstring on why a tree with one
        hue cannot spend three more. An unknown kind falls to `DIM` rather than
        raising, the way `button.py` and `pill.py` fall to their defaults: a
        banner built from a string that came off a run should say its piece
        quietly, not take the pane down on its way to reporting that something
        else already failed.
        """
        return ACCENT if self._kind in (WARN, FAIL) else DIM


def _triangle(box: QRectF) -> QPainterPath:
    """The warning's outline: the one kind whose silhouette differs from the
    others, which is the whole of what it buys over a fourth thing inside a
    circle. Inset at the foot so a triangle and a circle of the same box carry
    the same visual weight — a triangle drawn to the full square reads larger
    than the circle beside it."""
    path = QPainterPath(QPointF(box.center().x(), box.top()))
    path.lineTo(box.right(), box.bottom() - box.height() * 0.08)
    path.lineTo(box.left(), box.bottom() - box.height() * 0.08)
    path.closeSubpath()
    return path
