"""Series tool: the signal it reads, written to a csv; signal in, the same signal out.

A pass-through, as Houdini's File Cache SOP is: the signal leaves unchanged, so the node has a trace
and a band like any series node, and the file is that trace. One line per row of the loop window:
`row`, the frame index; `time`, row over fps, in seconds; `signal`; `gate`, 1 where this node's band
keeps the row (see `sieve_player.graph.gated`). The band to export is this node's; an upstream band
zeroes rows before they reach here, as for any series node. The range is the window, so the whole
video is a window the length of the video, and Write writes the rows the walk has so far and says
how many. The key line, the write and the widget are tools/_csvfile.py's.

The file sits beside the footage as `<stem>_<a>-<b>.csv`, overwritten; with `beside footage` off,
Write asks where, with that name filled in, and remembers the folder for the session.
"""
import os
import sys

import numpy as np

from tools._csvfile import DEFAULTS, FILTER, key_line, replace  # noqa: F401  DEFAULTS and FILTER are this tool's facets

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "csv", "series", "signal", "signal"
COLUMNS = ("row", "time", "signal", "gate")


def run(series, params):
    return {"signal": np.asarray(series.data, np.float32).reshape(-1)}


def count(result):
    """How many rows Write would write from `result`, 0 when it has none."""
    return 0 if not isinstance(result, dict) or "signal" not in result else len(result["signal"])


def default_name(footage, start, n):
    root, _ = os.path.splitext(str(footage))
    return f"{root}_{start}-{start + n - 1}.csv"


def lines(result, start, fps, footage):
    """The file, a line at a time with its newline: the key line, the column names, one per row. A
    signal value is written as the shortest text that reads back to the same float32."""
    sig = np.asarray(result["signal"], np.float32).reshape(-1)
    gate = np.asarray(result.get("gate", np.ones(len(sig), bool)), bool)
    yield key_line(result.get("key", ""), start, len(sig), footage, result.get("plate")) + "\n"
    yield ",".join(COLUMNS) + "\n"
    for i, (v, g) in enumerate(zip(sig, gate)):
        r = start + i
        yield f"{r},{r / fps:.6f},{np.format_float_positional(v, trim='-')},{int(g)}\n"


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
