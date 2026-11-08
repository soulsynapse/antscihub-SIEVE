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
    out, state = np.zeros(len(series.data), np.float32), None
    for r, t in enumerate(series.data):
        state, share = step(state, t, r, params)
        out[r] = share["signal"]
    return {"signal": out}


def step(state, row, i, params):
    """The state is the row before, None at the first, which reads 0."""
    m, moving = params["method"], float(params["moving"])
    if m not in METHODS:
        raise ValueError(f"travel: no method {m!r}; one of {METHODS}")
    s = np.zeros(0) if state is None else steps(state, row)
    v = 0.0 if len(s) == 0 else {"mean": s.mean, "sum": s.sum, "max": s.max, "count": lambda: (s > moving).sum()}[m]()
    return row, {"signal": np.float32(v)}


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
