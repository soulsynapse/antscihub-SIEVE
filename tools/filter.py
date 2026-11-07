"""Frame tool: the records of a blob table whose `field` lies in [lo, hi]; blobs in, blobs out.

`field` is any column of the table, blobs' own or one added upstream, or `core_ratio` (core / area)
or `aspect` (major / minor). A blank bound is none; a NaN field never passes.
"""
import numpy as np

from tools._table import DTYPE, OUTLINES, draw as draw_table

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "filter", "frame", "blobs", "blobs"
RATIOS = ("core_ratio", "aspect")
FIELDS = (*DTYPE.names, *RATIOS)
DEFAULTS = {"field": "area", "lo": "", "hi": "", "outline": "box"}


def column(table, field):
    with np.errstate(divide="ignore", invalid="ignore"):
        if field == "core_ratio":
            return np.where(table["core"] < 0, np.nan, table["core"] / np.maximum(table["area"], 1))
        if field == "aspect":
            return table["major"] / np.where(table["minor"] > 0, table["minor"], np.nan)
    if field not in table.dtype.names:
        raise ValueError(f"filter: no field {field!r}; one of {(*table.dtype.names, *RATIOS)}")
    return table[field].astype(np.float64)


def bound(text, default):
    text = str(text).strip()
    return default if text == "" else float(text)


def keep(table, field, lo, hi):
    v = column(table, field)
    return table[(v >= bound(lo, -np.inf)) & (v <= bound(hi, np.inf))]


def run(frames, row, params):
    return keep(frames(row), params["field"], params["lo"], params["hi"])


def draw(painter, row, result, start, params):
    draw_table(painter, result, params.get("outline", "box"), color=(240, 200, 60))


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_choice("field", FIELDS, DEFAULTS["field"], editable=True)
    w.add_text("lo", DEFAULTS["lo"])
    w.add_text("hi", DEFAULTS["hi"])
    w.add_choice("outline", OUTLINES, DEFAULTS["outline"])
    return w


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import blobs, gray, threshold

    sys.exit(play([gray, threshold, blobs, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
