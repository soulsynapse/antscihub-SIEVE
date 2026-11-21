"""Series tool: the upstream signal smoothed over a window of rows centred on each; signal in, signal out.

Centred, never causal: the window is replayed, not live, so a burst peaks where it happened and the
playhead sits on it. `kernel` is `mean` or `median` and `reach` the rows either side, so the window
is 2 * reach + 1 rows and reach 0 is the signal untouched. A mean spreads a one-row spike over the
window; a median drops it and leaves a plateau alone, so impulse noise wants the median and jitter
the mean. At either end, and at the end of a walk still filling in, the window is the rows that
exist, so the edge rows smooth over fewer and settle as rows land.

A row the upstream node's band shuts out is absent (see `sieve_player.graph.gated`): it is NaN
here too, and the window about a row beside it is the rows that are present, as at either end.
"""
import warnings

import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "smooth", "series", "signal", "signal"
KERNELS = ("mean", "median")
MAX_REACH = 60
PARAMS = {
    "kernel": {"default": "mean", "kind": "choice", "choices": KERNELS},
    "reach": {"default": 2, "kind": "int", "range": (0, MAX_REACH)},
}


def reach_in_rows(params):
    return max(0, int(params["reach"])), max(0, int(params["reach"]))


def run(series, params):
    x = np.ma.filled(np.ma.asarray(series.data, np.float64), np.nan).reshape(-1)
    reach, k = max(0, int(params["reach"])), params["kernel"]
    if k not in KERNELS:
        raise ValueError(f"smooth: no kernel {k!r}; one of {KERNELS}")
    if reach == 0 or len(x) < 2:
        return {"signal": x.astype(np.float32)}
    w = 2 * reach + 1
    padded = np.concatenate((np.full(reach, np.nan), x, np.full(reach, np.nan)))   # nan past either end: a row that is not there
    windows = np.lib.stride_tricks.sliding_window_view(padded, w)                   # one per row of x
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)     # a window of absent rows alone: NaN, as the row is
        s = np.nanmean(windows, axis=1) if k == "mean" else np.nanmedian(windows, axis=1)
    s[np.isnan(x)] = np.nan
    return {"signal": s.astype(np.float32)}


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import gray, motion, reduce

    sys.exit(play([gray, motion, reduce, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
