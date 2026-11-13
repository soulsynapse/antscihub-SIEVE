"""Series tool: how many records each row holds; a blobs or a tracks table in, signal out.

The walk folds a frame node's rows to their lengths, so the window holds (T, 1) and never the
tables, and the signal is that column; fed by a series node, track say, the rows arrive as tables
and the signal is their lengths. The band on the trace is the player's, as reduce's is: handles at
1 and 1 gate the rows with exactly one record in them.
"""
import numpy as np

from tools._table import is_table

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "count", "series", ("blobs", "tracks"), "signal"
DEFAULTS = {}


def fold(frame):
    """A row's [record count], float64."""
    return np.array([len(frame)], np.float64)


def run(series, params):
    out = np.zeros(len(series.data), np.float32)
    for r, row in enumerate(series.data):
        out[r] = step(None, row, r, params)[1]["signal"]
    return {"signal": out}


def step(state, row, i, params):
    """No state: a row's signal is its table's length or its fold's one number."""
    return None, {"signal": np.float32(len(row) if is_table(row) else np.asarray(row, np.float64).reshape(-1)[0])}


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    return ParamWidget(parent)   # no knobs


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import blobs, gray, threshold

    sys.exit(play([gray, threshold, blobs, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
