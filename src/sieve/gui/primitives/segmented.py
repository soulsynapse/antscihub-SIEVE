"""The segmented bar: a fixed few, side by side, exactly one of them on.

Lifted from `mockup/paper_primitives.py`, and the sixth control after
`button.py`, `field.py`, `slider.py`, `check.py` and `select.py`. It arrives
ahead of a view asking, the way most of them did, and what it settles is the
last size of *pick one* the tree had no answer at: a few options that are
alternatives to each other and are read together — three time scales, three
overlays, the walk's three positions — where the point is the comparison and not
the list.

That makes four answers to "pick one", and the split between them is the whole
reason there are four rather than one control stretched across all of it. A
radio (`check.py`) is a fixed few, each one a fact standing on its own line; a
section list (`nav.py`) is a few, and picking one *moves* you; a select
(`select.py`) is many, hidden, because standing them open would cost twelve
lines. This is a few whose options only mean anything against each other, which
is why they are one object in one row and not a column of boxes: a column
invites the eye to read each option, and a bar invites it to read the one that
is on. A view choosing between this and a radio should ask whether the options
would still make sense read one at a time — if they would, they are radios.

The dress is not the mockup's, and the departure is forced before it is chosen.
The mockup lights the current segment with an accent wash under accent text, and
a wash is not one of the eight roles; a ninth is a colour every palette below
would have to answer. But the tree already has an answer to *which of these
visible few is current*, and it is `nav.py`'s: an accent edge along the leading
side, never a fill, so that the option under the pointer and the option that is
on are never the same picture and can both be true at once. A horizontal bar's
leading side is its foot, so the mark is the same one turned ninety degrees, at
the same `nav.MARK_W` — restating that width here would be a second answer to
how wide the mark is, free to drift from the nav standing in the next card. The
rule runs under every segment and only its colour changes, for the reason `nav`
gives: a mark that appeared would step the labels of whichever segment gained
it.

Where it does part from the nav is the ink, and that is a difference in the
picture rather than in the rule. A nav's entries have a row each and the edge
down one of them is unmissable; three segments share one row, where the same
mark is a few pixels under one word among three. So the current segment's label
is `TEXT` and the others are `DIM` — which also gives the pointer something to
say on a segment that is already lit, since the fill under it is `PANEL_HOT`
either way.

It is styled and not painted, by `button.py`'s rule and not by preference: this
is filled boxes with text in them and a corner that is a number, which is the
shape a stylesheet is good at, and the collapsed border between two segments is
a `border-left-width: 0` rather than anything a painter is needed for. The one
thing the sheet cannot do is the focus ring, because a ring is drawn outside the
box — so this widget keeps `field.RING_GAP` of its own around the bar and paints
`field.ring()` there itself, the way `check.py` does and for the same reason.
The corner is `field.RADIUS` for the reason that constant is public: the ring is
drawn at whatever the box's corner is plus the inset, and a bar with a corner of
its own would be a bar the ring no longer follows.

Focus is the bar's and not each segment's, which is why the segments refuse it.
The keyboard's picture of this is one control with a value, the same as it is of
a select — tabbing into three stops for three views of one choice would make it
three controls — so the bar takes the tab stop and answers ← and →, which mean
"the next option" and are only answerable by the thing that knows what the
options are. That is `nav.py`'s split between ↑/↓ and Escape, on the other axis.

What is missing is the mockup's stretch after the last segment. The bar is as
wide as its widest label times its count and no wider, and every segment is that
width: options that are alternatives have to be comparable, and a bar whose
segments were each as wide as their own word would be three boxes of three sizes
saying that the longest one matters most.
"""

from __future__ import annotations

from typing import Sequence

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QSizePolicy, QWidget

from sieve.gui import metrics, palette
from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, PANEL_HOT, TEXT, mix, rgb
from sieve.gui.primitives.field import EDGE, RADIUS, RING_GAP, RING_W, ring
from sieve.gui.primitives.nav import MARK_W

#: The box around one segment's label. Its own numbers and not `button.py`'s,
#: because a segment's width is not its label's: the padding here is the air the
#: *widest* label gets, and every other segment is padded out past it to match.
#: The height is a button's, so a bar standing beside one does not set a taller
#: row than the verb next to it.
_PAD_X = 10
_PAD_Y = 6


