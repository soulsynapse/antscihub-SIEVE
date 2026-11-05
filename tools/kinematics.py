"""Series tool: each record's motion from its id's previous record; tracks in, tracks out with
`dx`, `dy`, `speed` and `heading` added.

`dx` and `dy` are px per row, the displacement from the id's latest record at least `span` rows
earlier over the rows between, so a step across a gap is not a jump and a span of several rows
reads a direction where one row is the centroid's jitter; `speed` is their length and `heading`
their direction in degrees from the x axis with y down, the convention of blobs' `angle` and
decode's heading, which resolves the 180 degrees `angle` cannot. A record with none that far back
reads NaN in all four. The signal is the mean speed of the row's records that have one, 0 where
none does. A table that already has one of the columns raises.
"""
from collections import deque

import numpy as np

from tools.blobs import with_column

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "kinematics", "series", "tracks", "tracks"
COLUMNS = ("dx", "dy", "speed", "heading")
DEFAULTS = {"span": 1}
MAX_SPAN = 300


def kinematics(rows, span=1):
    out, seen = np.empty(len(rows), object), {}
    for r, t in enumerate(rows):
        v = np.full((len(t), 2), np.nan)
        for i, b in enumerate(t):
            past = seen.setdefault(int(b["id"]), deque())
            while len(past) > 1 and past[1][0] <= r - span:   # past[0] is the latest record span rows back; the rest are newer
                past.popleft()
            if past and past[0][0] <= r - span:
                r0, x0, y0 = past[0]
                v[i] = (float(b["cx"]) - x0) / (r - r0), (float(b["cy"]) - y0) / (r - r0)
            past.append((r, float(b["cx"]), float(b["cy"])))
        with np.errstate(invalid="ignore"):
            cols = {"dx": v[:, 0], "dy": v[:, 1], "speed": np.hypot(v[:, 0], v[:, 1]),
                    "heading": np.degrees(np.arctan2(v[:, 1], v[:, 0]))}
        for name in COLUMNS:
            t = with_column(t, name, cols[name].astype(np.float32))
        out[r] = t
    return out


def run(series, params):
    rows = kinematics(series.data, int(params["span"]))
    with np.errstate(invalid="ignore"):
        signal = np.array([np.nanmean(t["speed"]) if len(t) and not np.all(np.isnan(t["speed"])) else 0.0 for t in rows], np.float32)
    return {"rows": rows, "signal": signal}


def draw(painter, row, result, start, params):
    from tools import track

    track.draw(painter, row, result, start, params)


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_int("span", 1, MAX_SPAN, DEFAULTS["span"])
    return w
