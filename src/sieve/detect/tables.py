"""A detection written where R can read it, and a person can too.

VISION step 1 asks for the measured thing "as a csv and enough information to
stick it into R". `sieve.detect` already computes it; until this module there
was no way out of the process except stdout, which is a summary and not a
measurement — `docs/todo/parity-comparison-finding.md` wants a count/gate
series a harness compares against forever, and a printed interval count cannot
be that.

**One declaration per column, and the header, the cells, and the data
dictionary are three readings of it.** `Column` carries the name, the clause
`README.md` explains it with, and the function that gets the value; nothing
else names a column anywhere. The list itself is irreducibly hand-written —
no introspection of `DetectorUpdate` can know that its `count` field means
"how many blocks fell inside the value band" — but it is written *once*.

**A column name has to say what the number is, without the code open.** So
`blocks_in_band` rather than `count` (it is a count *of* something, and the
something is the point), `end_frame_exclusive` rather than `end_frame`
(half-open is a convention a reader cannot see and will get wrong by one),
`detected` rather than `gated`. Names are the whole of the documentation a CSV
carries, and `README.md` beside the tables carries the rest — the value band
these counts were taken inside is not derivable from any column, so the file
records the settings the run resolved.

**And the something comes from the pipeline, not from here.** `blocks_in_band`
was a literal in this module until the element declaration existed, which made
it an assumption about the series node written down as a noun: `sieve detect
--node` at a `downsample` node wrote a pixel count under it, no refusal and no
warning, and shipped the invented noun to disk where it outlived the session.
`series_columns` takes the `ElementKind` the graph resolved and names four
columns from it; a node whose elements have no declared meaning never reaches
here, because `cli/detect_cmd.py` refuses it instead. Renaming these to
something shape-neutral was the alternative and is worse than either:
`units_in_band` is honest and unreadable, which is the trade rule 6 exists to
refuse rather than to make.

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
`detect_gate` compares the windowed mean against `count_frac x <element>s_total`,
so the quantity a `DetectorSettings` threshold sits on is a *fraction* while
the series is a *count*. Both divisions are done here, so they are done once
and against the element count the run really had, rather than in every plot.

**Measured numbers print at `float32` precision; derived ones are rounded.**
The two are not the same decision. The in-band count and the windowed mean come
out of `float32` arrays, and the shortest string that round-trips *as float32*
is both exactly lossless and short — `0.1`, not `float64` repr's
`0.10000000149011612`. That keeps the parity fixture bit-exact and legible at
once. Times and fractions are *derived* from columns that are themselves exact
(`frame`, the element total), so a reader can recompute them to any precision and
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
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, TypeVar

import numpy as np

from sieve.core.filter_base import ElementKind
from sieve.core.pipeline_model import DetectorSettings
from sieve.detect.detector import DetectorUpdate

#: What one row is built from — a frame of a series, or one interval.
Source = TypeVar("Source")


@dataclass(frozen=True, slots=True)
class Column(Generic[Source]):
    """A column's name, what it means, and how to get it — declared once.

    The three were three lists before this: a tuple of header strings, a row
    builder repeating them as dict keys, and a hand-written markdown table in
    `README.md` repeating them a third time. Renaming a column meant three
    edits, and *adding* one meant three edits of which only two were checked —
    a column absent from the README documented itself as not existing, and
    nothing could see it, because the README was prose about a tuple rather
    than a rendering of it.

    So the header, every row, and the data dictionary are now three readings
    of this one list, and the failure mode is gone rather than tested for.
    """

    name: str
    #: One clause, for the `README.md` table. Written for somebody who has the
    #: CSV open and not the code.
    meaning: str
    of: Callable[[Source], str]


#: Written where a cell has no value to hold. Not `FALSE`, and not `0`: a
#: disarmed detector has not decided that the frame is quiet, it has not
#: looked. Both R and pandas read this as missing without being told to.
ABSENT = "NA"

#: Decimals on the two derived kinds. Seconds to a millisecond is finer than a
#: frame at any rate SIEVE sees; a fraction to six significant figures is finer
#: than one block in the largest grid anyone has run. Both stay recomputable
#: from `frame` and the element total, which are exact.
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


@dataclass(frozen=True, slots=True)
class Frame:
    """One row of `series.csv`: a replicate's detection, at one offset into it."""

    export: DetectionExport
    #: Index into the series, not a source frame. `frame` adds `export.start`.
    offset: int

    @property
    def elements(self) -> int:
        """How many values the series node emitted per frame.

        What *kind* of value is `series_columns`' argument and not knowable
        from the array; this is only how many there were.
        """
        return self.export.update.band_power.shape[1]

    @property
    def frame(self) -> int:
        return self.export.start + self.offset


