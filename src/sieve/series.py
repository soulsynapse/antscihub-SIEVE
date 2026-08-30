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

**A key is a place to come back to.** `Sinks` is the collection: one series
per key, kept past the binding that asked for it, so a knob moved and moved
back is a lookup and not a re-run. The rule it evicts by, and why it is not
ADR-0006's, is on the class.

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
from collections import OrderedDict
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
        return key_of(self.source, self.step_key, self.form_key)

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


def key_of(source: str, step_key: str, form_key: str) -> str:
    """The one spelling of a series key, so the collection and the series agree.

    A function rather than each side formatting the same three fields: a
    collection that filed under a key one character off from the one the
    series answers with would hand back a miss for something it holds, and
    the symptom is recomputed work rather than an error.
    """
    return f"{source}|{step_key}|{form_key}"


#: How many series no binding currently names are kept before the oldest is
#: dropped. A parameter dragged over a handful of values comes back to any of
#: them with its rows still covered; a sweep over hundreds does not grow
#: without bound. Cost is per row of the listing — four bytes of value, one of
#: coverage, eight of pts — so a stranded series over a hundred thousand rows
#: is about 1.3 MB, and this is a count because every series over one source is
#: the same size.
DEFAULT_KEPT = 16


class Sinks:
    """Every series written under one session, kept under its own key.

    **What this exists for is the re-key.** A step's key folds its params
    (ADR-0010) and a series is filed under that key and the form it was
    measured in, so moving a knob names a different series — correctly. What
    was wrong is what happened to the old one: the binding was rebuilt, a
    fresh empty series was made for every node, and the rows already covered
    under the previous key were held by nothing and could not be got back.
    Dragging a slider one notch and back recomputed a run that was still
    correct. Here the previous key is still a key, so it comes back covered.

    **Released is not dropped, and that is the difference from the pool.**
    ADR-0006's rule — held until released — is about frames, where a release
    is permission to evict. A series is the record of the work, and the reason
    to keep one is exactly that no binding names it right now: the parameter
    moved and will move back. So `release` only marks, and eviction is by
    recency among the unheld, capped at `DEFAULT_KEPT`. Whatever a binding is
    holding is never a candidate, however long it has sat.

    **A key that no longer means the same rows is not a hit.** Rows are ranks
    against a listing snapshot (ADR-0004), and nothing in the key folds the
    listing, so an extent that grew leaves a held series whose rows number
    against a table the new binding is not using. That is dropped and rebuilt
    rather than reused. The values were about real instants and merging them
    onto the new table would keep them; that is a merge, and it wants a
    consumer that has lost something to it before being written.

    **The lock guards the dict and nothing else.** Every operation under it is
    a dict touch; a series hands itself out and does its own locking from
    there, so a rebind on one thread and a read on another never wait on each
    other for longer than a lookup.
    """

    def __init__(self, kept: int = DEFAULT_KEPT) -> None:
        self.kept = max(0, kept)
        self._by_key: OrderedDict[str, Series] = OrderedDict()
        #: keys some binding is holding — never evicted, whatever their age
        self._held: set[str] = set()
        self._lock = threading.Lock()

    def series(self, source: str, step_key: str, form_key: str,
               listed: tuple[int, ...], timebase: str) -> Series:
        """The series for that key — the one already written into, if there is one."""
        key = key_of(source, step_key, form_key)
        pts = np.asarray(listed, dtype=np.int64)
        with self._lock:
            held = self._by_key.get(key)
            if held is not None and not np.array_equal(held.pts, pts):
                del self._by_key[key]
                held = None
            if held is None:
                held = Series(source=source, step_key=step_key,
                              form_key=form_key, pts=pts, timebase=timebase)
                self._by_key[key] = held
            self._by_key.move_to_end(key)
            self._held.add(key)
            self._evict()
        return held

    def release(self) -> None:
        """No binding holds anything now. Called where one is torn down.

        Everything released stays under its key; what the cap costs is the
        oldest of them, and the binding being replaced was the most recent
        user of its own, so a rebind never evicts what it is about to ask for.
        """
        with self._lock:
            self._held.clear()
            self._evict()

    def wipe(self) -> None:
        """Drop everything. What closing a recording calls."""
        with self._lock:
            self._by_key.clear()
            self._held.clear()

    def _evict(self) -> None:
        """Oldest-first among the unheld, down to the cap. Under the lock."""
        loose = [key for key in self._by_key if key not in self._held]
        for key in loose[: max(0, len(loose) - self.kept)]:
            del self._by_key[key]

    def __len__(self) -> int:
        with self._lock:
            return len(self._by_key)


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
