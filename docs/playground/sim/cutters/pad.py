"""Frame tool of the miniature alone: the footage cut at each run of rows a gate keeps, widened by
`pad` rows either side and held to the result's rows, so a cut reads rows its gate does not keep
and, past half the gap between two runs, two cuts overlap. A cutting tool that is not `period`,
for docs/playground/sim/miniature.py to ask its oracles of.
"""
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "pad", "frame", ("bgr", "gray", "mask", "hsv", "flow"), "same"
PARAMS = {"pad": {"default": 1, "kind": "int", "range": (0, 64)}}
CUT_BY = {"gate": ("signal", "tracks")}


def key_params(params):
    return {}


def cut_extents(params, result, count):
    if result is None:
        raise ValueError("no gate; wire a series node into gate")
    n, gate = len(result["signal"]), result.get("gate")
    g = np.concatenate([[False], np.ones(n, bool) if gate is None else np.asarray(gate, bool), [False]])
    edges = np.flatnonzero(g[1:] != g[:-1])
    return [{"rows": (max(0, int(a) - params["pad"]), min(n, int(b) + params["pad"]))} for a, b in zip(edges[::2], edges[1::2])]


def reach_in_rows(params):
    return 0, 0


def run(frames, row, params):
    return frames(row)
