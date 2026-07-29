"""A detection written where R can read it, and a person can too.

VISION step 1 asks for the measured thing "as a csv and enough information to
stick it into R". `sieve.detect` already computes it; until this module there
was no way out of the process except stdout, which is a summary and not a
measurement — `docs/todo/parity-comparison-finding.md` wants a count/gate
series a harness compares against forever, and a printed interval count cannot
be that.

**A column name has to say what the number is, without the code open.** So
`blocks_in_band` rather than `count` (it is a count *of* something, and the
something is the point), `end_frame_exclusive` rather than `end_frame`
(half-open is a convention a reader cannot see and will get wrong by one),
`detected` rather than `gated`. Names are the whole of the documentation a CSV
carries, and `README.md` beside the tables carries the rest — the value band
these counts were taken inside is not derivable from any column, so the file
records the settings the run resolved.

**Two files, because they are two claims with different lifetimes.** The
series is what the transform and the gate *measured*; the intervals are what
the current `DetectorSettings` *claims* from it. A re-tune moves the second
and leaves the first alone, and one wide table would make a threshold change
look like a new measurement. Both carry `replicate` and `node_id`, so a batch
is one file per kind rather than one directory per arena — R wants long form.

**Disarmed writes no intervals file at all** (rule 6). A header-only
`intervals.csv` reads as "armed, found nothing", which is the one wrong answer
that looks like a right one; `detected` in the series goes to `NA` for the
same reason, and `NA` is a value both R and pandas already read as absent. A
project with no detector never reaches here — the counts are taken inside the
value band, so there is no series either, and the caller refuses.

**`windowed_mean_fraction` is the column the threshold is drawn on.**
`detect_gate` compares the windowed mean against `count_frac x blocks_total`,
so the quantity a `DetectorSettings` threshold sits on is a *fraction* while
the series is a *count*. Both divisions are done here, so they are done once
and against the block count the run really had, rather than in every plot.

**Measured numbers print at `float32` precision; derived ones are rounded.**
The two are not the same decision. `blocks_in_band` and the windowed mean come
out of `float32` arrays, and the shortest string that round-trips *as float32*
is both exactly lossless and short — `0.1`, not `float64` repr's
`0.10000000149011612`. That keeps the parity fixture bit-exact and legible at
once. Times and fractions are *derived* from columns that are themselves exact
(`frame`, `blocks_total`), so a reader can recompute them to any precision and
rounding them loses nothing; they are rounded because six ugly digits of a
convenience column is what makes a table unreadable.

**Non-finite values are spelled `Inf`, `-Inf`, `NaN`** — R's spellings, which
pandas also parses. Not `NA`: a value that overflowed is not a value that was
never taken, and collapsing them is rule 6 in the direction nobody checks.

**No `settled` column.** A whole-clip pass is final by construction
(`detector.settled_for(..., final=True)`), so the column would be constant
`TRUE` — and a column that can only take one value invites the reader to
believe it varies. When a partial record is ever exported, that is the change
that earns the column.
"""

from __future__ import annotations

import csv
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeAlias

import numpy as np

from sieve.core.pipeline_model import DetectorSettings
from sieve.detect.detector import DetectorUpdate

#: One row, keyed by column name. Never a positional tuple — see `_write`.
Row: TypeAlias = Mapping[str, str]

SERIES_COLUMNS = (
    "replicate",
    "node_id",
    "filter",
    "frame",
    "time_seconds",
    "blocks_total",
    "blocks_in_band",
    "blocks_in_band_fraction",
    "windowed_mean_blocks",
    "windowed_mean_fraction",
    "detected",
)
INTERVAL_COLUMNS = (
    "replicate",
    "node_id",
    "filter",
    "start_frame",
    "end_frame_exclusive",
    "start_seconds",
    "end_seconds",
    "duration_frames",
    "duration_seconds",
)

