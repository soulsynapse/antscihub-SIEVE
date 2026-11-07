"""Series tool: the tracks whose `property` over the window lies in [lo, hi]; tracks in, tracks out.

`property` is rows (records of the id), displacement (px, first record to last), path (px, summed
over the id's consecutive records, across any gap), or mean (of `column`, NaN where every value
is). A blank bound is none; a NaN property never passes. Ids are not renumbered, and a dropped
id's records leave every row; the signal is the records each row keeps. `column` is read only for
mean, and one the tables lack raises then.
"""
import numpy as np

from tools._table import draw_tracks

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "tracks-filter", "series", "tracks", "tracks"
PROPERTIES = ("rows", "displacement", "path", "mean")
DEFAULTS = {"property": "rows", "column": "area", "lo": "", "hi": ""}


def properties(rows, property, column="area"):
    """Each id's `property` over `rows`, as {id: value}."""
    if property not in PROPERTIES:
        raise ValueError(f"tracks-filter: no property {property!r}; one of {PROPERTIES}")
    seen = {}
    for t in rows:
        if property == "mean" and len(t) and column not in t.dtype.names:
            raise ValueError(f"tracks-filter: no column {column!r}; one of {t.dtype.names}")
        for b in t:
            seen.setdefault(int(b["id"]), []).append(b)
    out = {}
    for id, recs in seen.items():
        if property == "rows":
            out[id] = len(recs)
        elif property == "mean":
            with np.errstate(invalid="ignore"):
                out[id] = float(np.nanmean([float(b[column]) for b in recs])) if any(not np.isnan(float(b[column])) for b in recs) else np.nan
        else:
            xy = np.array([(float(b["cx"]), float(b["cy"])) for b in recs])
            out[id] = float(np.hypot(*(xy[-1] - xy[0]))) if property == "displacement" else float(np.hypot(*np.diff(xy, axis=0).T).sum())
    return out


def bound(text, default):
    text = str(text).strip()
    return default if text == "" else float(text)


def keep(rows, property, column, lo, hi):
    value = properties(rows, property, column)
    lo, hi = bound(lo, -np.inf), bound(hi, np.inf)
    kept = {id for id, v in value.items() if lo <= v <= hi}
    out = np.empty(len(rows), object)
    out[:] = [t[np.isin(t["id"], list(kept))] if len(t) else t for t in rows]
    return out


def run(series, params):
    rows = keep(series.data, params["property"], params["column"], params["lo"], params["hi"])
    return {"rows": rows, "signal": np.array([len(t) for t in rows], np.float32)}


def draw(painter, row, result, start, params):
    draw_tracks(painter, row, result, start, params.get("outline", "box"))


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_choice("property", PROPERTIES, DEFAULTS["property"])
    w.add_text("column", DEFAULTS["column"])
    w.add_text("lo", DEFAULTS["lo"])
    w.add_text("hi", DEFAULTS["hi"])
    return w
