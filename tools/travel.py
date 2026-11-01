"""Series tool: the `method` over each row's steps, the centroid displacements in px of the ids in it and
the row before; tracks in, signal out. `count` is the ids that stepped over `moving` px. No shared id reads 0.
"""
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "travel", "series", "tracks", "signal"
METHODS = ("mean", "sum", "max", "count")
DEFAULTS = {"method": "mean", "moving": 1.0}


def steps(prev, cur):
    if len(prev) == 0 or len(cur) == 0:
        return np.zeros(0)
    ids, i_prev, i_cur = np.intersect1d(prev["id"], cur["id"], return_indices=True)
    return np.hypot(cur["cx"][i_cur] - prev["cx"][i_prev], cur["cy"][i_cur] - prev["cy"][i_prev]).astype(np.float64)


def run(series, params):
    m, moving = params["method"], float(params["moving"])
    if m not in METHODS:
        raise ValueError(f"travel: no method {m!r}; one of {METHODS}")
    rows = series.data
    out = np.zeros(len(rows), np.float32)
    for r in range(1, len(rows)):
        s = steps(rows[r - 1], rows[r])
        if len(s) == 0:
            continue
        out[r] = {"mean": s.mean, "sum": s.sum, "max": s.max, "count": lambda: (s > moving).sum()}[m]()
    return {"signal": out}


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_choice("method", METHODS, DEFAULTS["method"])
    w.add_float("moving", 0.0, 50.0, DEFAULTS["moving"], decimals=1)
    return w


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import blobs, gray, threshold, track

    sys.exit(play([gray, threshold, blobs, track, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
