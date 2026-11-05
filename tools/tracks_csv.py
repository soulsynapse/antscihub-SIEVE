"""Series tool: the tracks it reads, written to a csv; tracks in, the same tracks out.

A pass-through as csv is, sharing its Write widget and key line: the rows leave unchanged, the signal
is the records each row holds, so the node's band gates rows by their count. One line per record of
the window, long format: `row`, `time`, `id`, the table's columns less `contour` and `id`, and
`gate`, 1 where this node's band keeps the row; a row with no records writes nothing, so an
upstream band's rows are simply absent. Scores and labels read it as one table of row, id, x, y.
"""
import os

import numpy as np

from tools import csv, track

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "tracks-csv", "series", "tracks", "tracks"
DEFAULTS = dict(csv.DEFAULTS)
FILTER = csv.FILTER


def fields(dtype):
    """The columns written from a table of `dtype`, in its order, less `contour` and `id`."""
    return tuple(n for n in dtype.names if n not in ("contour", "id") and dtype[n] != object)


def columns(dtype):
    return ("row", "time", "id", *fields(dtype), "gate")


def run(series, params):
    rows = np.empty(len(series.data), object)
    rows[:] = list(series.data)
    return {"rows": rows, "signal": np.array([len(t) for t in rows], np.float32)}


def count(result):
    """How many rows of the window Write would write from `result`, 0 when it has no rows."""
    return 0 if not isinstance(result, dict) or "rows" not in result else len(result["rows"])


def default_name(footage, start, n):
    root, _ = os.path.splitext(str(footage))
    return f"{root}_{start}-{start + n - 1}_tracks.csv"


def text(result, start, fps, footage):
    rows = result["rows"]
    gate = np.asarray(result.get("gate", np.ones(len(rows), bool)), bool)
    dtype = rows[0].dtype if len(rows) else track.DTYPE
    names = fields(dtype)
    lines = [f"# sieve key={result.get('key', '')} rows={start}-{start + len(rows) - 1} footage={os.path.basename(str(footage))}",
             ",".join(columns(dtype))]
    for i, (t, g) in enumerate(zip(rows, gate)):
        r = start + i
        for b in t:
            vals = (np.format_float_positional(float(b[f]), trim="-") if np.issubdtype(dtype[f], np.floating) else str(int(b[f]))
                    for f in names)
            lines.append(f"{r},{r / fps:.6f},{int(b['id'])},{','.join(vals)},{int(g)}")
    return "\n".join(lines) + "\n"


def write(path, result, start, fps, footage):
    csv.replace(path, text(result, start, fps, footage))


def settings(parent=None):
    import sys

    return csv.settings(parent, export=sys.modules[__name__])


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import blobs, gray, threshold

    sys.exit(play([gray, threshold, blobs, track, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
