"""Series tool: per row, the ids present in it and the row before whose `column` changed from
`from` to `to`; tracks in, signal out.

Either bound blank is any value, so both blank counts every change. The values are compared as
numbers, and an id reading NaN on either row has no value there and changes nothing. An id absent
in the row before counts nothing, so an entry is a crossing and never an appearance. A column the
tables lack raises.
"""
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "transitions", "series", "tracks", "signal"
DEFAULTS = {"column": "nest", "from": "", "to": ""}


def _value(text):
    text = str(text).strip()
    return None if text == "" else float(text)


def changed(prev, cur, column, lo=None, hi=None):
    """How many ids in both tables have `column` moving from `lo` to `hi`, either None for any."""
    if len(prev) == 0 or len(cur) == 0:
        return 0
    for t in (prev, cur):
        if column not in t.dtype.names:
            raise ValueError(f"transitions: no column {column!r}; one of {t.dtype.names}")
    _, i_prev, i_cur = np.intersect1d(prev["id"], cur["id"], return_indices=True)
    a, b = prev[column][i_prev].astype(np.float64), cur[column][i_cur].astype(np.float64)
    hit = (a != b) & ~np.isnan(a) & ~np.isnan(b)
    if lo is not None:
        hit &= a == lo
    if hi is not None:
        hit &= b == hi
    return int(np.count_nonzero(hit))


def run(series, params):
    lo, hi, rows = _value(params["from"]), _value(params["to"]), series.data
    out = np.zeros(len(rows), np.float32)
    for r in range(1, len(rows)):
        out[r] = changed(rows[r - 1], rows[r], params["column"], lo, hi)
    return {"signal": out}


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_text("column", DEFAULTS["column"])
    w.add_text("from", DEFAULTS["from"])
    w.add_text("to", DEFAULTS["to"])
    return w
