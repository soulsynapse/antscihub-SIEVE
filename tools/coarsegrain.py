"""Frame tool: v2's block grid. A plane or a flow field reduced to one value per `block`-pixel cell, out as in.

A cell is the decision about grain, so it is this node and not a knob inside each tool that measures:
changeenergy -> coarsegrain(mean) is v2's change_energy grid, speed -> coarsegrain(mean) its flow_speed,
and the same cell can sit after a mask (fraction: the share of set pixels) or a background difference.
The grid is ceiling-divided, so a short last row or column of cells is reduced over the pixels it has.
On a flow field the method runs per component, so mean is the block's mean vector; max and fraction
have no vector reading and raise.
"""
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "coarsegrain", "frame", ("gray", "mask", "flow"), "same"
METHODS = ("mean", "max", "sum", "fraction")
DEFAULTS = {"block": 32, "method": "mean"}


def grid(h, w, block):
    """(ny, nx): the cells over an h x w plane, the edge cells partial."""
    return -(-h // block), -(-w // block)


def reduce_blocks(a, block, method):
    """`a` is (H, W) or (H, W, C); out is (ny, nx[, C]) float32 by `method` over each cell."""
    a = np.asarray(a)
    h, w = a.shape[:2]
    block = max(1, int(block))
    ys, xs = np.arange(0, h, block), np.arange(0, w, block)
    if method == "fraction":
        a = a != 0
    if method == "max":
        out = np.maximum.reduceat(np.maximum.reduceat(a, ys, axis=0), xs, axis=1)
    else:
        out = np.add.reduceat(np.add.reduceat(a, ys, axis=0, dtype=np.float64), xs, axis=1)
        if method in ("mean", "fraction"):
            ny = np.diff(np.append(ys, h))
            nx = np.diff(np.append(xs, w))
            counts = np.outer(ny, nx).reshape(len(ys), len(xs), *([1] * (a.ndim - 2)))
            out = out / counts
        elif method != "sum":
            raise ValueError(f"coarsegrain: no method {method!r}; one of {METHODS}")
    return np.asarray(out, np.float32)


def run(frames, row, params):
    f = frames(row)
    m = params["method"]
    if f.ndim == 3 and m in ("max", "fraction"):
        raise ValueError(f"coarsegrain: {m!r} has no reading over a flow field; mean or sum")
    return reduce_blocks(f, params["block"], m)


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_int("block", 1, 256, DEFAULTS["block"])
    w.add_choice("method", METHODS, DEFAULTS["method"])
    return w


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import changeenergy, gray

    sys.exit(play([gray, changeenergy, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