@dataclass(frozen=True, slots=True)
class Interval:
    """One row of `intervals.csv`, half-open in frames as the gate holds it."""

    export: DetectionExport
    first: int
    last: int


def series_columns(element: ElementKind) -> tuple[Column[Frame], ...]:
    """`series.csv`'s columns, four of them named for what was counted.

    A function rather than a constant because the noun is the graph's:
    `blocks_total` over a `block_signal` node, `pixels_total` over a
    per-pixel one, and a node that could not say which never gets here. The
    plural is the enum's value plus `s` — `ElementKind` members are chosen to
    read that way, and a table of exceptions would be a second place to
    forget one.

    Args:
        element: What one value of the series node's output is a value of, as
            `pipeline/dag.py`'s `Dag.elements` resolved it.
    """
    unit = f"{element.value}s"
    return (
        Column(
            "replicate",
            "which arena; `baseline` when the project defines none",
            lambda r: r.export.replicate,
        ),
        Column(
            "node_id",
            "the graph node the signal was taken from (a generated id)",
            lambda r: r.export.node_id,
        ),
        Column(
            "filter",
            "that node's filter, for reading and for plot legends",
            lambda r: r.export.filter_id,
        ),
        Column("frame", "absolute source frame", lambda r: str(r.frame)),
        Column(
            "time_seconds",
            "`frame / fps`, to the millisecond",
            lambda r: _seconds(r.frame / r.export.fps),
        ),
        Column(
            f"{unit}_total",
            f"{unit} this frame was divided into",
            lambda r: str(r.elements),
        ),
        Column(
            f"{unit}_in_band",
            "how many of them fell inside the value band",
            lambda r: _measured(r.export.update.count[r.offset]),
        ),
        Column(
            f"{unit}_in_band_fraction",
            f"the same, over `{unit}_total`",
            lambda r: _fraction(r.export.update.count[r.offset], r.elements),
        ),
        Column(
            f"windowed_mean_{unit}",
            f"`{unit}_in_band` averaged over the detection window",
            lambda r: _measured(r.export.update.windowed[r.offset]),
        ),
        Column(
            "windowed_mean_fraction",
            f"the same, over `{unit}_total` — **the count threshold is compared against this**",
            lambda r: _fraction(r.export.update.windowed[r.offset], r.elements),
        ),
        Column(
            "detected",
            "whether the threshold was met; `NA` where the detector is disarmed",
            lambda r: _detected(r),
        ),
    )


INTERVAL_COLUMNS: tuple[Column[Interval], ...] = (
    Column(
        "replicate",
        "which arena; `baseline` when the project defines none",
        lambda r: r.export.replicate,
    ),
    Column(
        "node_id",
        "the graph node the signal was taken from (a generated id)",
        lambda r: r.export.node_id,
    ),
    Column(
        "filter",
        "that node's filter, for reading and for plot legends",
        lambda r: r.export.filter_id,
    ),
    Column("start_frame", "first detected frame, inclusive", lambda r: str(r.first)),
    Column("end_frame_exclusive", "one past the last detected frame", lambda r: str(r.last)),
    Column("start_seconds", "`start_frame` in time", lambda r: _seconds(r.first / r.export.fps)),
    Column(
        "end_seconds", "`end_frame_exclusive` in time", lambda r: _seconds(r.last / r.export.fps)
    ),
    Column(
        "duration_frames", "`end_frame_exclusive - start_frame`", lambda r: str(r.last - r.first)
    ),
    Column(
        "duration_seconds",
        "the same, in time",
        lambda r: _seconds((r.last - r.first) / r.export.fps),
    ),
)


def write_tables(
    directory: Path, exports: Sequence[DetectionExport], *, element: ElementKind
) -> tuple[Path, ...]:
    """Write `series.csv`, `README.md`, and `intervals.csv` when armed.

    Returns the paths actually written, so a caller can report the absent
    intervals file as absent rather than as empty.

    Args:
        directory: Where the three files go.
        exports: One per replicate detected in this run.
        element: What one value of the series node emits is a value of. A
            keyword on the call rather than a field on `DetectionExport`
            because every export in one run is taken over *one* node, so a
            per-export copy could disagree with itself and the writer would
            have to pick — and picking silently is what this argument exists
            to stop.

    Raises:
        TableVerificationError: if a table does not read back as what was
            written. The partial is deleted, never left behind (rule 8).
        OSError: if the directory cannot be made or written.
    """
    directory.mkdir(parents=True, exist_ok=True)
    columns = series_columns(element)
    written = [write_table(directory / "series.csv", columns, _series_rows(exports))]
    # On armed-ness, never on row count. The two collapse for every input a
    # first implementation is tried against and come apart on the one that
    # matters: an armed detector that found nothing owes an empty file, and
    # `if rows:` would delete exactly that answer.
    if any(export.update.intervals is not None for export in exports):
        written.append(
            write_table(directory / "intervals.csv", INTERVAL_COLUMNS, _interval_rows(exports))
        )
    readme = directory / "README.md"
    readme.write_text(_readme(exports, written, columns, element), encoding="utf-8")
    return (*written, readme)


