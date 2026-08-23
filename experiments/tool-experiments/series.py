"""The reduced series, and the explicit record of which frames have one.

Tier 4 of the storage plan — the analysis cache — is the one tier never
built and never felt. The session explorer computes DIS over the covered run
on every debounce and throws the result away, which was honest as an
instrument for the felt cost and leaves the time-columnar half of the plan
with nothing behind it. This is the smallest thing that can stand in for it:
one float per frame per tool, a coverage record beside it, and a pts table
saying what a row means.

Three properties it has to have, each of which is a listed failure mode
rather than a preference.

**Coverage is recorded, never inferred.** An unwritten frame and a frame
whose value really is zero read identically in the values array, and every
consumer added later is one that does not know to check. So `covered` is its
own array and `get` returns `None` rather than a number it cannot vouch for.
A boolean per frame is eleven kilobytes for the 5.3K source's whole
timeline; an RLE would be smaller and is not yet worth the bug surface.

**A row means a pts, not an ordinal.** The array is integer-addressed
because arrays are, and what row *i* is a statement about is
`pts[i]` — ADR-0004's split, applied to the one structure in this folder
that is durable. The footage this tree runs on answers "how many frames"
three different ways, so a series that names frames by position agrees with
a store that counted differently right up until it silently does not.

**The warm-up rows are not covered.** A tool whose oldest requirement sits
*k* rows back has no honest value for the first *k* frames of any run it
computes: the window is not
full, and whatever it produces there is an artefact of where the sweep
happened to start. Writing it and masking it at display is the failure
`docs/decode/ideas.md` records — the value still exists for anything that
does not mask, and a later overlapping sweep supplies the honest one, so
there are then two answers for one frame. `write_sweep` refuses the warm-up
rows rather than trusting callers to drop them.

Invalidation is by key and needs no machinery: what a stored value depends
on is folded into the tool's key and the form's key, so a change upstream of
the series names a different series, and a change downstream of it — a
threshold read off the numbers, a smoothing window at display — names the
same one and correctly reuses it.

The layout question the plan raises (chunked, time-major, Zarr) is not
answered here and does not need to be to measure anything: a per-frame
scalar series is already time-major, and one `.npy` per key is the null
hypothesis the series-tier experiment has to beat.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class Series:
    """One tool's reduced output over one source, in one form."""

    source: str          #: what the frames came from
    tool_key: str        #: tools.Tool.key() — folds the params the field uses
    form_key: str        #: forms.Form.key() — the picture it is about
    pts: np.ndarray      #: int64 ticks, one per row; the row's actual identity
    timebase: str        #: e.g. "1/90000", recorded once beside the ticks
    values: np.ndarray = None    # type: ignore[assignment]
    covered: np.ndarray = None   # type: ignore[assignment]

    def __post_init__(self) -> None:
        n = len(self.pts)
        if self.values is None:
            self.values = np.zeros(n, dtype=np.float32)
        if self.covered is None:
            self.covered = np.zeros(n, dtype=bool)

    @property
    def key(self) -> str:
        return f"{self.source}|{self.tool_key}|{self.form_key}"

    # ── reading ──────────────────────────────────────────────────────────
    def get(self, row: int) -> float | None:
        """The value, or `None` — never a zero standing in for absence."""
        if 0 <= row < len(self.values) and self.covered[row]:
            return float(self.values[row])
        return None

    def runs(self, start: int, end: int) -> list[tuple[int, int]]:
        """Covered stretches within `[start, end)`, as half-open rows."""
        return _runs(self.covered[start:end], start, True)

    def missing(self, start: int, end: int) -> list[tuple[int, int]]:
        """Uncovered stretches — what a sweep still owes.

        The frames a sweep must *decode* to close one of these is wider
        than the gap by the tool's reach on the leading edge: to produce an
        honest value at row *r* it needs everything back to `r - reach`
        decoded, even where its offsets are sparse enough that it only
        *holds* a few. A scheduler pricing a gap prices `gap + reach`.
        """
        return _runs(self.covered[start:end], start, False)

    def coverage(self, start: int, end: int) -> float:
        span = self.covered[start:end]
        return float(span.mean()) if len(span) else 0.0

    # ── writing ──────────────────────────────────────────────────────────
    def put(self, row: int, value: float) -> None:
        """One frame's value — the overlay's side effect, one at a time.

        This is how a tool's series fills by being looked at: the field was
        computed to be drawn, the frame was hot, and the number that falls
        out of it is the same number a sweep would have written.
        """
        if 0 <= row < len(self.values):
            self.values[row] = value
            self.covered[row] = True

    def write_sweep(self, start: int, end: int, reach: int,
                    values) -> tuple[int, int]:
        """A span's worth, with the warm-up rows refused.

        `start`/`end` are the rows the sweep *decoded*; `values` are the
        honest results, which for a tool whose oldest requirement sits
        `reach` back begin at `start + reach`. Sparse offsets do not change
        this — a lag-30 tool cannot answer for row 5 of a span starting at
        0 no matter how few of the intervening frames it holds. Returns the
        rows actually written.
        """
        first = start + max(0, reach)
        values = np.asarray(values, dtype=np.float32)
        if len(values) != end - first:
            raise ValueError(
                f"reach {reach} over rows [{start},{end}) admits "
                f"{end - first} values, got {len(values)}")
        self.values[first:end] = values
        self.covered[first:end] = True
        return first, end

    # ── persistence ──────────────────────────────────────────────────────
    def save(self, root: Path) -> Path:
        root.mkdir(parents=True, exist_ok=True)
        stem = self.key.replace("|", "__").replace("/", "-").replace(":", "-")
        path = root / f"{stem}.npz"
        np.savez_compressed(path, values=self.values, covered=self.covered,
                            pts=self.pts)
        path.with_suffix(".json").write_text(json.dumps({
            "source": self.source, "tool_key": self.tool_key,
            "form_key": self.form_key, "timebase": self.timebase,
            "rows": int(len(self.pts)),
            "covered": int(self.covered.sum()),
        }, indent=1), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path) -> "Series":
        meta = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
        blob = np.load(path)
        return cls(source=meta["source"], tool_key=meta["tool_key"],
                   form_key=meta["form_key"], pts=blob["pts"],
                   timebase=meta["timebase"], values=blob["values"],
                   covered=blob["covered"])


def _runs(mask: np.ndarray, offset: int, want: bool) -> list[tuple[int, int]]:
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