class Segmented(QWidget):
    """A row of alternatives with one of them lit.

    It knows what it looks like and nothing about what choosing means, which is
    `chosen` and the caller's — the same split every primitive here makes.
    Handed its options rather than fetching any, for `select.py`'s reason.
    """

    #: Which option is on. Emitted on every move, the pointer's and the
    #: keyboard's alike, so the side that draws it follows both without either
    #: knowing about the other — `nav.py` names its own the same, since it is the
    #: same question asked of a different shape.
    chosen = Signal(int)

    def __init__(
        self,
        options: Sequence[str],
        current: int = 0,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("segmented")
        # It answers ← and →, so it has to be reachable by tabbing as well as by
        # clicking — a control the pointer alone can focus is one the keyboard
        # cannot get back to once anything else has had it.
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        # One row and no taller: a bar stands in a column of settings, and one
        # that stretched would put its labels somewhere other than where the
        # control above it put its own.
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._current = -1
        self._segments: list[QPushButton] = []

        row = QHBoxLayout(self)
        # The room the ring is drawn in, on every side. A ring painted on a
        # widget with no margins would clip against its own edge, and a ring that
        # is three sides of a rectangle is a rendering fault rather than a state.
        row.setContentsMargins(RING_GAP, RING_GAP, RING_GAP, RING_GAP)
        # Butted, not spaced: the divider between two segments is the left one's
        # own border, and a gap would make this a row of small buttons.
        row.setSpacing(0)
        for index, text in enumerate(options):
            segment = QPushButton(text)
            segment.setObjectName("segment")
            segment.setCursor(Qt.CursorShape.PointingHandCursor)
            # The tab stop is the bar's — see the module docstring. A segment
            # that took focus would also draw the platform's own focus rect
            # inside a box this file has already decided the look of.
            segment.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            segment.clicked.connect(lambda _=False, index=index: self.select(index))
            row.addWidget(segment)
            self._segments.append(segment)

        # Set rather than passed through `select`, which would refuse an index it
        # is already at and emit for one it is not: what a bar comes up on is not
        # a move, and nothing is connected yet to hear it called one.
        self._current = max(0, min(len(self._segments) - 1, current)) if self._segments else -1
        self._resize()
        # Bound methods and never lambdas, for the reason `button.py` gives:
        # PySide6 drops a connection to a bound method when the receiver goes,
        # where a lambda closing over `self` would keep a dead bar subscribed.
        palette.CHANGED.connect(self._dress)
        metrics.CHANGED.connect(self._resize)

    def current(self) -> int:
        """The option that is on, or -1 while there are none."""
        return self._current

    def select(self, index: int) -> None:
        """Light an option. Out of range is nothing, so a caller may hand this
        the result of an arithmetic without checking the ends first."""
        if not 0 <= index < len(self._segments) or index == self._current:
            return
        self._current = index
        self._dress()
        self.chosen.emit(index)

    def step(self, delta: int) -> None:
        """Move `delta` options, stopping at the ends rather than wrapping — a
        held key comes to rest on the last option instead of reappearing on the
        first. `nav.py` stops the same way."""
        if not self._segments:
            return
        self.select(max(0, min(len(self._segments) - 1, self._current + delta)))

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            self.step(-1 if key == Qt.Key.Key_Left else +1)
            event.accept()
            return
        # Everything else goes up, Escape among them: it means "close what is on
        # top" and is the overlay's, and an accepted key here is one the thing on
        # top never sees.
        super().keyPressEvent(event)

    def _resize(self) -> None:
        """The font at the size now in force, and the width that needs.

        Its own slot rather than a repaint, which is the difference from
        `palette.CHANGED`: a colour changes what this is drawn in, where a size
        changes how much of the row it takes. The widest label sets every
        segment's width, so the bar has to be measured again whenever the type
        does — a width computed once at build would be right until the user
        moved the slider in preferences and wrong after.
        """
        if not self._segments:
            return
        font = self.font()
        font.setPointSize(metrics.pt("name"))
        self.setFont(font)
        text = self.fontMetrics()
        width = max(text.horizontalAdvance(s.text()) for s in self._segments) + 2 * _PAD_X
        for segment in self._segments:
            segment.setFont(font)
            segment.setFixedWidth(width)
        self._dress()
        self.updateGeometry()

    def _dress(self) -> None:
        """A sheet per segment, in the palette and at the size now in use.

        Re-set on every move rather than toggled through a dynamic property, for
        `nav.py`'s reason: a property needs an unpolish/polish pair to take, and
        this is one string on one widget. It is rebuilt on `palette.CHANGED` as
        well, so it has to come back in whichever state the bar was left in —
        which is why `_current` is held here and not read back off a sheet.

        Scoped to `#segment` rather than to `QPushButton`, for the reason
        `button.py` gives: this stands inside a card whose sheet is on an
        ancestor, and a bare class rule would reach every button in the pane.
        """
        edge = rgb(mix(LINE, TEXT, EDGE))
        last = len(self._segments) - 1
        for index, segment in enumerate(self._segments):
            on = index == self._current
            left = RADIUS if index == 0 else 0
            right = RADIUS if index == last else 0
            segment.setStyleSheet(f"""
                #segment {{
                    background: {rgb(PANEL)};
                    color: {rgb(TEXT if on else DIM)};
                    border: 1px solid {edge};
                    border-left-width: {1 if index == 0 else 0}px;
                    border-bottom: {MARK_W}px solid {rgb(ACCENT if on else LINE)};
                    border-top-left-radius: {left}px;
                    border-bottom-left-radius: {left}px;
                    border-top-right-radius: {right}px;
                    border-bottom-right-radius: {right}px;
                    padding: {_PAD_Y}px {_PAD_X}px;
                    font-size: {metrics.pt("name")}pt;
                }}
                #segment:hover {{
                    background: {rgb(PANEL_HOT)};
                    color: {rgb(TEXT)};
                }}
                #segment:disabled {{
                    background: {rgb(PANEL_HOT)};
                    color: {rgb(DIM)};
                    border-bottom-color: {rgb(LINE)};
                }}
            """)

    def paintEvent(self, event) -> None:
        """The ring, and nothing else — the bar has no fill of its own outside
        the segments, so one standing on a card shows the card through it.

        Drawn on the row the segments occupy rather than on this widget's whole
        rect, which is what the margins above are for: the ring abuts the bar's
        edge instead of sitting a gap away from it.
        """
        del event
        if not self.hasFocus():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        inset = RING_W / 2
        box = QRectF(self.rect()).adjusted(
            RING_GAP - inset,
            RING_GAP - inset,
            inset - RING_GAP,
            inset - RING_GAP,
        )
        painter.setPen(QPen(ring(), RING_W))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(box, RADIUS + inset, RADIUS + inset)
        painter.end()