#: Written where a cell has no value to hold. Not `FALSE`, and not `0`: a
#: disarmed detector has not decided that the frame is quiet, it has not
#: looked. Both R and pandas read this as missing without being told to.
ABSENT = "NA"

#: Decimals on the two derived kinds. Seconds to a millisecond is finer than a
#: frame at any rate SIEVE sees; a fraction to six significant figures is finer
#: than one block in the largest grid anyone has run. Both stay recomputable
#: from `frame` and `blocks_total`, which are exact.
SECONDS_DECIMALS = 3
FRACTION_FIGURES = 6


class TableVerificationError(RuntimeError):
    """The written table did not read back as the rows that were handed to it."""


@dataclass(frozen=True, slots=True)
class DetectionExport:
    """One replicate's detection, and what is needed to say where it came from."""

    replicate: str
    #: Which node's output the series was taken over. It changes *what the
    #: measurement is*, so it is a column and not a filename.
    node_id: str
    #: The node's filter, beside its id. Redundant and deliberately so: the id
    #: is the correct key and a generated hash, unreadable and not stable
    #: across a rebuild of the node. `block_signal` is what a legend wants.
    filter_id: str
    fps: float
    #: The series' first source frame, so `frame` is absolute.
    start: int
    update: DetectorUpdate
    #: The settings this replicate resolved to, for `README.md`. The value band
    #: is not recoverable from any column, so without it "in band" names a set
    #: the file cannot describe.
    settings: DetectorSettings


def write_tables(directory: Path, exports: Sequence[DetectionExport]) -> tuple[Path, ...]:
    """Write `series.csv`, `README.md`, and `intervals.csv` when armed.

    Returns the paths actually written, so a caller can report the absent
    intervals file as absent rather than as empty.

    Raises:
        TableVerificationError: if a table does not read back as what was
            written. The partial is deleted, never left behind (rule 8).
        OSError: if the directory cannot be made or written.
    """
    directory.mkdir(parents=True, exist_ok=True)
    written = [write_table(directory / "series.csv", SERIES_COLUMNS, _series_rows(exports))]
    # On armed-ness, never on row count. The two collapse for every input a
    # first implementation is tried against and come apart on the one that
    # matters: an armed detector that found nothing owes an empty file, and
    # `if rows:` would delete exactly that answer.
    if any(export.update.intervals is not None for export in exports):
        written.append(
            write_table(directory / "intervals.csv", INTERVAL_COLUMNS, _interval_rows(exports))
        )
    readme = directory / "README.md"
    readme.write_text(_readme(exports, written), encoding="utf-8")
    return (*written, readme)


def _series_rows(exports: Sequence[DetectionExport]) -> list[Row]:
    rows: list[Row] = []
    for export in exports:
        update = export.update
        blocks = update.band_power.shape[1]
        gate = update.gate
        for offset in range(int(update.count.shape[0])):
            frame = export.start + offset
            rows.append(
                {
                    "replicate": export.replicate,
                    "node_id": export.node_id,
                    "filter": export.filter_id,
                    "frame": str(frame),
                    "time_seconds": _seconds(frame / export.fps),
                    "blocks_total": str(blocks),
                    "blocks_in_band": _measured(update.count[offset]),
                    "blocks_in_band_fraction": _fraction(update.count[offset], blocks),
                    "windowed_mean_blocks": _measured(update.windowed[offset]),
                    "windowed_mean_fraction": _fraction(update.windowed[offset], blocks),
                    "detected": ABSENT if gate is None else _boolean(bool(gate[offset])),
                }
            )
    return rows


