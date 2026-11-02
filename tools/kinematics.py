"""Series tool: each record's motion from its id's previous record; tracks in, tracks out with
`dx`, `dy`, `speed` and `heading` added.

`dx` and `dy` are px per row, the displacement from the id's previous record over the rows between,
so a step across a gap is not a jump; `speed` is their length and `heading` their direction in
degrees from the x axis with y down, the convention of blobs' `angle` and decode's heading, which
resolves the 180 degrees `angle` cannot. An id's first record in the window reads NaN in all four.
The signal is the mean speed of the row's records that have one, 0 where none does. A table that
already has one of the columns raises.
"""
import numpy as np

from tools.blobs import with_column

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "kinematics", "series", "tracks", "tracks"
COLUMNS = ("dx", "dy", "speed", "heading")
DEFAULTS = {}


def kinematics(rows):
    out, last = np.empty(len(rows), object), {}
    for r, t in enumerate(rows):
        v = np.full((len(t), 2), np.nan)
        for i, b in enumerate(t):
            id = int(b["id"])
            if id in last:
                r0, x0, y0 = last[id]
                v[i] = (float(b["cx"]) - x0) / (r - r0), (float(b["cy"]) - y0) / (r - r0)
            last[id] = r, float(b["cx"]), float(b["cy"])
        with np.errstate(invalid="ignore"):
            cols = {"dx": v[:, 0], "dy": v[:, 1], "speed": np.hypot(v[:, 0], v[:, 1]),
                    "heading": np.degrees(np.arctan2(v[:, 1], v[:, 0]))}
        for name in COLUMNS:
            t = with_column(t, name, cols[name].astype(np.float32))
        out[r] = t
    return out


def run(series, params):
    rows = kinematics(series.data)
    with np.errstate(invalid="ignore"):
        signal = np.array([np.nanmean(t["speed"]) if len(t) and not np.all(np.isnan(t["speed"])) else 0.0 for t in rows], np.float32)
    return {"rows": rows, "signal": signal}


def draw(painter, row, result, start, params):
    from tools import track

    track.draw(painter, row, result, start, params)


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    return ParamWidget(parent)   # no knobs
