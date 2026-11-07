"""Series tool: the `method` over a numeric column of each row's blob table; blobs in, signal out.

`field` is `area`, `major`, `minor`, `w` or `h`, in px, or any numeric column added upstream;
`method` reduces the row's column to one number. A row with no blobs reads 0, as count's does,
since the trace scales by the signal's max and a NaN there would blank it. No fold: the median needs the whole column, so the window holds
the tables, as it does for track.
"""
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "size", "series", "blobs", "signal"
FIELDS = ("area", "major", "minor", "w", "h")
METHODS = ("mean", "median", "min", "max", "sum", "std")
DEFAULTS = {"field": "area", "method": "mean"}


def run(series, params):
    field, m = params["field"], params["method"]
    if m not in METHODS:
        raise ValueError(f"size: no method {m!r}; one of {METHODS}")
    reduce = getattr(np, m)
    rows = series.data
    out = np.zeros(len(rows), np.float32)
    for r, t in enumerate(rows):
        if field not in t.dtype.names or t.dtype[field] == object:
            raise ValueError(f"size: no numeric field {field!r}; one of {tuple(n for n in t.dtype.names if t.dtype[n] != object)}")
        if len(t):
            out[r] = reduce(np.asarray(t[field], np.float64))
    return {"signal": out}


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