def _interval_rows(exports: Sequence[DetectionExport]) -> list[Row]:
    """Every armed replicate's intervals, half-open in frames as they are held.

    An armed replicate that found nothing contributes no rows and is still the
    reason the file exists — which is why the file's presence, not its length,
    is what carries "a detector ran here".
    """
    rows: list[Row] = []
    for export in exports:
        for first, last in export.update.intervals or ():
            rows.append(
                {
                    "replicate": export.replicate,
                    "node_id": export.node_id,
                    "filter": export.filter_id,
                    "start_frame": str(first),
                    "end_frame_exclusive": str(last),
                    "start_seconds": _seconds(first / export.fps),
                    "end_seconds": _seconds(last / export.fps),
                    "duration_frames": str(last - first),
                    "duration_seconds": _seconds((last - first) / export.fps),
                }
            )
    return rows


def _boolean(value: bool) -> str:
    """`TRUE`/`FALSE` — R's own spelling, which pandas also reads as boolean."""
    return "TRUE" if value else "FALSE"


def _measured(value: Any) -> str:
    """A `float32` array element, at the shortest length that round-trips it.

    `unique=True` asks numpy for exactly the digits needed to recover the same
    `float32`, which for a value that came from a whole number is the whole
    number. Widening to `float64` first and calling `repr` — the obvious
    implementation — prints `0.10000000149011612` for a stored `0.1` and is
    no more faithful, because the extra digits describe the widening.
    """
    scalar = np.float32(value)
    if not math.isfinite(float(scalar)):
        return _nonfinite(float(scalar))
    return str(np.format_float_positional(scalar, unique=True, trim="0"))


def _fraction(value: Any, blocks: int) -> str:
    """`value / blocks` — the scale `DetectorSettings.count_frac` is stated in.

    Zero blocks is `NA`, not zero (rule 6): a grid with no blocks measured
    nothing, and `0/0` rendered as `0.0` would be a fraction nothing computed.
    """
    if blocks == 0:
        return ABSENT
    quotient = float(value) / blocks
    if not math.isfinite(quotient):
        return _nonfinite(quotient)
    return f"{quotient:.{FRACTION_FIGURES}g}"


def _seconds(value: float) -> str:
    if not math.isfinite(value):
        return _nonfinite(value)
    return f"{value:.{SECONDS_DECIMALS}f}"


def _nonfinite(value: float) -> str:
    if math.isnan(value):
        return "NaN"
    return "Inf" if value > 0 else "-Inf"


def _band(bounds: tuple[float, float]) -> str:
    """A `[lo, hi]` band in prose, with an open end said rather than printed.

    `%g` renders an unbounded edge as the literal `inf`, and "386383 to inf"
    reads as a number that failed to format. An open band is a real and common
    tuning — most of these bands are one-sided — so it gets words.
    """
    lo, hi = bounds
    if math.isinf(lo) and math.isinf(hi):
        return "unbounded"
    if math.isinf(hi):
        return f"{lo:g} and above"
    if math.isinf(lo):
        return f"{hi:g} and below"
    return f"{lo:g} to {hi:g}"


