"""The run of views a pane shows one at a time, and the slide between them.

The right pane holds three things that are never read against each other — the
projects, the chain, the walked step's form — and one that is read against the
footage on the left at all times. Standing all three at once would take the room
from the fourth, and stacking them with no motion would leave the user to work
out which of three lookalike screens they are now on. So they sit side by side
on a track wider than the pane, and moving between them slides the track: the
direction of travel is the only thing that says where you now are relative to
where you were, and it is free, because the pane never changes size.

A position is a view (ADR-0001) and never a pane: the pane is the space, one
space, and what the swipe changes is its occupant. That is why the three are
positions on a track rather than three panes shown and hidden — the frame's
panes are countable and fixed, and a construct that grew two more of them every
time a screen was added would make "which pane" unanswerable.

The track is moved rather than the positions: one animated property, and every
position keeps the geometry it was given, so a plot mid-refill in the position
being left does not also get resized on its way off screen.
"""

from __future__ import annotations

from typing import Iterable, Sequence

from PySide6.QtCore import (
    Property,
    QAbstractAnimation,
    QEasingCurve,
    QPropertyAnimation,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from sieve.gui.frame.panes import Blank

#: How long the slide takes. Long enough to be read as travel and not a cut,
#: short enough that holding an arrow key walks the track rather than queueing
#: up a wait — the interactive loop is the product, and a transition the user
#: waits out is the loop's cost paid on every move.
SLIDE_MS = 260

#: The positions the right pane swipes between, in the order they sit on the
#: track. The order is the reading order of the work: the project you opened,
#: the chain in it, the step you are standing on in that chain — so ← and →
#: mean out and in, and nothing has to say which way is which.
POSITIONS = ("project", "pipeline", "step")


class Swipe(QWidget):
    """A track of positions inside one pane, one of them in front at a time.

    The widget is the window onto the track: it is the size of the pane, the
    track is that width times the number of positions, and `offset` is how many
    pane-widths along the track has been pulled. Positions are the swipe's
    children only through the track, so nothing outside sees them move.
    """

    def __init__(
        self, positions: Sequence[QWidget], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        if not positions:
            raise ValueError("a swipe with no positions has nothing to show")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._positions = list(positions)
        self._current = 0
        self._offset = 0.0

        self._track = QWidget(self)
        for position in self._positions:
            position.setParent(self._track)

        self._animation = QPropertyAnimation(self, b"offset", self)
        self._animation.setDuration(SLIDE_MS)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._relayout()

    # -- the animated property ------------------------------------------

    def _get_offset(self) -> float:
        return self._offset

    def _set_offset(self, value: float) -> None:
        self._offset = float(value)
        self._track.move(-round(self._offset * self.width()), 0)

    #: How far along the track the pane is looking, in pane-widths. Written by
    #: the animation and by every resize, which is why it is a property and not
    #: an argument to `go`.
    offset = Property(float, _get_offset, _set_offset)

    # -- where the swipe is standing -------------------------------------

    def current(self) -> int:
        """Which position is in front — the one asked for, not the one drawn.

        Reported from the start of the slide rather than its end: what the
        window is standing on is what the keys will act on next, and a caller
        that had to wait out the animation to be told would be answering the
        user's second keystroke against their first position.
        """
        return self._current

    def position(self, index: int) -> QWidget:
        """The view standing at `index`, whether or not it is in front."""
        return self._positions[index]

    def count(self) -> int:
        return len(self._positions)

    # -- moving ----------------------------------------------------------

    def go(self, index: int) -> None:
        """Slide until `index` is in front. Asking for where you are is nothing.

        Unless a slide is already running, in which case it is a re-aim: the
        arrows are held down and each keystroke restarts the animation from
        wherever the track has got to, so the track never jumps back to a
        position it was already leaving.
        """
        if not 0 <= index < len(self._positions):
            raise ValueError(
                f"a swipe of {len(self._positions)} has no position {index}"
            )
        running = self._animation.state() == QAbstractAnimation.State.Running
        if index == self._current and not running:
            return
        self._current = index
        self._animation.stop()
        self._animation.setStartValue(self._offset)
        self._animation.setEndValue(float(index))
        self._animation.start()

    def step(self, delta: int) -> None:
        """Move `delta` positions, stopping at the ends rather than wrapping.

        Clamped and not wrapped because the track is a line and reads as one:
        the ends are where a held arrow key comes to rest, and a wrap would put
        the user at the far end of the work with the slide saying they had
        walked one step further into it.
        """
        self.go(max(0, min(len(self._positions) - 1, self._current + delta)))

    # -- geometry --------------------------------------------------------

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._relayout()

    def _relayout(self) -> None:
        """Re-cut the track to the pane's size and put it back where it was.

        The offset is in pane-widths, so it survives the resize untouched and
        the position in front stays in front; it is re-applied here because the
        pixels it works out to have just changed.
        """
        width, height = self.width(), self.height()
        self._track.resize(width * len(self._positions), height)
        for index, position in enumerate(self._positions):
            position.setGeometry(index * width, 0, width, height)
        self._set_offset(self._offset)


def build_swipe(pane: str = "right", names: Iterable[str] = POSITIONS) -> Swipe:
    """The swipe as the right pane has it: one blank per position, in order.

    Blank for the reason the panes are — what stands here is the frame's claim
    about how many positions there are and which way they run, and that claim
    is checkable only while nothing inside it is contributing a size hint or a
    scroll of its own.
    """
    return Swipe([Blank(f"{pane} {name}") for name in names])
