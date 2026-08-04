"""`sieve sweep` — decode throughput over core sets and worker counts.

The instrument for `docs/todo/adaptive-worker-allocation.md`. The luma finding
(`docs/findings/2026.07.28-the-luma-path-has-almost-nothing-left-to-thread.md`)
ran this sweep by hand, on one core set, and its protocol is reproduced here so
the two are comparable: sequential reads over a fixed span, a warm-up pass,
repeats, and the median reported per configuration. What is added is the
machine axis — the same measurement under a restricted set of cores, which is
how one machine answers a question about several.

**It changes process affinity and is therefore a command, not a test.** See
`bench/sweep.py`; the isolation a sweep needs is a process of its own.
"""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Annotated

import typer

from sieve.bench.sweep import (
    AffinityUnavailableError,
    Cell,
    Reading,
    class_core_sets,
    curvature,
    design,
    sized_core_sets,
    sweep,
)
from sieve.cli.common import frame_source, refuse
from sieve.decode.reader import VideoDecodeError

#: The luma finding's span, so a reading here can be compared with the readings
#: that produced `LUMA_WORKER_CAP` rather than merely resembling them.
DEFAULT_FIRST_FRAME = 210
DEFAULT_FRAME_COUNT = 150


def sweep_decode(
    video: Annotated[
        Path,
        typer.Argument(exists=True, dir_okay=False, readable=True, help="Footage to read."),
    ],
    workers: Annotated[
        str, typer.Option("--workers", help="Worker counts to try, comma-separated.")
    ] = "1,2,3,4,6,8",
    sizes: Annotated[
        str | None,
        typer.Option(
            "--core-counts",
            help="Also sweep core counts within each class, comma-separated. "
            "Off by default: it multiplies the run time by how many you name.",
        ),
    ] = None,
    first_frame: Annotated[int, typer.Option("--first-frame")] = DEFAULT_FIRST_FRAME,
    frames: Annotated[int, typer.Option("--frames", min=2)] = DEFAULT_FRAME_COUNT,
    repeats: Annotated[int, typer.Option("--repeats", min=1)] = 3,
    luma: Annotated[
        bool,
        typer.Option(
            "--luma/--colour",
            help="Decode the luma plane. The two paths have different optima, "
            "so a sweep must say which it measured.",
        ),
    ] = True,
    as_json: Annotated[bool, typer.Option("--json", help="Emit records instead of a table.")] = (
        False
    ),
) -> None:
    """Measure ms/frame across core sets and worker counts, and report the spread.

    The spread is the point. A core set whose best and worst worker counts are
    within a few percent has no gradient for a controller to act on, and that
    result closes a question rather than opening one.

    Raises:
        typer.Exit: code 1 if the footage cannot be read, or if this platform
            will not pin a process — a sweep that silently ran unpinned would
            report the machine axis as noise under the labels of an experiment.
    """
    try:
        counts = _integers(workers, "--workers")
        core_counts = _integers(sizes, "--core-counts") if sizes else ()
    except ValueError as error:
        raise refuse(str(error)) from error

    core_sets = list(class_core_sets())
    for source in tuple(core_sets):
        core_sets.extend(sized_core_sets(source, core_counts))
    cells = design(core_sets, counts)
    if not cells:
        raise refuse(f"no cell has as many cores as workers; asked for {sorted(set(counts))}")

    span = range(first_frame, first_frame + frames)

    def objective(cell: Cell) -> float:
        with frame_source(video, cell.workers, luma=luma) as reader:
            started = perf_counter()
            for index in span:
                reader.read(index)
            return (perf_counter() - started) * 1000.0 / len(span)

    try:
        readings = sweep(cells, objective, repeats=repeats)
    except AffinityUnavailableError as error:
        raise refuse(str(error)) from error
    except VideoDecodeError as error:
        raise refuse(f"footage could not be read: {error}") from error

    typer.echo(_report(readings, luma=luma, as_json=as_json))


def _integers(raw: str, option: str) -> tuple[int, ...]:
    """A comma-separated list, refused as a whole rather than partially parsed."""
    try:
        values = tuple(int(part) for part in raw.split(",") if part.strip())
    except ValueError as error:
        raise ValueError(f"{option} takes comma-separated integers, got {raw!r}") from error
    if not values or any(value < 1 for value in values):
        raise ValueError(f"{option} takes positive integers, got {raw!r}")
    return values


def _report(readings: tuple[Reading, ...], *, luma: bool, as_json: bool) -> str:
    """The surface, and the one number the controller question turns on.

    Both statistics per cell: `best` is what the configuration can do and
    `typical` is what a session gets, and the gap between them on a core set is
    itself a reading — a wide one means the scheduler moved the work around
    during the measurement, which is the effect the whole sweep exists to see.
    """
    records = [
        {
            "cores": reading.cell.cores.label,
            "cpus": len(reading.cell.cores.cpus),
            "workers": reading.cell.workers,
            "best_ms": round(reading.best, 2),
            "typical_ms": round(reading.typical, 2),
        }
        for reading in readings
    ]
    spread = curvature(readings)
    if as_json:
        path = "luma" if luma else "colour"
        return json.dumps({"path": path, "cells": records, "spread": spread})

    lines = [f"{'cores':<16}{'cpus':>5}{'workers':>9}{'best ms':>10}{'typical':>10}"]
    lines.extend(
        f"{row['cores']:<16}{row['cpus']:>5}{row['workers']:>9}"
        f"{row['best_ms']:>10}{row['typical_ms']:>10}"
        for row in records
    )
    lines.append("")
    lines.append("worst/best across worker counts, per core set:")
    lines.extend(f"  {label:<16}{ratio:.2f}x" for label, ratio in sorted(spread.items()))
    return "\n".join(lines)
