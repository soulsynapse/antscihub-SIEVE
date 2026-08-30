"""What row a listed position is, in one store's snapshot of a listing.

ADR-0004 admits an ordinal only as a per-store coordinate carried beside a
table, and this is that table. It lived in `serve.py` until the pipeline
needed it too, and a pipeline reaching into the tier stack for it would have
been the package importing something its own statement says it must not own.
It depends on nothing, which is the other half of why it is here.
"""

from __future__ import annotations


class Ordinals:
    """A listing snapshot and the table that says what row *i* of it means.

    ADR-0004 admits an ordinal only as a per-store coordinate carried beside a
    table, and this is that table. It is deliberately *not* on `Store`, which
    holds that an extent is asked and never stored: a growing folder must move
    `Store.positions` under everything that asks. Here the snapshot is the
    point — chunks are filed by ordinal, and a grid that renumbered itself
    when a still landed would file the next chunk over the last one.

    Which also names the bug: a source still being written into grows past
    this and nothing re-takes it. `docs/vertical-slice.md` carries that as
    untested rather than as fixed.
    """

    def __init__(self, listed: tuple[int, ...]) -> None:
        self.listed = listed
        self._rank = {position: index for index, position in enumerate(listed)}

    def __len__(self) -> int:
        return len(self.listed)

    def rank(self, position: int) -> int | None:
        """Which row *position* is, or None if this listing has no such frame."""
        return self._rank.get(position)

    def around(self, position: int, radius: int,
               within: tuple[int, int] | None = None) -> tuple[int, ...]:
        """Listed positions within *radius* rows of *position*.

        In rows and never in pts, which is the mistake this exists to make
        unavailable: at 90 kHz over 23.976 fps one frame is 3753.75 ticks, so
        a pts difference compared against a count of frames reads every
        ordinary step as a jump.

        `within` clips to a half-open span of ordinals — the filled window,
        whose frames are the only ones anything holds.
        """
        here = self.rank(position)
        if here is None:
            return ()
        low, high = (0, len(self.listed)) if within is None else within
        return self.listed[max(low, here - radius):min(high, here + radius + 1)]
