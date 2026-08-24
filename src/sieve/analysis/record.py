"""Computing a step's value where its inputs landed, and filing it.

ADR-0005 implemented, and it is the smallest module in the tree because the
decision it carries is entirely about *when* rather than about what. A step's
value is computed when its inputs are admitted — a frame decoded into a form
that may be recorded — and never on the cadence of anything that draws.

**What this refuses is the display as a data source**, and the reason is worth
having here rather than only in the ADR, because the wrong version is the
appealing one. A tool's field has to be recomputed in order to be drawn; the
frame it is drawn from was already decoded; the number that falls out is the
same number a background pass would write later at full price. Every clause of
that is true and the conclusion does not follow. What a renderer selects depends
on what the machine had time to draw — on paint cost, on compositor cadence, on
window size — so a value filed by the drawing would make *which rows exist*
depend on how busy the machine was. A fill is machine-dependent too and that is
fine: it varies in when rows are produced, not in which.

**The test that separates them:** would the set of recorded values differ on a
slower machine? For this producer it would not. Coverage may lag; coverage may
not be chosen by rendering.

**The step is read once.** `admitted` takes the tools it is to evaluate as an
argument rather than reaching for a mutable "current step" — and that is not
fussiness, it is the defect this tree actually shipped. A producer that reads
the active step to decide which inputs to gather and reads it *again* to decide
where to file the answer will, when the step changes between the two, write a
value computed with one step under the key of another. Both numbers are
plausible, both keys are real, and no instrument that measures time can see it
(`experiments/tool-experiments/05-provenance.py`).

**A value is written only where every declared input is resident**, in the form
the step asked for. A step whose inputs are half there has no honest value, and
a producer that substituted a near-enough frame would be filing a value under a
key that does not describe what it was computed from.
"""

from __future__ import annotations

import threading
from pathlib import Path

import numpy as np

from sieve.analysis.series import Series
from sieve.analysis.tool import Tool
from sieve.frame.form import Form
from sieve.frame.table import FrameTable


class Recorder:
    """The series a session is filling, and the one place values are written."""

    def __init__(self, source: str, table: FrameTable, root: Path | None = None):
        self.source = source
        self.table = table
        self.root = root
        self._series: dict[str, Series] = {}
        self._lock = threading.RLock()
        self.written = 0
        #: rows whose inputs were resident and whose value was already stored.
        #: Counted rather than silently skipped: recomputing something already
        #: filed under its key is one of the things ADR-0008 calls waste, and a
        #: producer that could not tell the difference could not report it.
        self.already = 0

    # ── the series ───────────────────────────────────────────────────────
    def series_for(self, tool: Tool, form: Form) -> Series:
        """The series this step's values go in, made once and kept.

        Keyed by the step *and* the form, because those are the two things the
        values depend on: the same arithmetic over a different picture is a
        different answer, and a store that folded them together would hand back
        numbers about the wrong crop under a name that looked right.
        """
        key = f"{tool.key()}|{form.key()}"
        with self._lock:
            found = self._series.get(key)
            if found is None:
                found = self._series[key] = Series(
                    source=self.source,
                    tool_key=tool.key(),
                    form_key=form.key(),
                    pts=self.table.pts,
                    timebase=self.table.timebase_str,
                )
            return found

    def series(self) -> dict[str, Series]:
        with self._lock:
            return dict(self._series)

    def tools_by_key(self, active: list[tuple[Tool, Form]]) -> dict[str, Tool]:
        """What answers to each series key, for anything checking provenance."""
        return {f"{tool.key()}|{form.key()}": tool for tool, form in active}

    # ── writing ──────────────────────────────────────────────────────────
    def admitted(self, active: list[tuple[Tool, Form]], row: int,
                 resident) -> int:
        """A row landed. Record whatever can now honestly be computed.

        `active` is handed in and read once. Reaching for a session's current
        step here — once to gather and once to file — is exactly the defect
        that survived four cost experiments, because a value filed by the wrong
        producer costs what the right one costs.

        Returns how many values were written, which is a number and not a
        promise: a step whose inputs are not all resident writes nothing, and
        that is coverage lagging rather than a failure.
        """
        written = 0
        for tool, form in active:
            series = self.series_for(tool, form)
            for position in self._positions_ready(tool, form, row, resident,
                                                  len(series.values)):
                if series.get(position) is not None:
                    self.already += 1
                    continue
                frames = {need: resident.get(form.key(), need)
                          for need in tool.needs(position)}
                if any(frame is None for frame in frames.values()):
                    continue
                value = tool.reduce(tool.field(frames, position))
                series.put(position, float(value))
                written += 1
        self.written += written
        return written

    @staticmethod
    def _positions_ready(tool: Tool, form: Form, row: int, resident,
                         rows: int):
        """Which positions this admission may have completed.

        A frame is an input to more than one position: a step admitting
        `(-1, 0)` uses row *r* to compute *r* and *r+1*. So admitting a row
        offers every position that names it, which is what makes a sequential
        fill produce a contiguous series rather than every other value.
        """
        for offset in tool.offsets:
            position = row - offset
            if 0 <= position < rows:
                yield position

    # ── keeping it ───────────────────────────────────────────────────────
    def save(self) -> list[Path]:
        """Write every series, if this recorder was given somewhere to write.

        Returns what it wrote. A recorder with no root holds its series in
        memory, which is what a check wants and what a session that has not
        been told where its project is has to do.
        """
        if self.root is None:
            return []
        return [series.save(self.root) for series in self.series().values()]

    def load(self) -> int:
        """Read back whatever is already written. Returns how many series."""
        if self.root is None or not self.root.is_dir():
            return 0
        found = 0
        for path in sorted(self.root.glob("*.npz")):
            try:
                series = Series.load(path)
            except (OSError, KeyError, ValueError):
                continue
            if series.source != self.source:
                continue
            if len(series.pts) != len(self.table.pts) or \
                    not np.array_equal(series.pts, self.table.pts):
                # a series about different footage, or about this footage as
                # some other pass counted it. Its rows do not mean what this
                # table says they mean, and adopting it would file future
                # values beside numbers about other frames.
                continue
            with self._lock:
                self._series[f"{series.tool_key}|{series.form_key}"] = series
            found += 1
        return found
