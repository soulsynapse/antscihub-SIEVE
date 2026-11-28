"""Holds a cutting tool that says CUT_BY_A_PART to what it says: `hold` asks its `cut_extents` of
every run of rows of a gate and of the whole, and asserts the cuts of a part that touch neither of
its ends are cuts of the whole, and that every cut of the whole with a row in the part is a cut of
the part or meets one that touches an end. The registry reports that a tool says it and the player
takes its word; this is where the promise is checked."""
import numpy as np


def cuts(tool, params, gate, first=0):
    """The rows [first, end) of each cut `tool` answers of `gate`, a bool a row, on rows counted from `first`."""
    result = {"signal": np.asarray(gate, float), "gate": np.asarray(gate, bool)}
    return [(a + first, b + first) for a, b in (x["rows"] for x in tool.cut_extents(params, result, None))]


def hold(tool, params, gate):
    """Asserts `tool` cuts every part of `gate` as it cuts the whole, the cuts at a part's ends aside."""
    whole = cuts(tool, params, gate)
    for a in range(len(gate)):
        for b in range(a + 1, len(gate) + 1):
            part = cuts(tool, params, gate[a:b], a)
            ends = [p for p in part if p[0] <= a or p[1] >= b]
            for p in part:
                assert p in ends or p in whole, f"{tool.NAME}: of rows {a} to {b} it cuts {p}, no cut of the whole"
            for w in whole:
                if w[0] < b and w[1] > a:
                    assert w in part or any(p[0] < w[1] and p[1] > w[0] for p in ends), f"{tool.NAME}: of rows {a} to {b} it misses {w}"
