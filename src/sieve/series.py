"""A step's reduced output, and the explicit record of which rows have one.

Ported from `experiments/tool-experiments/series.py`, whose docstring carries
the argument for each property; what follows is what a reader of this tree has
to know to use it correctly.

**Coverage is recorded, never inferred.** An unwritten row and a row whose
value is genuinely zero are indistinguishable in the values array, and every
consumer added later is one that does not know to check. So `covered` is its
own array and `get` returns `None` rather than a number it cannot vouch for.

**A row means a pts, not an ordinal.** The array is integer-addressed because
arrays are; what row *i* is a statement about is `pts[i]` (ADR-0004).

**Warm-up rows are not covered.** A step whose oldest admitted input sits *k*
rows back has no honest value for the first *k* rows of a run: the window is
not full, and what it produces there is an artefact of where the run began.
`first_honest` names the boundary and producers ask it, because a `put` of a
single row cannot tell whether the window behind it was full.

**Every access takes the lock**, and reads that hand an array outward copy it
under the lock — a numpy slice is a view, and a view of a buffer another
thread is writing is a race whose symptom is a plausible number.

**Not persisted.** The experiment's `save`/`load` are deliberately left
behind: what a series is filed under on disk is part of the persistent format
that has not been decided, and a shape written now is one that has to be read
forever. Nothing in this tree outlives its session yet.

**Known gaps, stated so nobody assumes otherwise.** Nothing answers whether a
*span* is usable — a consumer walks `runs` and `missing` itself, and one that
reads uncovered rows as computed zeros repeats the failure coverage exists to
prevent. There is no provisional third state. Both want a real consumer before
being designed for.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

import numpy as np


@dataclass
class Series:
    """One step's reduced output over one source, in one form."""

    source: str          #: what the inputs came from
    step_key: str        #: folds this step's params, version and prefix
    form_key: str        #: `forms.Form.key()` — the picture it is about
    pts: np.ndarray      #: int64 ticks, one per row; the row's real identity
    timebase: str        #: the stream's own, recorded once beside the ticks
    values: np.ndarray = None    # type: ignore[assignment]
    covered: np.ndarray = None   # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.lock = threading.RLock()
        rows = len(self.pts)
        if self.values is None:
            self.values = np.zeros(rows, dtype=np.float32)
        if self.covered is None:
            self.covered = np.zeros(rows, dtype=bool)

    @property
    def key(self) -> str:
        """Source, step and form — everything the values depend on."""
        return f"{self.source}|{self.step_key}|{self.form_key}"

    # -- reading -----------------------------------------------------------

    def get(self, row: int) -> float | None:
        """The value, or `None` — never a zero standing in for absence."""
        with self.lock:
            if 0 <= row < len(self.values) and self.covered[row]:
                return float(self.values[row])
        return None

    def snapshot(self, start: int, end: int) -> tuple[np.ndarray, np.ndarray]:
        """Copies of the values and the coverage over a span."""
        with self.lock:
            return (self.values[start:end].copy(),
                    self.covered[start:end].copy())

    def first_honest(self, start: int, reach: int) -> int:
        """The first row a run beginning at `start` may vouch for.

        Asked rather than worked out by each producer: one that derives it
        privately can get it wrong quietly, and a wrong answer writes an
        artefact of where the run began into a row a later run disagrees with.
        """
        return start + max(0, reach)

    def runs(self, start: int, end: int) -> list[tuple[int, int]]:
        """Covered stretches within `[start, end)`, as half-open rows."""
        with self.lock:
            return _runs(self.covered[start:end].copy(), start, True)

    def missing(self, start: int, end: int) -> list[tuple[int, int]]:
        """Uncovered stretches — what an ordered pass still owes.

        What such a pass must *work through* to close one is wider than the
        gap, by the step's reach on the leading edge: a scheduler pricing a
        gap prices `gap + reach`.
        """
        with self.lock:
            return _runs(self.covered[start:end].copy(), start, False)

    def coverage(self, start: int, end: int) -> float:
        """The fraction of `[start, end)` that has a value."""
        with self.lock:
            span = self.covered[start:end]
            return float(span.mean()) if len(span) else 0.0

    # -- writing -----------------------------------------------------------

    def put(self, row: int, value: float) -> None:
        """One row's value.

        Called where the inputs it was computed from were admitted, and never
        by anything that draws (ADR-0005). The input is equally hot either
        way; what differs is that admission happens on a cadence the producer
        controls and drawing happens on one the machine decides.
        """
        with self.lock:
            if 0 <= row < len(self.values):
                self.values[row] = value
                self.covered[row] = True


def _runs(mask: np.ndarray, offset: int, want: bool) -> list[tuple[int, int]]:
    """Contiguous stretches of `mask` equal to `want`, as half-open rows."""
    out: list[tuple[int, int]] = []
    start = None
    for row, flag in enumerate(mask):
        if bool(flag) == want and start is None:
            start = row
        elif bool(flag) != want and start is not None:
            out.append((start + offset, row + offset))
            start = None
    if start is not None:
        out.append((start + offset, len(mask) + offset))
    return out