def _series_rows(exports: Sequence[DetectionExport]) -> list[Frame]:
    return [
        Frame(export, offset)
        for export in exports
        for offset in range(int(export.update.count.shape[0]))
    ]


def _interval_rows(exports: Sequence[DetectionExport]) -> list[Interval]:
    """Every armed replicate's intervals, in the order the gate found them.

    An armed replicate that found nothing contributes no rows and is still the
    reason the file exists — which is why the file's presence, not its length,
    is what carries "a detector ran here".
    """
    return [
        Interval(export, first, last)
        for export in exports
        for first, last in export.update.intervals or ()
    ]


def _detected(row: Frame) -> str:
    """`TRUE`/`FALSE` — R's own spelling, which pandas also reads as boolean.

    `NA` for a disarmed detector, which is the whole reason this is a function
    and not `str(bool(...))`: a detector that has not looked has not decided
    the frame is quiet.
    """
    gate = row.export.update.gate
    if gate is None:
        return ABSENT
    return "TRUE" if bool(gate[row.offset]) else "FALSE"


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


def _fraction(value: Any, elements: int) -> str:
    """`value / elements` — the scale `DetectorSettings.count_frac` is stated in.

    Zero elements is `NA`, not zero (rule 6): a frame divided into nothing
    measured nothing, and `0/0` rendered as `0.0` would be a fraction nothing
    computed.
    """
    if elements == 0:
        return ABSENT
    quotient = float(value) / elements
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


def _dictionary(columns: Sequence[Column[Any]]) -> list[str]:
    """The markdown table for `columns` — rendered from them, never beside them."""
    return [
        "| column | meaning |",
        "|---|---|",
        *(f"| `{column.name}` | {column.meaning} |" for column in columns),
        "",
    ]


def _readme(
    exports: Sequence[DetectionExport],
    written: Sequence[Path],
    columns: Sequence[Column[Frame]],
    element: ElementKind,
) -> str:
    """A data dictionary, and the settings the columns cannot carry.

    Generated rather than a static file next to the module: the per-replicate
    resolved settings are the half that is not derivable from the tables, and
    a checked-in document could not hold them.

    `columns` is passed in rather than rebuilt from `element` so that the
    dictionary is a rendering of the list that was actually written, which is
    the property `test_the_readme_documents_exactly_the_columns_written` pins.
    """
    lines = [
        "# What is in this folder",
        "",
        "Written by `sieve detect --csv`. Every row is one replicate's detection over",
        f"one node's per-frame signal, whose values are {element.value}s. Frames are",
        "absolute source frames.",
        "",
        "## series.csv — what was measured, one row per frame",
        "",
        *_dictionary(columns),
    ]
    if any(path.name == "intervals.csv" for path in written):
        lines += [
            "## intervals.csv — what was claimed from it",
            "",
            *_dictionary(INTERVAL_COLUMNS),
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
                else f"{_band(settings.count_frac)} of `{element.value}s_total`"
            ),
            "",
        ]
    return "\n".join(lines)


def write_table(path: Path, columns: Sequence[Column[Source]], rows: Sequence[Source]) -> Path:
    """One verified CSV: write, read back, then rename — `materialize.py`'s order.

    The header and every cell come out of `columns`, in one pass over it, so a
    row cannot be a different width or a different order than the header that
    names it. That was a real defect and not a hypothetical one: rows were
    positional tuples that had to be kept parallel to a separate tuple of
    header strings by hand, and the readback below could not catch a mismatch,
    because it compared a wrong file against the equally wrong rows it had
    been handed.

    The readback is not ceremony either: a CSV whose quoting or line
    terminator is wrong parses as fewer rows or wider ones and is silent about
    it, and this file's whole purpose is to be read by something that is not
    SIEVE.
    """
    cells = [[column.of(row) for column in columns] for row in rows]
    header = [column.name for column in columns]
    part = path.with_name(f"{path.name}.part")
    try:
        with part.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(header)
            writer.writerows(cells)
        _verify(part, header, cells)
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    part.replace(path)
    return path


def _verify(path: Path, header: Sequence[str], cells: Sequence[Sequence[str]]) -> None:
    with path.open("r", encoding="utf-8", newline="") as handle:
        read = list(csv.reader(handle))
    expected = [list(header), *(list(row) for row in cells)]
    if read != expected:
        raise TableVerificationError(
            f"{path.name} read back as {len(read)} rows, not the {len(expected)} written"
        )
