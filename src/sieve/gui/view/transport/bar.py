"""The strip: the whole recording as one band, with a playhead on it.

Ported from `mockup/mockup.py`'s `MockStrip`, which is where the paint, the
hit test and the bubble were designed. What changed is everything the mockup
took from a constant: it stood on a fixed frame count and a fixed rate, and
the strip a real source needs stands on an extent that may still be growing
and a timebase that may be invented.

**It reports intent and never policy.** `docs/decode/ideas.md`: a drag is a
guess, a release is a commitment, a playback tick is neither. This emits all
three as separate signals and decides nothing about how any of them is served
— which is what lets a tier land later without the strip being touched.

**It shows where you are even when the picture cannot.** The bubble carries
the position under the cursor throughout a drag. On a fixed camera every frame
looks alike, and the session explorer measured drags repainting at ~90 Hz and
still reading as frozen, which is a fact about the footage rather than about
the loop.

**A source that cannot be scrubbed says so by not being scrubbable.** With
`Access.FORWARD` the band draws its head and refuses every gesture, rather
than accepting one and serving something else. That is `lseek` on a pipe:
the honest refusal, never the emulation.

Nothing that updates participates in layout negotiation — the size policy is
fixed in height and ignored across, per
`docs/findings/2026.08.22-what-froze-the-felt-loop.md`, where a text label
nudging a splitter was what resized the video every few seconds.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QFontMetricsF, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from sieve.contract.edges import Access
from sieve.gui.palette import DIM, LINE, STACK_BG, TEXT
from sieve.gui.view.transport.geometry import Geometry

#: Tall enough for a band, a bubble over it, and the marks below.
HEIGHT = 96

_TRACK_INSET = 4.0
_BUBBLE_PAD = (8.0, 3.0)
#: Height of the row along the bottom that draws what the source can start at.
_STARTS_BAND = 5.0
#: Below this spacing in pixels the ticks are a filled bar and are not drawn.
_STARTS_APART = 6.0


class Strip(QWidget):
    """One recording end to end. Emits where the user pointed; serves nothing."""

    #: a guess — the pointer moved with the button down. Cheap answers only.
    dragged = Signal(int)
    #: a commitment — the button came up here. This one may be paid for.
    released = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.setMouseTracking(True)
        self._positions: tuple[int, ...] = ()
        self._starts: frozenset[int] = frozenset()
        self._playhead: int | None = None
        self._hover: int | None = None
        self._scrubbing = False
        self._scrubbable = True
        self._follow_cursor()

    # -- what it is about --------------------------------------------------

    def show_source(
        self,
        positions: tuple[int, ...],
        starts: tuple[int, ...] = (),
        access: Access = Access.RANDOM,
    ) -> None:
        """Take the extent, the starts, and what may be asked of the source."""
        self._positions = positions
        self._starts = frozenset(starts)
        self._scrubbable = access is Access.RANDOM
        if self._playhead is not None and self._playhead not in set(positions):
            self._playhead = positions[0] if positions else None
        self._follow_cursor()
        self.update()

    def show_playhead(self, position: int | None) -> None:
        if position == self._playhead:
            return
        self._playhead = position
        self.update()

    def playhead(self) -> int | None:
        return self._playhead

    def geometry_now(self) -> Geometry:
        return Geometry(self._positions, float(self.width()))

    # -- painting ----------------------------------------------------------

    def _bubble_text(self) -> str:
        where = self._hover if self._hover is not None else self._playhead
        if where is None:
            return ""
        mapping = self.geometry_now()
        return f"{mapping.ordinal(where) + 1:,} / {mapping.count:,}   pts {where:,}"

    def _bubble_rect(self, text: str) -> QRectF:
        if not text or self._hover is None:
            return QRectF()
        pad_x, pad_y = _BUBBLE_PAD
        metrics = QFontMetricsF(self.font())
        width = metrics.horizontalAdvance(text) + 2.0 * pad_x
        height = metrics.height() + 2.0 * pad_y
        centre = self.geometry_now().centre_of(self._hover)
        left = max(min(centre - width / 2.0, self.width() - width), 0.0)
        return QRectF(left, _TRACK_INSET, width, height)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        track = QRectF(self.rect()).adjusted(0.0, _TRACK_INSET, 0.0, -_TRACK_INSET)
        painter.fillRect(track, STACK_BG)
        painter.setPen(QPen(LINE, 1.0))
        painter.drawRect(track.adjusted(0.5, 0.5, -0.5, -0.5))

        mapping = self.geometry_now()
        if mapping.empty:
            painter.setPen(DIM)
            painter.drawText(
                self.rect(), int(Qt.AlignmentFlag.AlignCenter), "nothing open"
            )
            painter.end()
            return

        self._paint_starts(painter, track, mapping)
        if self._playhead is not None:
            painter.setPen(QPen(TEXT, 1.0))
            x = mapping.centre_of(self._playhead)
            painter.drawLine(QPointF(x, track.top()), QPointF(x, track.bottom()))

        text = self._bubble_text()
        box = self._bubble_rect(text)
        if not box.isEmpty():
            painter.setPen(QPen(LINE, 1.0))
            painter.setBrush(STACK_BG)
            painter.drawRoundedRect(box, 3.0, 3.0)
            painter.setPen(TEXT)
            painter.drawText(box, int(Qt.AlignmentFlag.AlignCenter), text)
        painter.end()

    def _paint_starts(self, painter, track: QRectF, mapping: Geometry) -> None:
        """A row of ticks along the foot: where a read may begin.

        Drawn because it is the one thing about a source a person cannot see
        in the picture and will feel immediately — those are the columns a
        landing is cheap at.

        Not drawn when every position is one, since a solid bar says nothing
        the absence of a bar does not — and not drawn when they crowd closer
        than `_STARTS_APART` either, which is the same statement about a
        different denominator: 472 keyframes across this window's width comb
        down to a filled strip, and a filled strip is the picture that means
        "all of them". Zooming is what makes them legible, and there is no
        zoom yet.
        """
        if not self._starts or len(self._starts) >= mapping.count:
            return
        columns = [mapping.centre_of(p) for p in sorted(self._starts)]
        if len(columns) > 1 and (columns[-1] - columns[0]) / (len(columns) - 1) < _STARTS_APART:
            return
        foot = QRectF(track.left(), track.bottom() - _STARTS_BAND,
                      track.width(), _STARTS_BAND)
        painter.setPen(QPen(DIM, 1.0))
        for x in columns:
            painter.drawLine(QPointF(x, foot.top()), QPointF(x, foot.bottom()))

    # -- gestures ----------------------------------------------------------

    def _follow_cursor(self) -> None:
        self.setCursor(
            Qt.CursorShape.PointingHandCursor
            if self._scrubbable
            else Qt.CursorShape.ForbiddenCursor
        )

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton or not self._scrubbable:
            super().mousePressEvent(event)
            return
        self._scrubbing = True
        self._aim(event.position(), guess=True)

    def mouseMoveEvent(self, event) -> None:
        position = self.geometry_now().at(event.position().x())
        if position != self._hover:
            self._hover = position
            self.update()
        if self._scrubbing:
            self._aim(event.position(), guess=True)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton or not self._scrubbing:
            super().mouseReleaseEvent(event)
            return
        self._scrubbing = False
        self._aim(event.position(), guess=False)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        if self._hover is not None:
            self._hover = None
            self.update()

    def _aim(self, at: QPointF, *, guess: bool) -> None:
        """Move the playhead and say which kind of ask this was.

        The playhead moves on the guess as well as the commitment, because it
        is the answer to "where am I", which is known immediately — what is
        not yet known is what the picture there looks like, and that is the
        receiver's problem rather than this widget's.
        """
        position = self.geometry_now().at(at.x())
        if position is None:
            return
        self.show_playhead(position)
        (self.dragged if guess else self.released).emit(position)
