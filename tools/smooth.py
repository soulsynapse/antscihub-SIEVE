"""Series tool: the upstream signal smoothed over a window of rows centred on each; signal in, signal out.

Centred, never causal: the window is replayed, not live, so a burst peaks where it happened and the
playhead sits on it. `kernel` is `mean` or `median` and `reach` the rows either side, so the window
is 2 * reach + 1 rows and reach 0 is the signal untouched. A mean spreads a one-row spike over the
window; a median drops it and leaves a plateau alone, so impulse noise wants the median and jitter
the mean. At either end, and at the end of a walk still filling in, the window is the rows that
exist, so the edge rows smooth over fewer and settle as rows land.

Reads what the upstream node's band lets through, zeros where it does not (see
`sieve_player.graph.gated`): a stretch shut out upstream pulls a mean down at its edges.
"""
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "smooth", "series", "signal", "signal"
KERNELS = ("mean", "median")
DEFAULTS = {"kernel": "mean", "reach": 2}
MAX_REACH = 60


def run(series, params):
    x = np.asarray(series.data, np.float64).reshape(-1)
    reach, k = max(0, int(params["reach"])), params["kernel"]
    if k not in KERNELS:
        raise ValueError(f"smooth: no kernel {k!r}; one of {KERNELS}")
    if reach == 0 or len(x) < 2:
        return {"signal": x.astype(np.float32)}
    w = 2 * reach + 1
    padded = np.concatenate((np.full(reach, np.nan), x, np.full(reach, np.nan)))   # nan past either end: a row that is not there
    windows = np.lib.stride_tricks.sliding_window_view(padded, w)                   # one per row of x
    s = np.nanmean(windows, axis=1) if k == "mean" else np.nanmedian(windows, axis=1)
    return {"signal": s.astype(np.float32)}


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_choice("kernel", KERNELS, DEFAULTS["kernel"])
    w.add_int("reach", 0, MAX_REACH, DEFAULTS["reach"])
    return w


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import gray, motion, reduce

    sys.exit(play([gray, motion, reduce, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
