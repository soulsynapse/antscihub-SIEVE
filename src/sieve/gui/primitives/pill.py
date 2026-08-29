"""The pill: a word saying what state a thing is in, with a dot beside it.

Lifted from `mockup/paper_primitives.py`, and the first thing here that is
neither a surface nor a control. A card, a stack, a section and a view are what
the work is *seen in*; a button, a field, a slider, a check, a select and a bar
are what the work is *done with*. This is the third kind — a mark the interface
makes about something, that takes no gesture at all. It arrives ahead of a view
asking, the way `button.py` and `field.py` and `check.py` did, and for their
reason: *what does a state look like* is a budget spent across the whole
application, and the first view to draw a running step would be fixing it for
every view after it.

The mockup's own comment is the claim worth lifting: the dot carries the state
and the word carries the meaning, so a pill is never colour alone. That is
written there as a courtesy to a colour-blind reader and it turns out to be the
whole load-bearing part here, because this tree cannot draw the mockup's dots.
The mockup lights three — green for current, amber for recomputing, grey for not
run — and green and amber are two hues past the one every palette commits to
(`palette.py`: the accent is the only hue, and two of the palettes are chosen so
that an accent-blind reader can still find it). A ninth and tenth role would be
colours every palette below has to answer, which is what `button.py` refuses for
danger and is refused again here. So the dot is drawn in the three roles that
exist — `LIVE` in the accent, `IDLE` in the ink, `OFF` in `DIM` — and what is
lost is exactly the part the mockup already said was redundant.

What that refusal does cost is a *fourth* state: failure. A pill cannot say
"errored" in a way distinguishable from "off", because the difference between
those two is a hue and there is one. A view with something to report that badly
does not have a primitive here yet, and inventing a red-adjacent fourth kind
would be inventing the ninth role by the back door. The mockup's `banner` is
where that argument actually belongs, and it is not lifted with this.

Painted rather than styled, for two reasons and neither is taste. The dot is one
of them: the mockup drew it as a `●` in rich text, which is a glyph — its size
and its baseline are the font's, so the same pill is a different drawing on a
machine with a different face installed, and a painted circle is a circle
everywhere. The corner is the other. A pill's radius is half its own height by
definition, and its height follows `metrics.pt` — so a stylesheet built once
with a number in it is wrong the moment the user moves the type slider, and the
one number this file would have to keep in step is the one it can just compute
at paint time.

The corner is therefore neither this file's constant nor `metrics.radius()`.
Every other primitive here argues that the radius slider is *card corners* and
declines to follow it; this one declines for the further reason that it has no
choice to make — `metrics.RADIUS_MAX` is capped where a card "stops reading as a
stack of cards and starts reading as a stack of buttons, past this the shape is
the pill that argument was against", and this is that shape, on purpose, because
that is what tells a pill from a small card at a glance.

The word is never elided, which is the inverse of `check.py`'s floor. A check
may lose its label to whatever holds it, because the box still carries the
state; a pill's dot carries almost nothing on its own, so the text is the mark
and the minimum size is the whole of it.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from sieve.gui import metrics, palette
from sieve.gui.palette import ACCENT, DIM, LINE, TEXT

#: The states, in the three the eight roles can tell apart. Strings and not an
#: enum, for `button.py`'s reason: they are what a caller writes, `Pill("Not
#: run", OFF)` reads as the sentence it is, and the constants exist so the
#: spelling is checked somewhere.
#:
#: `LIVE` is the accent, the tree's one answer to *this is the one you are acting
#: on* and already the nav's mark and the checked box's fill; `IDLE` is the ink, a
#: plain fact about the thing; `OFF` is `DIM`, the absence of one. Three — see the
#: module docstring on where a failure is said instead.
LIVE = "live"
IDLE = "idle"
OFF = "off"

#: The dot, and the room between it and the word. A fixed radius rather than a
#: fraction of the type size, for `check.py`'s reason: it is a mark rather than a
#: letter, so the air around it is the same at every size. The gap is narrower
#: than a check's, because a dot is smaller than a box and the pair has to read
#: as one thing inside its own outline.
_DOT = 3.0
_GAP = 6

#: The air inside the outline. `_PAD_Y` sets the height and so the corner;
#: `_PAD_X` is wider, because the ends are round and a word reads as closer to a
#: curve than to a straight edge at the same distance.
_PAD_X = 9
_PAD_Y = 3


class Pill(QWidget):
    """A word and a dot inside a rounded outline, saying what state a thing is in.

    It knows what it looks like and what it was told to say, and nothing about
    what put it in that state — the same split every primitive here makes, with
    the difference that there is no signal on this end of it. A pill offers no
    gesture: it takes no focus, changes no cursor, and answers neither the
    pointer nor the keyboard, because everything it could do on a click is
    something the thing it describes should be clicked for instead.
    """

    def __init__(
        self,
        text: str = "",
        kind: str = IDLE,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._text = text
        self._kind = kind
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # As wide as its word and no taller than its own line, so a pill at the
        # end of a row keeps the shape its round ends give it.
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._resize()
        # Bound methods: PySide6 drops a connection to a bound method when the
        # receiver goes, where a lambda closing over `self` keeps a dead
        # pill subscribed for the life of the run.
        palette.CHANGED.connect(self.update)
        metrics.CHANGED.connect(self._resize)

    def state(self) -> tuple[str, str]:
        """The word and the kind, for a caller that built one from data and has
        to read back what it made."""
        return self._text, self._kind

    def set_state(self, text: str, kind: str) -> None:
        """Say something else.

        The two together and not one setter each, because they are one fact: a
        pill going from "Recomputing" to "Current" changes both, and two calls
        would put a frame between them showing a word in the wrong dot. The
        width moves with the word, so this asks the layout again rather than
        only repainting.
        """
        self._text = text
        self._kind = kind
        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QSize:
        """The dot, the gap, the word, and the padding around all three —
        measured rather than guessed, since the word is arbitrary and the type
        size is the user's."""
        text = self.fontMetrics()
        width = _PAD_X + 2 * _DOT + _PAD_X
        if self._text:
            width += _GAP + text.horizontalAdvance(self._text)
        return QSize(int(width), text.height() + 2 * _PAD_Y)

    def minimumSizeHint(self) -> QSize:
        """The whole of it — see the module docstring on why the word is not
        elided."""
        return self.sizeHint()

    def _resize(self) -> None:
        """The font at the size now in force, and the room that needs.

        `gloss` and not `name`: a pill is the quiet mark beside a thing rather
        than the thing, and one set at the name's size would read as a second
        name on the row. Its own slot rather than a repaint, for the reason
        `check.py` gives — a size changes how much of the row this takes, so the
        layout has to be told and `updateGeometry` is how.
        """
        font = self.font()
        font.setPointSize(metrics.pt("gloss"))
        self.setFont(font)
        self.updateGeometry()
        self.update()

    def paintEvent(self, event) -> None:
        """Outline, dot, word — and no fill under any of them.

        Unfilled because a pill is put on a card, in a row, and on the ground
        between them, and a fill would be this file naming which of those it
        stands on. The outline is `LINE`, the same hairline the cards are
        divided by, so the shape is what says *pill* and the border says nothing
        else.
        """
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Half a pixel in on every side, for `card.py`'s reason: a 1px pen
        # straddles the path it is given, so the widget's own rect would lose the
        # pen's outer half.
        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        corner = box.height() / 2
        painter.setPen(QPen(LINE, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(box, corner, corner)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._dot())
        painter.drawEllipse(
            QRectF(box.left() + _PAD_X, box.center().y() - _DOT, 2 * _DOT, 2 * _DOT).center(),
            _DOT,
            _DOT,
        )

        if self._text:
            painter.setPen(QPen(DIM))
            painter.drawText(
                QRectF(
                    box.left() + _PAD_X + 2 * _DOT + _GAP,
                    box.top(),
                    box.width(),
                    box.height(),
                ),
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                self._text,
            )
        painter.end()

    def _dot(self) -> QColor:
        """The one part that differs between the three kinds.

        The word is `DIM` in all of them and that is deliberate: a pill is a
        secondary mark wherever it stands, and lighting its text as well would
        make a live one compete with the name it is beside — which is the row's
        heading, and the thing actually worth reading first. An unknown kind
        falls to `IDLE` rather than raising, the way `button.py` falls to its
        default: a pill built from a string out of a document should say
        something plain, not take the pane down.
        """
        if self._kind == LIVE:
            return ACCENT
        if self._kind == OFF:
            return DIM
        return TEXT
