"""Series tool: how many blobs each row holds; blobs in, signal out.

The walk folds each row's table to its length, so the window holds (T, 1) and never the tables,
and the signal is that column. The band on the trace is the player's, as reduce's is: handles at
1 and 1 gate the rows with exactly one blob in them.
"""
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "count", "series", "blobs", "signal"
DEFAULTS = {}


def fold(frame):
    """A row's [blob count], float64."""
    return np.array([len(frame)], np.float64)


def run(series, params):
    data = np.asarray(series.data, np.float64).reshape(len(series.data), -1)
    return {"signal": data[:, 0].astype(np.float32)}


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    return ParamWidget(parent)   # no knobs


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import blobs, gray, threshold

    sys.exit(play([gray, threshold, blobs, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
