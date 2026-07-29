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


Source = TypeVar("Source")


@dataclass(frozen=True, slots=True)
class Column(Generic[Source]):
    name: str

    meaning: str
    of: Callable[[Source], str]


ABSENT = "NA"


SECONDS_DECIMALS = 3
FRACTION_FIGURES = 6


class TableVerificationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DetectionExport:
    replicate: str

    node_id: str

    filter_id: str
    fps: float

    start: int
    update: DetectorUpdate

    settings: DetectorSettings


@dataclass(frozen=True, slots=True)
class Frame:
    export: DetectionExport

    offset: int

    @property
    def elements(self) -> int:
        return self.export.update.band_power.shape[1]

    @property
    def frame(self) -> int:
        return self.export.start + self.offset


@dataclass(frozen=True, slots=True)
class Interval:
    export: DetectionExport
    first: int
    last: int


def series_columns(element: ElementKind) -> tuple[Column[Frame], ...]:
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
    Column(
        "end_frame_exclusive", "one past the last detected frame", lambda r: str(r.last)
    ),
    Column(
        "start_seconds",
        "`start_frame` in time",
        lambda r: _seconds(r.first / r.export.fps),
    ),
    Column(
        "end_seconds",
        "`end_frame_exclusive` in time",
        lambda r: _seconds(r.last / r.export.fps),
    ),
    Column(
        "duration_frames",
        "`end_frame_exclusive - start_frame`",
        lambda r: str(r.last - r.first),
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
    directory.mkdir(parents=True, exist_ok=True)
    columns = series_columns(element)
    written = [write_table(directory / "series.csv", columns, _series_rows(exports))]
    if any(export.update.intervals is not None for export in exports):
        written.append(
            write_table(
                directory / "intervals.csv", INTERVAL_COLUMNS, _interval_rows(exports)
            )
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
    return [
        Interval(export, first, last)
        for export in exports
        for first, last in export.update.intervals or ()
    ]


def _detected(row: Frame) -> str:
    gate = row.export.update.gate
    if gate is None:
        return ABSENT
    return "TRUE" if bool(gate[row.offset]) else "FALSE"


def _measured(value: Any) -> str:
    scalar = np.float32(value)
    if not math.isfinite(float(scalar)):
        return _nonfinite(float(scalar))
    return str(np.format_float_positional(scalar, unique=True, trim="0"))


def _fraction(value: Any, elements: int) -> str:
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
    lo, hi = bounds
    if math.isinf(lo) and math.isinf(hi):
        return "unbounded"
    if math.isinf(hi):
        return f"{lo:g} and above"
    if math.isinf(lo):
        return f"{hi:g} and below"
    return f"{lo:g} to {hi:g}"


def _dictionary(columns: Sequence[Column[Any]]) -> list[str]:
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


def write_table(
    path: Path, columns: Sequence[Column[Source]], rows: Sequence[Source]
) -> Path:
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
