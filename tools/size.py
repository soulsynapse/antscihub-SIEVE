"""Series tool: the `method` over a numeric column of each row's table; a blobs or a tracks table in, signal out.

`field` is `area`, `major`, `minor`, `w` or `h`, in px, or any numeric column added upstream;
`method` reduces the row's column to one number. A row with no records reads 0, as count's does,
since the trace scales by the signal's max and a NaN there would blank it. No fold: the median needs the whole column, so the window holds
the tables, as it does for track.
"""
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "size", "series", ("blobs", "tracks"), "signal"
FIELDS = ("area", "major", "minor", "w", "h")
METHODS = ("mean", "median", "min", "max", "sum", "std")
DEFAULTS = {"field": "area", "method": "mean"}


def run(series, params):
    out = np.zeros(len(series.data), np.float32)
    for r, t in enumerate(series.data):
        out[r] = step(None, t, r, params)[1]["signal"]
    return {"signal": out}


def step(state, row, i, params):
    """No state: a row's signal is its own table's."""
    field, m = params["field"], params["method"]
    if m not in METHODS:
        raise ValueError(f"size: no method {m!r}; one of {METHODS}")
    if field not in row.dtype.names or row.dtype[field] == object:
        raise ValueError(f"size: no numeric field {field!r}; one of {tuple(n for n in row.dtype.names if row.dtype[n] != object)}")
    return None, {"signal": np.float32(getattr(np, m)(np.asarray(row[field], np.float64)) if len(row) else 0.0)}


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_choice("field", FIELDS, DEFAULTS["field"], editable=True)
    w.add_choice("method", METHODS, DEFAULTS["method"])
    return w


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import blobs, gray, threshold

    sys.exit(play([gray, threshold, blobs, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
