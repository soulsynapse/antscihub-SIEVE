"""kinematics: dx, dy, speed and heading per record from the id's previous record, per row across a
gap, NaN on a first record, heading in blobs' angle convention; the signal is the row's mean speed."""
import numpy as np
import pytest

from sieve_player.graph import Series
from tests.test_tracks_filter import DTYPE, table
from tools import blobs, kinematics

ROWS = [table([(1, 0, 0, 10), (2, 50, 50, 30)]),
        table([(1, 3, 0, 10), (3, 10, 10, 20)]),                       # 2 is lost a row; 3 appears
        table([(1, 6, 0, 10), (2, 50, 54, 30), (3, 7, 14, 20)])]       # 2 moved 4 px down over two rows


def col(rows, name):
    return [[None if np.isnan(v) else round(float(v), 3) for v in t[name]] for t in rows]


def test_motion_per_row_across_a_gap_nan_on_a_first_record():
    out = kinematics.run(Series(ROWS, "k", 0, 30.0), {})
    rows = out["rows"]
    assert rows[0].dtype.names[-4:] == kinematics.COLUMNS and blobs.plane(rows[0]) == (20, 100)
    assert col(rows, "dx") == [[None, None], [3.0, None], [3.0, 0.0, -3.0]]
    assert col(rows, "dy") == [[None, None], [0.0, None], [0.0, 2.0, 4.0]]
    assert col(rows, "speed") == [[None, None], [3.0, None], [3.0, 2.0, 5.0]]
    assert col(rows, "heading") == [[None, None], [0.0, None], [0.0, 90.0, 126.87]]
    assert out["signal"].tolist() == [0.0, 3.0] + [np.float32(10 / 3)]
    with pytest.raises(ValueError):
        kinematics.kinematics(rows)
