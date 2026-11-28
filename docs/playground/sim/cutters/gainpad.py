"""Frame tool of the review alone: the footage cut at each run of rows a gate keeps, each frame
multiplied by `gain`. A cutting tool in time whose run is not the identity.
"""
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "gainpad", "frame", ("bgr", "gray", "mask", "hsv", "flow"), "same"
PARAMS = {"gain": {"default": 1, "kind": "int", "range": (0, 4)}}
CUT_BY = {"gate": ("signal", "tracks")}


def cut_extents(params, result, count):
    if result is None:
        raise ValueError("no gate; wire a series node into gate")
    n, gate = len(result["signal"]), result.get("gate")
    g = np.concatenate([[False], np.ones(n, bool) if gate is None else np.asarray(gate, bool), [False]])
    edges = np.flatnonzero(g[1:] != g[:-1])
    return [{"rows": (int(a), int(b))} for a, b in zip(edges[::2], edges[1::2])]


def reach_in_rows(params):
    return 0, 0


def run(frames, row, params):
    return (frames(row).astype(np.float32) * params["gain"]).clip(0, 255).astype(np.uint8)
