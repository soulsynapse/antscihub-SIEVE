"""Holds a series tool that steps to its oracle, `run`: `hold` steps the tool over a series and
asserts each row's share equals what `run` puts at that index over the rows so far and over the
whole, and that the shares accumulated equal `run` over the whole, field for field and dtype for
dtype; the AssertionError names the first row that diverged. The registry reports that a tool
offers `step` and never calls it; this is where a tool's promise is checked."""
import numpy as np

from sieve_player.graph import Series


def same(a, b):
    """Equal in value and dtype, NaN equal to NaN; tables by column, object arrays by element, and
    a dtype's plane metadata counted."""
    if isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
        if a.dtype != b.dtype or a.dtype.metadata != b.dtype.metadata or a.shape != b.shape:
            return False
        if a.dtype.names:
            return all(same(a[n], b[n]) for n in a.dtype.names)
        if a.dtype == object:
            return all(same(x, y) for x, y in zip(a.ravel(), b.ravel()))
        return bool(np.array_equal(a, b, equal_nan=True))
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        return False
    a, b = np.asarray(a), np.asarray(b)
    if a.dtype != b.dtype:
        return False
    return bool(a == b) or (a.dtype.kind == "f" and bool(np.isnan(a)) and bool(np.isnan(b)))


def accumulate(shares):
    """The result the per-row `shares` make, in order: a field whose shares are tables is an object
    array of them, any other the array of its values in their own dtype."""
    out = {}
    for field in shares[0]:
        values = [s[field] for s in shares]
        if isinstance(values[0], np.ndarray):
            a = np.empty(len(values), object)
            for i, v in enumerate(values):
                a[i] = v
        else:
            a = np.array(values)
        out[field] = a
    return out


def hold(tool, data, params, start=0, fps=30.0):
    """Asserts `tool.step` agrees with `tool.run` over `data`, a sequence of folded rows, and returns
    the accumulated result."""
    whole = tool.run(Series(data, "k", start, fps), params)
    state, shares = None, []
    for i, row in enumerate(data):
        state, share = tool.step(state, row, i, params)
        assert set(share) == set(whole), f"{tool.NAME}: step gives {sorted(share)}, run gives {sorted(whole)}"
        prefix = tool.run(Series(data[:i + 1], "k", start, fps), params)
        for field in share:
            for name, result in (("whole", whole), ("rows so far", prefix)):
                assert same(share[field], result[field][i]), f"{tool.NAME}: step diverged from run over the {name} at row {i}, field {field!r}"
        shares.append(share)
    out = accumulate(shares)
    for field in whole:
        assert same(out[field], whole[field]), f"{tool.NAME}: the accumulated {field!r} differs from run's"
    return out
