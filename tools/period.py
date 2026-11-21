"""Frame tool: the footage cut into periods of its rows, each a cut of its own that every node below
runs inside; a frame of any plane kind in, out as in.

The periods are fed by a file a `file` selector finds, wired into `periods`, or by a series node
wired into `gate`, and never both. A gate's periods are the runs of rows its gate keeps over the
whole footage, each [first, end) and named by its first row, so two that touch are one; while no
walk of the clip is held under the key the node wired there has, there are none, and the plan says
the `period` waits on it. A file is JSON:
`{"rows": the footage's count of rows, "periods": [{"name": ..., "first": ..., "end": ...}, ...]}`,
`first` the footage row a period begins at and `end` the row past its last, so a period is the
rows [first, end). Periods may touch and may overlap, each its own. A top-level key other than
`rows` and `periods` is ignored. `load_periods` raises on a file that does not read, a repeated
name, a period of no rows and one past `rows`, saying which. A save of the file reaches the node
through the window's watch on it, as a geometry file's reaches a `region`.

`cut_extents` is a cut a period, none chosen over another, of the gate's result where one is
handed and else of the file's. The key holds nothing of where the periods lie, so a node below is
keyed alike in every period and its values are told apart by the cut each read
(`sieve_player/cut.py:read`). A frame whose footage is not `rows` long raises with
the two counts, as does a file of no periods.
"""
import json

import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "period", "frame", ("bgr", "gray", "mask", "hsv", "flow"), "same"
PARAMS = {
    "rows": {"default": 0},
    "periods": {"default": []},
}


def _row(v, what):
    if isinstance(v, bool) or not isinstance(v, int):
        raise ValueError(f"{what} is {v!r}, not a row")
    return v


def load_periods(path):
    """Params from a file of periods: `rows` and `periods` as the file has them, checked. Raises
    ValueError on a malformed file with what was wrong."""
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    if not isinstance(d, dict) or "rows" not in d or "periods" not in d:
        raise ValueError("a file of periods has rows and periods")
    rows = d["rows"]
    if _row(rows, "rows") <= 0:
        raise ValueError(f"rows is {rows}, not a count of rows")
    if not isinstance(d["periods"], list):
        raise ValueError("periods is not a list")
    periods, seen = [], set()
    for i, p in enumerate(d["periods"]):
        if not isinstance(p, dict) or set(p) != {"name", "first", "end"}:
            raise ValueError(f"period {i} is not a name, a first and an end: {p!r}")
        name = p["name"]
        if not isinstance(name, str) or not name:
            raise ValueError(f"period {i} has the name {name!r}, not a word")
        if name in seen:
            raise ValueError(f"two periods are named {name!r}")
        first, end = _row(p["first"], f"{name}'s first"), _row(p["end"], f"{name}'s end")
        if first < 0 or end <= first:
            raise ValueError(f"{name} is rows {first} to {end}, no rows")
        if end > rows:
            raise ValueError(f"{name} ends at row {end}, past the footage's {rows}")
        seen.add(name)
        periods.append({"name": name, "first": first, "end": end})
    return {"rows": rows, "periods": periods}


PATHS = {"periods": load_periods}
CUT_BY = {"gate": ("signal", "tracks")}


def kept(gate):
    """[(first, end)] of each run of rows `gate`, a bool a row, keeps."""
    g = np.concatenate([[False], np.asarray(gate, bool), [False]])
    edges = np.flatnonzero(g[1:] != g[:-1])
    return [(int(a), int(b)) for a, b in zip(edges[::2], edges[1::2])]


def key_params(params):
    return {}


def cut_extents(params, result):
    if result is not None:
        gate = result.get("gate")       # a result no band was applied to keeps every row
        return [{"rows": rows} for rows in kept(np.ones(len(result["signal"]), bool) if gate is None else gate)]
    if not params["periods"]:
        raise ValueError("no periods; wire a file selector into periods" if not params["rows"] else "the file has no periods")
    return [{"rows": (p["first"], p["end"])} for p in params["periods"]]


def reach_in_rows(params):
    return 0, 0


def run(frames, row, params):
    if params["rows"] and not params["periods"]:
        raise ValueError("the file has no periods")
    if params["rows"] and params["rows"] != frames.count:
        raise ValueError(f"the footage is {frames.count} rows and the file's {params['rows']}; a period's rows are its footage's")
    return frames(row)
