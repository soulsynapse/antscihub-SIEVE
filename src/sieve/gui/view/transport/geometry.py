"""Where a position lands on a strip, and which position a pixel names.

The mockup's version of this mapped a frame *number* to a column, over a
constant count and a constant rate. Neither survives contact with the source
contract: an extent may still be growing, and nothing promises positions are
evenly spaced in their own timebase or that the timebase means anything —
a folder of stills has one tick per image because the contract requires a
timebase and stills carry no time at all.

**Positions map by their ordinal, not by their value.** Every listed position
gets the same width, which is true of every source and needs nothing to be
invented. Mapping by pts would draw real elapsed time, which is better exactly
where a timebase is real and is a fiction drawn to scale everywhere else; and
`docs/decode/ideas.md` already prefers the stable grid, because stable is what
caches.

**Rebuilt per paint, never held.** It is four fields and an integer division,
and the thing it is about — how many positions there are, how wide the widget
is — changes under it. A cached mapping is the extent-as-a-constant mistake
`sieve/store.py` already made once.

Nothing here imports Qt: what it deals in is positions, ordinals and floats,
and keeping it plain is what lets the mapping be checked without a widget.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass

#: A span narrower than this is drawn at this width instead. A window of one
#: position is a real thing to have and an invisible one is a bug report.
MIN_SPAN = 2.0


@dataclass(frozen=True, slots=True)
class Geometry:
    """The strip's mapping between listed positions and columns."""

    #: what the source lists, ascending — the extent as of this paint
    positions: tuple[int, ...]
    width: float

    @property
    def empty(self) -> bool:
        return not self.positions or self.width <= 0.0

    @property
    def count(self) -> int:
        return len(self.positions)

    # -- position to column ------------------------------------------------

    def ordinal(self, position: int) -> int:
        """Where *position* sits in the listing. Nearest at or below it.

        Nearest rather than exact because a caller may hold a position from
        before the extent moved, or one a source minted between two others,
        and a scrub bar that raised on an unknown position would be a widget
        that fails on the case it exists to survive.
        """
        if not self.positions:
            return 0
        found = bisect_right(self.positions, position) - 1
        return min(max(found, 0), self.count - 1)

    def left_of(self, position: int) -> float:
        """The left edge of the column *position* occupies."""
        if self.empty:
            return 0.0
        return self.ordinal(position) / self.count * self.width

    def centre_of(self, position: int) -> float:
        """The middle of that column — where a playhead line is drawn."""
        if self.empty:
            return 0.0
        return (self.ordinal(position) + 0.5) / self.count * self.width

    def span(self, start: int, end: int) -> tuple[float, float]:
        """A run's left and right edges, never narrower than `MIN_SPAN`."""
        left = self.left_of(start)
        right = (self.ordinal(end) + 1) / self.count * self.width if not self.empty else 0.0
        return left, max(right, left + MIN_SPAN)

    # -- column to position ------------------------------------------------

    def at(self, x: float) -> int | None:
        """Which position a column names, or None if there is nothing there."""
        if self.empty:
            return None
        index = int(x / self.width * self.count)
        return self.positions[min(max(index, 0), self.count - 1)]
