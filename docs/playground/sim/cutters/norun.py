"""Frame tool of the miniature alone: `pad` with no `run`, a cutting tool that says nothing of
what it hands down, for docs/playground/sim/miniature.py to ask what the player makes of one.
"""
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "norun", "frame", ("bgr", "gray", "mask", "hsv", "flow"), "same"
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
