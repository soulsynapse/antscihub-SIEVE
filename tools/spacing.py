"""Series tool: how far apart a row's blobs are; blobs in, signal out.

`method` is the mean, median or min over the row's blobs of the distance in px from each centroid
to its nearest other, or pairs, the count of centroid pairs within `r` px. A row with fewer than
two blobs reads 0, as count's empty row does, since a NaN would blank the trace. No fold: the
window holds the tables, as it does for size.
"""
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "spacing", "series", "blobs", "signal"
METHODS = ("mean", "median", "min", "pairs")
DEFAULTS = {"method": "mean", "r": 20.0}


def spacing(table, method, r=0.0):
    if method not in METHODS:
        raise ValueError(f"spacing: no method {method!r}; one of {METHODS}")
    if len(table) < 2:
        return 0.0
    xy = np.stack([table["cx"], table["cy"]], axis=1).astype(np.float64)
    d = np.hypot(*(xy[:, None, :] - xy[None, :, :]).T)
    if method == "pairs":
        return float(np.count_nonzero(np.triu(d <= r, 1)))
    np.fill_diagonal(d, np.inf)
    return float(getattr(np, method)(d.min(axis=1)))


def run(series, params):
    m, r = params["method"], float(params["r"])
    return {"signal": np.array([spacing(t, m, r) for t in series.data], np.float32)}


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_choice("method", METHODS, DEFAULTS["method"])
    w.add_float("r", 0.0, 500.0, DEFAULTS["r"], decimals=1)
    return w
