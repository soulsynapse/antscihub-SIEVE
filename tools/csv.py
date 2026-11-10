"""Series tool: what it reads, written to a csv; a signal, a blobs series or a tracks series in, the
same out.

A pass-through, as Houdini's File Cache SOP is: the rows leave unchanged, so the node has a trace
and a band like any series node, and the file is that trace. Over a signal, one line per row of the
loop window: `row`, the frame index; `time`, row over fps, in seconds; `signal`; `gate`, 1 where this
node's band keeps the row (see `sieve_player.graph.gated`). Over a table series the signal is the
records each row holds, a count this tool mints, and the file is long format, one line per record:
`row`, `time`, `id` for tracks and no such column for blobs, the table's numeric columns less
`contour` and `id`, and `gate`; a row with no records writes nothing, so an upstream band's rows
are simply absent. The key line carries `kind=` as the type written, so a reader can refuse a file
of the wrong kind by name. The band to export is this node's; an upstream band zeroes rows before
they reach here, as for any series node. The range is the window, so the whole video is a window
the length of the video, and Write writes the rows the walk has so far and says how many. The key
line, the write and the widget are tools/_csvfile.py's.

The file sits beside the footage as `<stem>_<a>-<b>.csv`, `_tracks` or `_blobs` before the
extension for a table, overwritten; with `beside footage` off, Write asks where, with that name
filled in, and remembers the folder for the session.
"""
import os
import sys

import numpy as np

from tools._csvfile import DEFAULTS, FILTER, key_line, replace  # noqa: F401  DEFAULTS and FILTER are this tool's facets

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "csv", "series", ("signal", "blobs", "tracks"), "same"
COLUMNS = ("row", "time", "signal", "gate")


def is_tables(data):
    return len(data) > 0 and getattr(data[0], "dtype", None) is not None and data[0].dtype.names is not None


def run(series, params):
    if not is_tables(series.data):
        return {"signal": np.asarray(series.data, np.float32).reshape(-1)}
    rows = np.empty(len(series.data), object)
    rows[:] = list(series.data)
    return {"rows": rows, "signal": np.array([len(t) for t in rows], np.float32)}


def kind_of(result):
    """The type `result` writes: signal, or tracks and blobs by whether the tables carry `id`; None
    for a table result with no rows, which says nothing."""
    if not isinstance(result, dict) or "rows" not in result:
        return "signal"
    rows = result["rows"]
    return None if not len(rows) else "tracks" if "id" in rows[0].dtype.names else "blobs"


def fields(dtype):
    """The columns written from a table of `dtype`, in its order: the numeric ones less `contour` and `id`."""
    return tuple(n for n in dtype.names if n not in ("contour", "id") and np.issubdtype(dtype[n], np.number))


def columns(dtype):
    return ("row", "time", *(("id",) if "id" in dtype.names else ()), *fields(dtype), "gate")


def count(result):
    """How many rows of the window Write would write from `result`, 0 when it has none."""
    if not isinstance(result, dict):
        return 0
    return len(result["rows"]) if "rows" in result else len(result["signal"]) if "signal" in result else 0


def default_name(footage, start, n, result=None):
    root, _ = os.path.splitext(str(footage))
    kind = kind_of(result)
    return f"{root}_{start}-{start + n - 1}{'' if kind in ('signal', None) else '_' + kind}.csv"


def lines(result, start, fps, footage):
    """The file, a line at a time with its newline, so a clip's records never sit whole in memory. A
    float is written as the shortest text that reads back to the same value."""
    kind = kind_of(result)
    if kind == "signal":
        sig = np.asarray(result["signal"], np.float32).reshape(-1)
        gate = np.asarray(result.get("gate", np.ones(len(sig), bool)), bool)
        yield key_line(result.get("key", ""), start, len(sig), footage, result.get("plate"), kind) + "\n"
        yield ",".join(COLUMNS) + "\n"
        for i, (v, g) in enumerate(zip(sig, gate)):
            r = start + i
            yield f"{r},{r / fps:.6f},{np.format_float_positional(v, trim='-')},{int(g)}\n"
        return
    rows = result["rows"]
    gate = np.asarray(result.get("gate", np.ones(len(rows), bool)), bool)
    yield key_line(result.get("key", ""), start, len(rows), footage, result.get("plate"), kind) + "\n"
    if not len(rows):
        return
    dtype = rows[0].dtype
    names = fields(dtype)
    yield ",".join(columns(dtype)) + "\n"
    for i, (t, g) in enumerate(zip(rows, gate)):
        r = start + i
        for b in t:
            vals = (np.format_float_positional(float(b[f]), trim="-") if np.issubdtype(dtype[f], np.floating) else str(int(b[f]))
                    for f in names)
            id = f"{int(b['id'])}," if kind == "tracks" else ""
            yield f"{r},{r / fps:.6f},{id}{','.join(vals)},{int(g)}\n"


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
