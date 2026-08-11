"""The tab row: a few sections across the top, and which one the room shows.

Lifted from `mockup/paper_primitives.py`, and the second answer to the question
`nav.py` asked — *which section am I reading* — rather than a fifth answer to
*pick one*, which `segmented.py` closed. The split is what a click does after
it: a segmented bar sets a value and leaves the screen where it was, and this
replaces what is under it. A view choosing between the two should ask whether
the room below changes; if it does not, it is a bar.

What makes it a second file rather than an argument to the nav is the room, and
the number is `nav._WIDTH`. A section list is a fixed 150px column, which is the
right price in a card that has a pane's width to spend and the wrong one in the
right pane, where three words down the side take a third of the form they are
listing. Across the top the same three words cost one line at any width. So the
nav is the shape for a card with room to the side and this is the shape for a
card with room above, and neither is the general case — a card that has both is
choosing between two pictures and not between a widget and its transpose.

Everything about *which one is current* is the nav's and borrowed rather than
restated: `MARK_W` of accent along the leading edge, never a fill, so the tab
under the pointer and the tab being read are two pictures that can both be true.
A row's leading edge is its foot, which is where `segmented.py` already put the
same mark — and that collision is real and worth naming, because a tab row and a
segmented bar are both a row of words with an accent rule under one of them. The
thing that tells them apart is the enclosure. A bar is closed: a hairline all
the way round, a panel fill, one corner at each end, and it reads as a single
control holding a value. A tab row has no box at all — its floor is a hairline
that runs the full width of whatever is beneath it, past the last label to the
edge, and what that says is that the room below the rule belongs to the tab
above it. Hence the size policy, which is the one place this parts from the bar:
a `Segmented` is exactly as wide as its segments, and this takes the width it is
given, because a floor that stopped after the last word would be a bar drawn
without its ends.

The mark is reserved under every tab and only its colour changes, which is
`nav.py`'s rule and the reason the row is `MARK_W` taller than its text needs. A
mark that appeared where there was none would step the label above it every time
the selection moved.

Painted rather than styled, which is where it parts from `segmented.py` under
the rule that file states. A stylesheet is good at filled boxes with corners,
and there is not one here: no fill, no border, no radius — a floor, some words,
and a rule under one of them. Painting is also the only thing that draws the
floor past the last tab in one stroke; a row of styled buttons would need a
stretch after the last one carrying a `border-bottom` of its own, and a stretch
after the last segment is the thing the bar refuses.

What is declined from the mockup is the display font on the current tab. Bold is
wider, so the lit tab's span grows and every tab after it steps sideways as the
selection moves — the same fault the reserved mark is there to avoid, in the one
axis a mark cannot fix. The ink does the work instead, `TEXT` against `DIM`,
which is `segmented.py`'s answer and leaves the pointer something to say on a
tab that is already lit.

Focus is drawn on the current tab and not around the whole row, and this is the
other place the bar's answer does not carry. `Segmented` rings its whole box
because the box is one control with one value; the keyboard's target here is a
*place* — ← and → move which section is open — so the ring goes where the eye
should be, which is the tab it just moved to. It is `field.ring()` at
`field.RING_W`, inset within the tab's own span and above the mark, so the row
needs no margin of its own and the ring never covers the thing that says which
tab is current.
"""

from __future__ import annotations

from typing import Sequence

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from sieve.gui import metrics, palette
from sieve.gui.palette import ACCENT, DIM, LINE, TEXT
from sieve.gui.primitives.field import RADIUS, RING_W, ring
from sieve.gui.primitives.nav import MARK_W

#: The air around a tab's word. Wider than it is tall, and both are this file's
#: rather than the bar's: a segment's padding is measured so the *widest* label
#: has room and every other is padded out to match, where tabs are each their own
#: width and the number is only the gap between one word and the next. The height
#: is what keeps the row a head rather than a line of text with a rule under it.
_PAD_X = 12
_PAD_Y = 8

#: The gap between two tabs' spans, on top of their padding. Small, because the
#: spans do not draw themselves — the only thing separating two tabs is white,
#: and a gap wide enough to be noticed would read as two rows of one word.
_GAP = 2


