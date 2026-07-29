"""What the written table is worth as a fixture: does it hold what it was given.

`tests/integration/test_cli_detect.py` owns the command and the two absences.
This owns the one property that makes the file usable for the comparison
`docs/todo/parity-comparison-finding.md` wants — a run diffed against a
recorded one — which is that the numbers survive the trip. A table that agrees
to six decimal places is a comparison that can never fail.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from sieve.detect.detector import DetectorUpdate
from sieve.detect.tables import DetectionExport, write_tables


def _update(count: np.ndarray, *, armed: bool) -> DetectorUpdate:
    frames = count.shape[0]
    gate = np.zeros(frames, dtype=np.bool_) if armed else None
    return DetectorUpdate(
        band_power=np.zeros((frames, 4), dtype=np.float32),
        count=count.astype(np.float32),
        windowed=count.astype(np.float32),
        gate=gate,
        intervals=() if armed else None,
        band_rows=(0, 4),
    )


def test_every_written_value_reads_back_bit_identical(tmp_path: Path) -> None:
    """`float32` widened to `float64` and printed must parse back to itself.

    Values chosen to be the ones a fixed-width format loses: a long mantissa,
    a subnormal-adjacent small, and a value whose decimal expansion does not
    terminate. Fails the moment `_number` becomes an f-string with a precision.
    """
    count = np.array([0.1, 1234.56789, 1e-7, 1 / 3], dtype=np.float32)
    write_tables(tmp_path, [DetectionExport("a", "blocks", 20.0, 0, _update(count, armed=True))])

    with (tmp_path / "series.csv").open(encoding="utf-8", newline="") as handle:
        read = [float(row["count"]) for row in csv.DictReader(handle)]
    assert read == [float(value) for value in count]


def test_an_armed_run_that_found_nothing_still_writes_the_file(tmp_path: Path) -> None:
    """The file's presence carries "a detector ran", not its length.

    The mirror of the disarmed case: an empty `intervals.csv` is the *right*
    answer here, and collapsing the two — writing nothing whenever there are
    no rows — would make "found nothing" and "never looked" the same artifact.
    """
    count = np.zeros(8, dtype=np.float32)
    write_tables(tmp_path, [DetectionExport("a", "blocks", 20.0, 0, _update(count, armed=True))])

    with (tmp_path / "intervals.csv").open(encoding="utf-8", newline="") as handle:
        assert list(csv.DictReader(handle)) == []


def test_replicates_share_one_file_in_long_form(tmp_path: Path) -> None:
    """One table per kind, keyed by `replicate` — the shape R groups by.

    A directory per arena is the plausible alternative and is what forces the
    R side to glob and bind before it can do anything.
    """
    count = np.arange(4, dtype=np.float32)
    write_tables(
        tmp_path,
        [
            DetectionExport("left", "blocks", 20.0, 0, _update(count, armed=True)),
            DetectionExport("right", "blocks", 20.0, 100, _update(count, armed=True)),
        ],
    )

    with (tmp_path / "series.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["replicate"] for row in rows] == ["left"] * 4 + ["right"] * 4
    assert [int(row["frame"]) for row in rows] == [0, 1, 2, 3, 100, 101, 102, 103]
