"""Series tool: what it reads, written to a csv; a signal, a blobs series or a tracks series in, the
same out.

A pass-through, as Houdini's File Cache SOP is: the rows leave unchanged, so the node has a trace
and a band like any series node, and the file is that trace. Over a signal, one line per row of the
loop window: `row`, the frame index; `time`, row over fps, in seconds; `signal`; `gate`, 1 where this
node's band keeps the row (see `sieve_player.graph.gated`). Over a table series the signal is the
records each row holds, a count this tool mints, and the file is long format, one line per record:
`row`, `time`, `id` for tracks and no such column for blobs, the table's numeric columns less
`contour` and `id`, and `gate`; a row with no records writes nothing. A row an upstream band
shuts out is absent here, a NaN signal or no table, and writes nothing either way. The key line
carries `kind=` as the type written, so a reader can refuse a file of the wrong kind by name. The
band to export is this node's. The range is the window, so the whole video is a window
the length of the video, and Write writes the rows the walk has so far and says how many. Below a
cut in time the rows are every period's held so far, one file of
them, each line carrying its period (`lines`). The key line, the write and the widget are
tools/_csvfile.py's.

The file sits beside the footage as `<stem>_<a>-<b>.csv`, `_periods` after the rows below a cut in
time, `_tracks` or `_blobs` before the extension for a table, overwritten; with `beside footage` off, Write asks where, with that name
filled in, and remembers the folder for the session.
"""
import os
import sys

import numpy as np

from tools._csvfile import FILTER, PARAMS, key_line, replace  # noqa: F401  PARAMS and FILTER are this tool's facets
from tools._table import is_tables

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "csv", "series", ("signal", "blobs", "tracks"), "same"
COLUMNS = ("row", "time", "signal", "gate")
PERIOD = ("period_first", "period_end")


def reach_in_rows(params):
    return 0, 0


def run(series, params):
    if not is_tables(series.data):
        return {"signal": np.ma.filled(np.ma.asarray(series.data, np.float32), np.nan).reshape(-1)}
    rows = np.empty(len(series.data), object)
    rows[:] = list(series.data)
    return {"rows": rows, "signal": np.array([np.nan if t is None else len(t) for t in rows], np.float32)}


def kind_of(result):
    """The type `result` writes: signal, or tracks and blobs by whether the tables carry `id`; None
    for a table result with no rows or none present, which says nothing."""
    if isinstance(result, dict) and "periods" in result:
        return next((k for *_, part in result["periods"] if (k := kind_of(part)) is not None), None)
    if not isinstance(result, dict) or "rows" not in result:
        return "signal"
    first = next((t for t in result["rows"] if t is not None), None)
    return None if first is None else "tracks" if "id" in first.dtype.names else "blobs"


def fields(dtype):
    """The columns written from a table of `dtype`, in its order: the numeric ones less `contour` and `id`."""
    return tuple(n for n in dtype.names if n not in ("contour", "id") and np.issubdtype(dtype[n], np.number))


def columns(dtype, periods=False):
    return ("row", "time", *(PERIOD if periods else ()), *(("id",) if "id" in dtype.names else ()), *fields(dtype), "gate")


def of_periods(listed):
    """What Write writes of a node below a cut in time: `listed`, a held.Listed for each of its
    periods, as a result of the node's key whose `periods` are (the period's rows, the part's first
    row, the part's result), in the order listed."""
    parts = [(lst.record.extent.rows, first, part) for lst in listed for first, part in lst.parts]
    return {"key": next((part.get("key", "") for *_, part in parts), ""), "periods": parts}


def _span(result):
    rows = [r for r, *_ in result["periods"]]
    return min(a for a, _ in rows), max(b for _, b in rows)


def count(result):
    """How many rows Write would write from `result`, 0 when it has none."""
    if not isinstance(result, dict):
        return 0
    if "periods" in result:
        return sum(count(part) for *_, part in result["periods"])
    return len(result["rows"]) if "rows" in result else len(result["signal"]) if "signal" in result else 0


def default_name(footage, start, n, result=None):
    """`start` and `n` are the window's; a result of periods is named by the rows its periods span."""
    root, _ = os.path.splitext(str(footage))
    kind = kind_of(result)
    tail = "" if kind in ("signal", None) else "_" + kind
    if isinstance(result, dict) and "periods" in result and result["periods"]:
        a, b = _span(result)
        return f"{root}_{a}-{b - 1}_periods{tail}.csv"
    return f"{root}_{start}-{start + n - 1}{tail}.csv"


def _records(result, start, fps, kind, names, dtype, said):
    if kind == "signal":
        sig = np.asarray(result["signal"], np.float32).reshape(-1)
        gate = np.asarray(result.get("gate", np.ones(len(sig), bool)), bool)
        for i, (v, g) in enumerate(zip(sig, gate)):
            if np.isnan(v):
                continue
            r = start + i
            yield f"{r},{r / fps:.6f},{said}{np.format_float_positional(v, trim='-')},{int(g)}\n"
        return
    rows = result["rows"]
    gate = np.asarray(result.get("gate", np.ones(len(rows), bool)), bool)
    for i, (t, g) in enumerate(zip(rows, gate)):
        r = start + i
        for b in () if t is None else t:
            vals = (np.format_float_positional(float(b[f]), trim="-") if np.issubdtype(dtype[f], np.floating) else str(int(b[f]))
                    for f in names)
            id = f"{int(b['id'])}," if kind == "tracks" else ""
            yield f"{r},{r / fps:.6f},{said}{id}{','.join(vals)},{int(g)}\n"


def _dtype(results):
    return next((t.dtype for r in results if "rows" in r for t in r["rows"] if t is not None), None)


def lines(result, start, fps, footage):
    """The file, a line at a time with its newline, so a clip's records never sit whole in memory. A
    float is written as the shortest text that reads back to the same value. A result of periods,
    `of_periods`'s, is one file of every period's rows, its key line over the rows they span, each
    line carrying `period_first` and `period_end`, its period's rows [first, end) on the footage, so
    a row two periods share is two lines."""
    kind = kind_of(result)
    of = result["periods"] if "periods" in result else [(None, start, result)]
    if "periods" in result:
        start, end = _span(result) if of else (start, start)
        n = end - start
    else:
        n = len(result["signal"] if kind == "signal" else result["rows"])
    yield key_line(result.get("key", ""), start, n, footage, kind) + "\n"
    if kind is None:
        return
    dtype = None if kind == "signal" else _dtype([part for *_, part in of])
    head = (*COLUMNS[:2], *PERIOD, *COLUMNS[2:]) if "periods" in result else COLUMNS
    yield ",".join(head if kind == "signal" else columns(dtype, "periods" in result)) + "\n"
    names = () if dtype is None else fields(dtype)
    for rows, first, part in of:
        said = "" if rows is None else f"{rows[0]},{rows[1]},"
        yield from _records(part, first, fps, kind, names, dtype, said)


def text(result, start, fps, footage):
    return "".join(lines(result, start, fps, footage))


def write(path, result, start, fps, footage):
    replace(path, lines(result, start, fps, footage))


def settings(parent=None):
    from tools._csvfile import widget

    return widget(parent, sys.modules[__name__])


if __name__ == "__main__":
    from sieve_player import play
    from tools import gray, motion, reduce

    sys.exit(play([gray, motion, reduce, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