class Tabs(QWidget):
    """A few section names in a row, one of them open, over the room it heads.

    It knows what it looks like and nothing about what a section holds, which is
    `chosen` and the caller's — the same split every primitive here makes, and
    the same one `SectionNav` makes on the other axis. Handed strings and
    reports an index; it has never heard of a setting.
    """

    #: Which section is open. Emitted on every move, the pointer's and the
    #: keyboard's alike, so the side that swaps the room below follows both
    #: without either knowing about the other. Named as `nav.py` and
    #: `segmented.py` name theirs, since it is the same question of a third
    #: shape.
    chosen = Signal(int)

    def __init__(
        self,
        names: Sequence[str],
        current: int = 0,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("tabs")
        # It answers ← and →, so it has to be reachable by tabbing as well as by
        # clicking — a surface the pointer alone can focus is one the keyboard
        # cannot get back to once anything else has had it.
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)
        # As wide as it is given and no taller than the row: the floor is the
        # top edge of what stands below, and one that stopped after the last word
        # would leave the room under it open at the side. See the docstring on
        # why this is the opposite of the bar's.
        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)

        self._names = list(names)
        self._current = max(0, min(len(self._names) - 1, current)) if self._names else -1
        self._hover = -1

        self._refont()
        # Bound methods and never lambdas, for the reason `button.py` gives:
        # PySide6 drops a connection to a bound method when the receiver goes,
        # where a lambda closing over `self` would keep a dead row subscribed.
        palette.CHANGED.connect(self.update)
        metrics.CHANGED.connect(self._refont)

    def current(self) -> int:
        """The section open, or -1 while there are none."""
        return self._current

    def select(self, index: int) -> None:
        """Open a section. Out of range is nothing, so a caller may hand this the
        result of an arithmetic without checking the ends first."""
        if not 0 <= index < len(self._names) or index == self._current:
            return
        self._current = index
        self.update()
        self.chosen.emit(index)

    def step(self, delta: int) -> None:
        """Move `delta` tabs, stopping at the ends rather than wrapping — a held
        key comes to rest on the last section instead of reappearing on the
        first. `nav.py` and `segmented.py` stop the same way."""
        if not self._names:
            return
        self.select(max(0, min(len(self._names) - 1, self._current + delta)))

    def sizeHint(self) -> QSize:
        spans = self._spans()
        width = int(spans[-1][0] + spans[-1][1]) if spans else 0
        return QSize(width, self._row_height())

    def minimumSizeHint(self) -> QSize:
        """As tall as the row and as wide as nothing. A tab row is put in a
        column that decides its width, and one that refused to be narrower than
        its words would push a pane wider rather than let the words clip."""
        return QSize(0, self._row_height())

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

    def mouseMoveEvent(self, event) -> None:
        self._set_hover(self._at(event.position().x()))
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self._set_hover(-1)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            index = self._at(event.position().x())
            if index >= 0:
                self.select(index)
                event.accept()
                return
        super().mousePressEvent(event)

    def _set_hover(self, index: int) -> None:
        """Note which tab the pointer is over, and dress the cursor for it.

        The hand is set as the pointer crosses a span rather than on the widget,
        which is the one thing here the mockup does differently: the floor runs
        the full width, so a cursor set once would offer a click over the empty
        room past the last word.
        """
        if index == self._hover:
            return
        self._hover = index
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if index >= 0 else Qt.CursorShape.ArrowCursor
        )
        self.update()

    def _refont(self) -> None:
        """The font at the size now in force, and the room that needs.

        Its own slot rather than a repaint, which is the difference from
        `palette.CHANGED`: a colour changes what the words are drawn in, where a
        size changes how much of the row they take and how tall the row is. A
        height measured once at build would be right until the user moved the
        slider in preferences and wrong after.
        """
        font = self.font()
        font.setPointSize(metrics.pt("name"))
        self.setFont(font)
        self.setFixedHeight(self._row_height())
        self.updateGeometry()
        self.update()

    def _row_height(self) -> int:
        """The word, the air around it, and the mark under it — which is there
        whether or not it is lit, so the words do not step when it moves."""
        return self.fontMetrics().height() + 2 * _PAD_Y + MARK_W

    def _spans(self) -> list[tuple[float, float]]:
        """Where each tab starts and how wide it is, measured at the size in
        force. Recomputed rather than held: the type size moves under a
        preference, and a table of positions cached at build is the one thing on
        screen still laid out for the old one."""
        text = self.fontMetrics()
        spans: list[tuple[float, float]] = []
        x = 0.0
        for name in self._names:
            width = text.horizontalAdvance(name) + 2 * _PAD_X
            spans.append((x, width))
            x += width + _GAP
        return spans

    def _at(self, x: float) -> int:
        """Which tab is under this, or -1 for the room past the last one. The gap
        between two spans belongs to neither, which is what keeps a click landing
        on the word it is under rather than on whichever neighbour rounded
        nearer."""
        for index, (left, width) in enumerate(self._spans()):
            if left <= x <= left + width:
                return index
        return -1

    def paintEvent(self, event) -> None:
        """A floor, the words, the mark, and the ring — in that order, because
        each of the last three stands on the one before it.

        The floor is drawn across the whole width and the mark over the stretch
        of it the current tab holds, rather than the floor being drawn in the
        gaps around the mark: one is a line with a brighter, thicker piece in it,
        which is what a tab row is, and the other is three lines that have to
        meet.
        """
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setFont(self.font())

        floor = self.height() - MARK_W / 2
        painter.setPen(QPen(LINE, MARK_W))
        painter.drawLine(QPointF(0, floor), QPointF(self.width(), floor))

        for index, (left, width) in enumerate(self._spans()):
            box = QRectF(left, 0, width, self.height() - MARK_W)
            lit = index == self._current
            painter.setPen(QPen(TEXT if lit or index == self._hover else DIM))
            painter.drawText(box, int(Qt.AlignmentFlag.AlignCenter), self._names[index])
            if not lit:
                continue
            painter.setPen(QPen(ACCENT, MARK_W))
            painter.drawLine(QPointF(left, floor), QPointF(left + width, floor))
            if self.hasFocus():
                # Inside the span and clear of the mark, so the ring says where
                # the keyboard is without covering what says which tab is open.
                inset = RING_W / 2
                painter.setPen(QPen(ring(), RING_W))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(
                    box.adjusted(inset, inset, -inset, -inset), RADIUS, RADIUS
                )
        painter.end()
