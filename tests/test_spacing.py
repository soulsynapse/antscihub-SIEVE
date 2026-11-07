"""spacing: nearest-other distance per row by mean, median or min, or pairs within r; under two blobs reads 0."""
import numpy as np
import pytest

from sieve_player.graph import Series
from tools import blobs, spacing


def table(points):
    t = np.zeros(len(points), blobs.DTYPE)
    t["cx"], t["cy"] = zip(*points) if points else ((), ())
    return t


ROWS = [table([(0, 0), (3, 4), (3, 0), (100, 100)]), table([(0, 0)]), table([])]   # nearest: 3, 4, 3, 96.05


def test_each_method_and_the_rows_under_two():
    s = lambda m, r=0.0: spacing.run(Series(ROWS, "k", 0, 30.0), {"method": m, "r": r})["signal"].tolist()
    assert s("min") == [3.0, 0.0, 0.0] and s("median") == [3.5, 0.0, 0.0]
    assert s("mean") == pytest.approx([(3 + 4 + 3 + np.hypot(97, 96)) / 4, 0.0, 0.0])
    assert s("pairs", 5.0) == [3.0, 0.0, 0.0] and s("pairs", 4.5) == [2.0, 0.0, 0.0] and s("pairs", 200) == [6.0, 0.0, 0.0]
    with pytest.raises(ValueError):
        spacing.spacing(ROWS[0], "sum")
