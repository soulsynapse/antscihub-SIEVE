"""filter: records whose field, a column or a ratio, lies in [lo, hi]; a blank bound is none and NaN never passes."""
import numpy as np

from tools import blobs, filter


def table(**cols):
    t = np.zeros(len(next(iter(cols.values()))), blobs.DTYPE)
    for k, v in cols.items():
        t[k] = v
    return t


def test_bounds_on_a_column_and_on_the_ratios():
    t = table(area=[100, 400, 900], core=[10, 300, -1], major=[20, 10, 10], minor=[5, 10, 0])
    run = lambda field, lo, hi: filter.run(lambda r: t, 0, {"field": field, "lo": lo, "hi": hi})["area"].tolist()  # noqa: E731
    assert run("area", "200", "") == [400, 900] and run("area", "", " 400 ") == [100, 400]
    assert run("core_ratio", "0.5", "") == [400]                 # 0.1, 0.75, NaN: the one without a diff never passes
    assert run("aspect", "2", "") == [100]                       # 4, 1, NaN on a zero minor
    assert run("x", "", "") == [100, 400, 900]
