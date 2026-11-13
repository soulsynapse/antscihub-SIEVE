"""size: a method over a size column per row, stepped as run whole; an empty row reads 0."""
import numpy as np

from tests.stepping import hold
from tools import blobs, size


def table(areas):
    t = np.zeros(len(areas), blobs.DTYPE)
    t["area"], t["major"] = areas, np.asarray(areas) * 2
    return t


def test_methods_over_rows_and_an_empty_row():
    rows = np.empty(3, object)
    rows[:] = [table([100, 300, 200]), table([]), table([50])]
    run = lambda field, m: hold(size, rows, {"field": field, "method": m})["signal"].tolist()  # noqa: E731
    assert run("area", "mean") == [200, 0, 50]
    assert run("area", "median") == [200, 0, 50]
    assert run("area", "min") == [100, 0, 50] and run("area", "max") == [300, 0, 50]
    assert run("area", "sum") == [600, 0, 50]
    assert run("major", "mean") == [400, 0, 100]
