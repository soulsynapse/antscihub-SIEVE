"""The meter: a quantity drawn as a length, in a groove the length is read off.

Lifted from `mockup/paper_primitives.py`, and the third thing here that is
neither a surface nor a control. `pill.py` says what state a thing is *in* and
`banner.py` says what just happened to it; this says *how much* — the one mark in
this tree that is a number rather than a word, and the only one whose meaning is
its size.

It arrives the way `menu.py` did rather than the way the marks above it did:
because the tree was already paying for not having it. `card.py` paints a foot
across the bottom of every card that is measuring something, with its own private
height, its own groove colour and its own rule for when the bar takes the accent;
`table.py` landed with cells that take a widget and a numeric column beside them,
which is the mockup's `Cellbar` — *`Meter`'s sibling inside a cell* — and the
second place the same bar is wanted. Writing that second one where it was wanted
would be the drift `menu.py` was moved to stop, with the added twist that the
copy already in the tree is inside a card and not reachable from a row. So the
drawing moves here and the card takes it from this file, which leaves `card.py`
deciding *whether its foot is drawn* and this deciding what a length looks like.

The hue is the same problem `pill.py` and `banner.py` each handed on, and here it
costs something the other two did not pay. The mockup draws its bar neutral below
the step's share of the frame budget and amber past it, which is a second hue and
so is refused for the third time (`palette.py`: the accent is the only one, and
two palettes are chosen so an accent-blind reader still finds it). What is left
is the accent, and the accent already means *this is the one you are acting on* —
so the two questions collapse into one flag, and the one the tree keeps is
selection, because that is the one `card.py` was already answering with it and
the one a column of twenty bars would otherwise spend twenty times over.

So a meter cannot say *this step is expensive*. That is a real loss and it has a
real answer, which the mockup's own card is already drawing: the cost is a
number, it stands at the other end of the same row, and a number saying `840 ms`
is a better report of an overrun than a colour saying *past a threshold somebody
picked*. The bar's job is the comparison between rows, and it keeps that.

Two shapes and one drawing, and which one is not this file's choice. A bar that
runs into a card's corner has to be clipped by it and carries no radius of its
own — the mockup's reason, and `banner.py`'s stripe has the same one — while a
bar floating in a cell is round at both ends. The dev bench already named what
that difference does: a bar with ends and a visible groove reads as a measurement
*of the thing beside it*, where a full-bleed strip reads as an edge that happens
to be two colours (`view/dev/card_mockups/look.py`, on the inset meter). Both
readings are wanted, in the two places they are true, so `round_ends` is the
caller's and the drawing is one function.

The corner is therefore neither this file's constant nor `metrics.radius()`, and
this is `pill.py`'s argument rather than the controls'. A round-ended bar's
radius is half its own height by definition and there is nothing to decide; the
card's foot has a radius and it is the card's.

Not a `QProgressBar`, for `segmented.py`'s reason about `QTabBar`. A styled
progress bar is a groove and a chunk with the platform's own metrics between
them, none of it clippable by the corner of the widget it is the foot of — and
what would be borrowed is an animation and a busy state, which is `pill.py`'s
`LIVE` said again in a shape that also claims to know a fraction it does not
have.

`HEIGHT` is public and `card.py`'s, moved rather than restated: four pixels is
the smallest bar that still reads as a length rather than as a hairline that
happens to be two colours, and small enough that a card carrying one is not a
card carrying a progress widget. A second 4 written in the card would be a second
answer to how thick a length is, free to drift from this one the way the menu's
dress drifted from chrome's.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from sieve.gui import palette
from sieve.gui.palette import ACCENT, DIM, LINE

#: How thick a bar is, wherever it is drawn — see the module docstring on why the
#: number lives here and not in the card that used to own it.
HEIGHT = 4

#: How long a free-standing one is when nothing has told it otherwise, and the
#: shortest it will agree to be. The default is the mockup's, which is the width
#: at which a row of them can be compared at a glance; the floor is where a
#: length stops being one and becomes a dash, and a cell narrower than that
#: should be carrying the number instead.
WIDTH = 84
_MIN_W = 24


def draw(
    painter: QPainter,
    box: QRectF,
    full: float,
    *,
    current: bool = False,
    round_ends: bool = True,
) -> None:
    """Paint a groove across `box` and `full` of it filled.

    Handed a painter rather than owning one, because the two callers are not the
    same kind of thing: `Meter` below is a widget with its own `paintEvent`, and
    the card's foot is four pixels of a card that is already painting itself
    inside a clip path it set. A function is what both can reach.

    The fill is clipped by the groove's own shape rather than drawn as a second
    rounded rect. At a small fraction a rounded rect narrower than its own two
    corners comes out as a lens or a dot — a shape that reads as *a mark at the
    left end* rather than as *a short length* — where a clipped rectangle is
    round at the end it starts from and square where it stops, which is what a
    bar that has got this far actually looks like.

    The groove is `LINE` in both shapes, which is `card.py`'s argument carried
    over: the foot sits against the ground and the cell's bar sits on a panel,
    and a groove in the colour of either is a groove that disappears — leaving a
    length with nothing to be a fraction of.
    """
    full = max(0.0, min(1.0, full))
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    if round_ends:
        corner = box.height() / 2
        painter.setBrush(LINE)
        painter.drawRoundedRect(box, corner, corner)
        # Intersected and not set: a caller may already be clipping — the card's
        # foot is drawn inside the clip the card set to its own corner — and a
        # plain `setClipRect` would replace that and let the bar out past it.
        painter.setClipRect(
            QRectF(box.left(), box.top(), box.width() * full, box.height()),
            Qt.ClipOperation.IntersectClip,
        )
        painter.setBrush(ACCENT if current else DIM)
        painter.drawRoundedRect(box, corner, corner)
    else:
        painter.fillRect(box, LINE)
        painter.fillRect(
            QRectF(box.left(), box.top(), box.width() * full, box.height()),
            ACCENT if current else DIM,
        )
    painter.restore()


class Meter(QWidget):
    """A short bar saying how much of something there is, standing on its own.

    It knows what it looks like and the fraction it was handed, and nothing about
    what that fraction is of — the split every primitive here makes, and like
    `Pill` and `Banner` with no signal on this end of it. A meter offers no
    gesture: it takes no focus, changes no cursor and answers neither the pointer
    nor the keyboard, which is the whole of what tells it from the slider two
    files over. A bar that can be dragged is a control and a bar that cannot is a
    report, and the two are told apart by the handle the slider has.

    It follows no size: `HEIGHT` is pixels and so is the length, where the pill
    and the banner grow with the text they hold. A mark whose meaning is its size
    cannot also take its size from a preference — two bars in one column at two
    type sizes would not be comparable, which is the only thing this shape is
    for.
    """

    def __init__(
        self,
        full: float = 0.0,
        current: bool = False,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._full = full
        self._current = current
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # As long as it is given and no thicker than a bar: a meter goes in a
        # cell of a declared width or in a row beside a number, and the length is
        # the holder's to set where the thickness is never anyone's.
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        # Bound methods, never lambdas: PySide6 drops a connection to a bound
        # method when the receiver goes, where a lambda closing over `self` would
        # keep a dead meter subscribed for the life of the run. No
        # `metrics.CHANGED` — nothing here is measured in points.
        palette.CHANGED.connect(self.update)

    def full(self) -> float:
        """The fraction, for a caller that built one from a run and has to read
        back what it made."""
        return self._full

    def set_full(self, full: float) -> None:
        """Move the length. Clamped at the ends rather than refused, so a caller
        may hand this a ratio of two numbers it did not check — a step that
        overran its budget is a full bar and never a bar drawn past its groove.
        """
        self._full = max(0.0, min(1.0, full))
        self.update()

    def set_current(self, current: bool) -> None:
        """Wear the accent, or stop.

        Its own setter and not folded into `set_full`, which is where this parts
        company with `Pill.set_state` and `Banner.set_message`. Those set two
        halves of one sentence and a frame showing one without the other would be
        wrong; these are two facts from two places — the fraction comes off
        whatever is being measured and the accent comes off the row the user is
        standing on — and they move at different moments.
        """
        self._current = current
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(WIDTH, HEIGHT)

    def minimumSizeHint(self) -> QSize:
        return QSize(_MIN_W, HEIGHT)

    def paintEvent(self, event) -> None:
        """Round-ended, because a free-standing one is not the foot of anything —
        see the module docstring on which shape says which thing."""
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # Half a pixel in top and bottom: the groove is a filled shape rather
        # than a stroked one, so the inset is not `card.py`'s pen problem but
        # antialiasing — a 4px rounded rect on the widget's own rect has its
        # curves cut off by the edge it is drawn against.
        box = QRectF(self.rect()).adjusted(0, 0.5, 0, -0.5)
        draw(painter, box, self._full, current=self._current)
        painter.end()