def _readme(exports: Sequence[DetectionExport], written: Sequence[Path]) -> str:
    """A data dictionary, and the settings the columns cannot carry.

    Generated rather than a static file next to the module: the per-replicate
    resolved settings are the half that is not derivable from the tables, and
    a checked-in document could not hold them.
    """
    lines = [
        "# What is in this folder",
        "",
        "Written by `sieve detect --csv`. Every row is one replicate's detection over",
        "one node's per-frame signal. Frames are absolute source frames.",
        "",
        "## series.csv — what was measured, one row per frame",
        "",
        "| column | meaning |",
        "|---|---|",
        "| `replicate` | which arena; `baseline` when the project defines none |",
        "| `node_id` | the graph node the signal was taken from (a generated id) |",
        "| `filter` | that node's filter, for reading and for plot legends |",
        "| `frame` | absolute source frame |",
        "| `time_seconds` | `frame / fps`, to the millisecond |",
        "| `blocks_total` | blocks in the grid this frame was divided into |",
        "| `blocks_in_band` | how many of them fell inside the value band |",
        "| `blocks_in_band_fraction` | the same, over `blocks_total` |",
        "| `windowed_mean_blocks` | `blocks_in_band` averaged over the detection window |",
        "| `windowed_mean_fraction` | the same, over `blocks_total` — **the count "
        "threshold is compared against this** |",
        "| `detected` | whether the threshold was met; `NA` where the detector is disarmed |",
        "",
    ]
    if any(path.name == "intervals.csv" for path in written):
        lines += [
            "## intervals.csv — what was claimed from it",
            "",
            "| column | meaning |",
            "|---|---|",
            "| `start_frame` | first detected frame, inclusive |",
            "| `end_frame_exclusive` | one past the last detected frame |",
            "| `start_seconds`, `end_seconds` | the same bounds in time |",
            "| `duration_frames`, `duration_seconds` | `end - start` |",
            "",
            "A present-but-empty `intervals.csv` means a detector ran and claimed nothing.",
            "An absent one means no replicate was armed — the two are not the same, and",
            "that is why the file is missing rather than empty.",
            "",
        ]
    else:
        lines += [
            "There is no `intervals.csv`: no replicate had a count threshold placed, so",
            "nothing was claimed. An empty file would have read as 'found nothing'.",
            "",
        ]
    lines += ["## The settings these numbers were taken under", ""]
    for export in exports:
        settings = export.settings
        lines += [
            f"### {export.replicate}",
            "",
            f"- signal node: `{export.node_id}` (`{export.filter_id}`), {export.fps:g} fps",
            f"- frequency band: {_band(settings.freq_band)} Hz",
            f"- value band: {_band(settings.value_band)}",
            f"- detection window: {settings.window_frames} frames, "
            f"{'centered' if settings.centered else 'trailing'}",
            "- count threshold: "
            + (
                "not placed — the detector is disarmed"
                if settings.count_frac is None
                else f"{_band(settings.count_frac)} of `blocks_total`"
            ),
            "",
        ]
    return "\n".join(lines)


def write_table(path: Path, columns: Sequence[str], rows: Sequence[Row]) -> Path:
    """One verified CSV: write, read back, then rename — the `pipeline/materialize.py` order.

    Rows are keyed by column name, never ordered by position, and `columns` is
    the contract both sides are held to. A positional tuple is the obvious
    implementation and has no defence at all against a column added to the
    header and not to the builder: the file would come out one cell short of
    its header on every row, and the readback below could not see it, because
    it would be comparing a wrong file against the equally wrong rows it was
    handed. `DictWriter` raising on an unknown key is half of that defence;
    `_check_keys` is the other half, since a *missing* key writes an empty
    cell rather than raising.

    The readback is not ceremony either: a CSV whose quoting or line
    terminator is wrong parses as fewer rows or wider ones and is silent about
    it, and this file's whole purpose is to be read by something that is not
    SIEVE.
    """
    _check_keys(path, columns, rows)
    part = path.with_name(f"{path.name}.part")
    try:
        with part.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=list(columns), lineterminator="\n", extrasaction="raise"
            )
            writer.writeheader()
            writer.writerows(rows)
        _verify(part, columns, rows)
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    part.replace(path)
    return path


def _check_keys(path: Path, columns: Sequence[str], rows: Sequence[Row]) -> None:
    """Every row fills every column, or nothing is written.

    Raises:
        TableVerificationError: naming the columns that went unfilled.
    """
    expected = set(columns)
    for row in rows:
        missing = expected - row.keys()
        if missing:
            raise TableVerificationError(
                f"{path.name}: no value for {', '.join(sorted(missing))} — a column was "
                "declared and never built"
            )


def _verify(path: Path, columns: Sequence[str], rows: Sequence[Row]) -> None:
    with path.open("r", encoding="utf-8", newline="") as handle:
        read = list(csv.DictReader(handle))
    expected = [{column: row[column] for column in columns} for row in rows]
    if [dict(row) for row in read] != expected:
        raise TableVerificationError(
            f"{path.name} read back as {len(read)} rows, not the {len(expected)} written"
        )
