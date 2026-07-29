"""What the written table is worth as a fixture: does it hold what it was given.

`tests/integration/test_cli_detect.py` owns the command and the two absences.
This checks that the numbers survive a write/read round trip. A table that agrees
to six decimal places is a comparison that can never fail.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from sieve.core.filter_base import ElementKind
from sieve.core.pipeline_model import DetectorSettings
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


def _export(name: str, count: np.ndarray, *, start: int, armed: bool) -> DetectionExport:
    return DetectionExport(
        replicate=name,
        node_id="n1",
        filter_id="block_signal",
        fps=20.0,
        start=start,
        update=_update(count, armed=armed),
        settings=DetectorSettings(count_frac=(0.5, 1.0) if armed else None),
    )


def test_every_measured_value_reads_back_bit_identical_and_stays_short(
    tmp_path: Path,
) -> None:
    """Lossless at the array's own precision, and legible — both, not a trade.

    The two halves fail for different reasons and both are load-bearing.
    Round-tripping fails the moment `_measured` becomes an f-string with a
    precision, which is what makes a parity diff silently pass. Shortness
    fails the moment it widens to `float64` before printing, which is the
    obvious implementation and turns a stored `0.1` into
    `0.10000000149011612` across every row of a 2000-frame clip.

    Values chosen as the ones each failure shows up on: a decimal a `float32`
    cannot hold exactly, a long mantissa, a small magnitude, and a fraction
    whose expansion does not terminate.
    """
    count = np.array([0.1, 1234.56789, 1e-7, 1 / 3], dtype=np.float32)
    write_tables(tmp_path, [_export("a", count, start=0, armed=True)], element=ElementKind.BLOCK)

    with (tmp_path / "series.csv").open(encoding="utf-8", newline="") as handle:
        written = [row["blocks_in_band"] for row in csv.DictReader(handle)]
    assert np.array(written, dtype=np.float32).tolist() == count.tolist()
    assert written[0] == "0.1"


def test_an_armed_run_that_found_nothing_still_writes_the_file(tmp_path: Path) -> None:
    """The file's presence carries "a detector ran", not its length.

    The mirror of the disarmed case: an empty `intervals.csv` is the *right*
    answer here, and collapsing the two — writing nothing whenever there are
    no rows — would make "found nothing" and "never looked" the same artifact.
    """
    count = np.zeros(8, dtype=np.float32)
    write_tables(tmp_path, [_export("a", count, start=0, armed=True)], element=ElementKind.BLOCK)

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
            _export("left", count, start=0, armed=True),
            _export("right", count, start=100, armed=True),
        ],
        element=ElementKind.BLOCK,
    )

    with (tmp_path / "series.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["replicate"] for row in rows] == ["left"] * 4 + ["right"] * 4
    assert [int(row["frame"]) for row in rows] == [0, 1, 2, 3, 100, 101, 102, 103]


def test_the_readme_documents_exactly_the_columns_written(tmp_path: Path) -> None:
    """The data dictionary is a rendering of the column list, not prose beside it.

    The failure this replaces a test for: a column added to the header and
    forgotten in the README documented itself as not existing, and nothing
    could see it. Asserting over the *written* header rather than over
    `SERIES_COLUMNS` keeps the check honest — comparing the list to itself
    would pass through any drift at all.
    """
    count = np.arange(4, dtype=np.float32)
    write_tables(tmp_path, [_export("a", count, start=0, armed=True)], element=ElementKind.BLOCK)

    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    for path in ("series.csv", "intervals.csv"):
        with (tmp_path / path).open(encoding="utf-8", newline="") as handle:
            for name in next(csv.reader(handle)):
                assert f"| `{name}` |" in readme, f"{path}: {name} is written and undocumented"
