"""A detection written where R can read it, and the two claims kept apart.

VISION step 1 asks for the measured thing "as a csv and enough information to
stick it into R". `sieve.detect` already computes it; until this module there
was no way out of the process except stdout, which is a summary and not a
measurement — `docs/todo/parity-comparison-finding.md` wants a count/gate
series a harness compares against forever, and a printed interval count cannot
be that.

**Two files, because they are two claims with different lifetimes.** The
series is what the transform and the gate *measured*; the intervals are what
the current `DetectorSettings` *claims* from it. A re-tune moves the second
and leaves the first alone, and one wide table would make a threshold change
look like a new measurement. Both carry `replicate` and `node`, so a batch is
one file per kind rather than one directory per arena — R wants the long form.

**Disarmed writes no intervals file at all** (rule 6). A header-only
`intervals.csv` reads as "armed, found nothing", which is the one wrong answer
that looks like a right one; `gated` in the series goes to `NA` for the same
reason, and `NA` is a value both R and pandas already read as absent. A
project with no detector never reaches here — `count` and `windowed` are
derived through `value_band`, so there is no series either, and the caller
refuses.

**Floats are written as `repr`, not formatted.** These tables are a fixture
later runs are diffed against; a `%.6f` that silently agrees to six places is
a comparison that cannot fail. `repr` round-trips, and `float32` widens to
`float64` exactly, so the file holds what the array held.

**No `settled` column.** A whole-clip pass is final by construction
(`detector.settled_for(..., final=True)`), so the column would be constant
`TRUE` — and a column that can only take one value invites the reader to
believe it varies. When a partial record is ever exported, that is the change
that earns the column.
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sieve.detect.detector import DetectorUpdate

SERIES_COLUMNS = ("replicate", "node", "frame", "t_s", "count", "windowed", "blocks", "gated")
INTERVAL_COLUMNS = ("replicate", "node", "start_frame", "end_frame", "start_s", "end_s")

#: Written for a `gated` cell whose gate is `None`. Not `FALSE`: a disarmed
#: detector has not decided that the frame is quiet, it has not looked.
ABSENT = "NA"


class TableVerificationError(RuntimeError):
    """The written table did not read back as the rows that were handed to it."""


@dataclass(frozen=True, slots=True)
class DetectionExport:
    """One replicate's detection, and the three facts that place it in time.

    `update` is required and never `None`: a project with no detector has no
    series either, since `count` comes out of `inband_count` over the value
    band. The caller refuses that case rather than exporting an empty one.
    """

    replicate: str
    #: Which node's output the series was taken over. It changes *what the
    #: measurement is*, so it is a column and not a filename.
    node: str
    fps: float
    #: The series' first source frame, so `frame` is absolute.
    start: int
    update: DetectorUpdate


def write_tables(directory: Path, exports: Sequence[DetectionExport]) -> tuple[Path, ...]:
    """Write `series.csv`, and `intervals.csv` when anything is armed.

    Returns the paths actually written, in that order, so a caller can report
    the absent second file as absent rather than as empty.

    Raises:
        TableVerificationError: if a file does not read back as what was
            written. The partial is deleted, never left behind (rule 8).
        OSError: if the directory cannot be made or written.
    """
    directory.mkdir(parents=True, exist_ok=True)
    written = [_write(directory / "series.csv", SERIES_COLUMNS, _series_rows(exports))]
    # On armed-ness, never on row count. The two collapse for every input a
    # first implementation is tried against and come apart on the one that
    # matters: an armed detector that found nothing owes an empty file, and
    # `if rows:` would delete exactly that answer.
    if any(export.update.intervals is not None for export in exports):
        written.append(
            _write(directory / "intervals.csv", INTERVAL_COLUMNS, _interval_rows(exports))
        )
    return tuple(written)


def _series_rows(exports: Sequence[DetectionExport]) -> list[tuple[str, ...]]:
    rows: list[tuple[str, ...]] = []
    for export in exports:
        update = export.update
        blocks = str(update.band_power.shape[1])
        gate = update.gate
        for offset in range(int(update.count.shape[0])):
            frame = export.start + offset
            gated = ABSENT if gate is None else _boolean(bool(gate[offset]))
            rows.append(
                (
                    export.replicate,
                    export.node,
                    str(frame),
                    _number(frame / export.fps),
                    _number(update.count[offset]),
                    _number(update.windowed[offset]),
                    blocks,
                    gated,
                )
            )
    return rows


def _interval_rows(exports: Sequence[DetectionExport]) -> list[tuple[str, ...]]:
    """Every armed replicate's intervals, half-open in frames as they are held.

    An armed replicate that found nothing contributes no rows and is still the
    reason the file exists — which is why the file's presence, not its length,
    is what carries "a detector ran here".
    """
    rows: list[tuple[str, ...]] = []
    for export in exports:
        for first, last in export.update.intervals or ():
            rows.append(
                (
                    export.replicate,
                    export.node,
                    str(first),
                    str(last),
                    _number(first / export.fps),
                    _number(last / export.fps),
                )
            )
    return rows


def _boolean(value: bool) -> str:
    """`TRUE`/`FALSE` — R's own spelling, which pandas also reads as boolean."""
    return "TRUE" if value else "FALSE"


def _number(value: Any) -> str:
    return repr(float(value))


def _write(path: Path, header: Sequence[str], rows: Sequence[Sequence[str]]) -> Path:
    """Write, read back, then rename — the `pipeline/materialize.py` order.

    The readback is not ceremony: a CSV whose quoting or line terminator is
    wrong parses as fewer rows or wider ones and is silent about it, and this
    file's whole purpose is to be read by something that is not SIEVE.
    """
    part = path.with_name(f"{path.name}.part")
    try:
        with part.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(header)
            writer.writerows(rows)
        _verify(part, header, rows)
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    part.replace(path)
    return path


def _verify(path: Path, header: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
    with path.open("r", encoding="utf-8", newline="") as handle:
        read = list(csv.reader(handle))
    expected = [list(header), *(list(row) for row in rows)]
    if read != expected:
        raise TableVerificationError(
            f"{path.name} read back as {len(read)} rows, not the {len(expected)} written"
        )
