"""A step's reduced output, and the explicit record of which rows have one.

The analysis tier the storage plan named and did not build: one float per
position per step, a coverage record beside it, and a pts table saying what
a row means. Small on purpose — what it exists to get right is not layout
but bookkeeping, and every property below is a listed failure mode rather
than a preference.

**Coverage is recorded, never inferred.** An unwritten row and a row whose
value is genuinely zero are indistinguishable in the values array, and every
consumer added later is one that does not know to check. So `covered` is its
own array and `get` returns `None` rather than a number it cannot vouch for.
A boolean per row is cheap enough that a denser encoding is not yet worth
its bug surface.

**A row means a pts, not an ordinal.** The array is integer-addressed
because arrays are; what row *i* is a statement about is `pts[i]`, which is
ADR-0004 applied to the one structure here that outlives a process. The
footage this tree runs on answers "how many frames" three different ways, so
a series naming rows by position agrees with a store that counted
differently right up until it silently does not.

**Warm-up rows are not covered.** A step whose oldest admitted input sits
*k* rows back has no honest value for the first *k* rows of any run it
computes: the window is not full, and what it produces there is an artefact
of where the run began. Writing that and masking it at display is the
failure `docs/decode/ideas.md` records — the value still exists for anything
that does not mask, and a later overlapping run supplies the honest one, so
one row ends up with two answers. `first_honest` names the boundary and
producers ask it, because a `put` of a single row cannot tell whether the
window behind it was full.

**Every access takes the lock.** A series is written by whichever thread
admitted the input and read by whichever one is drawing, so the guard
belongs here rather than in each caller's discipline. Reads that hand an
array outward copy it under the lock: a numpy slice is a view, and a view of
a buffer another thread is writing is a race whose symptom is a plausible
number rather than a crash.

**Invalidation needs no machinery, but it does need a bump.** What a
stored value depends on is folded into the tool key and the form key, so a
change upstream of the series names a different series and a change
downstream of it — a threshold read off the numbers, a smoothing applied at
display — names the same one and correctly reuses it. The half of that a
key cannot derive is the step's own code, which is why `tools.Tool.key`
folds a version its author bumps. Nothing here checks that it was bumped:
a `field` edited without one names the series it just stopped agreeing
with, and this file will hand back the old numbers as covered.

**What is missing, stated so nobody assumes otherwise.** `get` answers for
one row and nothing answers for a *span*: a consumer asking whether a
stretch is usable has to walk `runs` and `missing` itself, and one that
instead reads uncovered rows as computed zeros repeats the failure coverage
exists to prevent, one level further down the chain. There is also no third
state — a producer emitting provisional values and revising them later has
nowhere to say so, and anything reading one reads it as final. Both are
known gaps, and both want a real consumer before being designed for.

Layout is deliberately unanswered. A per-position scalar series is already
time-major, and one compressed array per key with a sidecar naming what it
is remains the null hypothesis anything more elaborate has to beat.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class Series:
    """One step's reduced output over one source, in one form."""

    source: str          #: what the inputs came from
    tool_key: str        #: tools.Tool.key() — folds the params the field uses
    form_key: str        #: forms.Form.key() — the picture it is about
    pts: np.ndarray      #: int64 ticks, one per row; the row's real identity
    timebase: str        #: the stream's own, recorded once beside the ticks
    values: np.ndarray = None    # type: ignore[assignment]
    covered: np.ndarray = None   # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.lock = threading.RLock()
        n = len(self.pts)
        if self.values is None:
            self.values = np.zeros(n, dtype=np.float32)
        if self.covered is None:
            self.covered = np.zeros(n, dtype=bool)

    @property
    def key(self) -> str:
        """Source, step and form — everything the values depend on."""
        return f"{self.source}|{self.tool_key}|{self.form_key}"

    # ── reading ──────────────────────────────────────────────────────────
    def get(self, row: int) -> float | None:
        """The value, or `None` — never a zero standing in for absence."""
        with self.lock:
            if 0 <= row < len(self.values) and self.covered[row]:
                return float(self.values[row])
        return None

    def snapshot(self, start: int, end: int):
        """Copies of the values and the coverage over a span.

        Copies rather than slices: a slice is a view on a buffer another
        thread is still writing, so handing one outward is a race that
        returns plausible numbers instead of failing.
        """
        with self.lock:
            return (self.values[start:end].copy(),
                    self.covered[start:end].copy())

    def first_honest(self, start: int, reach: int) -> int:
        """The first row a run beginning at `start` may vouch for.

        Asked rather than worked out by each producer, because a producer
        that derives it privately can get it wrong quietly, and a wrong
        answer writes an artefact of where the run began into a row a later
        run will disagree with.
        """
        return start + max(0, reach)

    def runs(self, start: int, end: int) -> list[tuple[int, int]]:
        """Covered stretches within `[start, end)`, as half-open rows."""
        with self.lock:
            return _runs(self.covered[start:end].copy(), start, True)

    def missing(self, start: int, end: int) -> list[tuple[int, int]]:
        """Uncovered stretches — what an ordered pass still owes.

        What such a pass must *work through* to close one of these is wider
        than the gap, by the step's reach on the leading edge: an honest
        value at row *r* needs everything back to `r - reach` available,
        even where sparse offsets mean only a few are held. A scheduler
        pricing a gap prices `gap + reach`.
        """
        with self.lock:
            return _runs(self.covered[start:end].copy(), start, False)

    def coverage(self, start: int, end: int) -> float:
        """The fraction of `[start, end)` that has a value."""
        with self.lock:
            span = self.covered[start:end]
            return float(span.mean()) if len(span) else 0.0

    # ── writing ──────────────────────────────────────────────────────────
    def put(self, row: int, value: float) -> None:
        """One row's value.

        Called where the inputs it was computed from were admitted, and
        never by anything that draws (ADR-0005). The input is equally hot
        either way; what differs is that admission happens on a cadence the
        producer controls and drawing happens on one the machine decides,
        so only the first is reproducible.
        """
        with self.lock:
            if 0 <= row < len(self.values):
                self.values[row] = value
                self.covered[row] = True

    # ── persistence ──────────────────────────────────────────────────────
    def save(self, root: Path) -> Path:
        """Write the arrays, and a sidecar naming what they are.

        The sidecar is not decoration: an array on disk whose key has to be
        recovered by parsing its filename is one that stops being readable
        the first time a key gains a character that a path cannot hold.
        """
        with self.lock:
            values, covered = self.values.copy(), self.covered.copy()
        root.mkdir(parents=True, exist_ok=True)
        stem = self.key.replace("|", "__").replace("/", "-").replace(":", "-")
        path = root / f"{stem}.npz"
        np.savez_compressed(path, values=values, covered=covered,
                            pts=self.pts)
        path.with_suffix(".json").write_text(json.dumps({
            "source": self.source, "tool_key": self.tool_key,
            "form_key": self.form_key, "timebase": self.timebase,
            "rows": int(len(self.pts)),
            "covered": int(covered.sum()),
        }, indent=1), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path) -> "Series":
        """Read one back, taking its identity from the sidecar."""
        meta = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
        blob = np.load(path)
        return cls(source=meta["source"], tool_key=meta["tool_key"],
                   form_key=meta["form_key"], pts=blob["pts"],
                   timebase=meta["timebase"], values=blob["values"],
                   covered=blob["covered"])


def _runs(mask: np.ndarray, offset: int, want: bool) -> list[tuple[int, int]]:
    """Contiguous stretches of `mask` equal to `want`, as half-open rows."""
    out: list[tuple[int, int]] = []
    run_start = None
    for i, flag in enumerate(mask):
        if bool(flag) == want and run_start is None:
            run_start = i
        elif bool(flag) != want and run_start is not None:
            out.append((run_start + offset, i + offset))
            run_start = None
    if run_start is not None:
        out.append((run_start + offset, len(mask) + offset))
    return out
