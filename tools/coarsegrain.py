"""Frame tool: v2's block grid. A plane or a flow field reduced to one value per `block`-pixel cell, out as in.

A cell is the decision about grain, so it is this node and not a knob inside each tool that measures:
changeenergy -> coarsegrain(mean) is v2's change_energy grid, speed -> coarsegrain(mean) its flow_speed,
and the same cell can sit after a mask (fraction: the share of set pixels) or a background difference.
The grid is ceiling-divided, so a short last row or column of cells is reduced over the pixels it has.
On a flow field the method runs per component, so mean is the block's mean vector; max and fraction
have no vector reading and raise.
"""
from tools._blocks import METHODS, reduce_blocks

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "coarsegrain", "frame", ("gray", "mask", "flow"), "same"
PARAMS = {
    "block": {"default": 32, "kind": "int", "range": (1, 256)},
    "method": {"default": "mean", "kind": "choice", "choices": METHODS},
}


def grid(h, w, block):
    """(ny, nx): the cells over an h x w plane, the edge cells partial."""
    return -(-h // block), -(-w // block)


def reach_in_rows(params):
    return 0, 0


def run(frames, row, params):
    f = frames(row)
    m = params["method"]
    if f.ndim == 3 and m in ("max", "fraction"):
        raise ValueError(f"coarsegrain: {m!r} has no reading over a flow field; mean or sum")
    return reduce_blocks(f, params["block"], m)


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import changeenergy, gray

    sys.exit(play([gray, changeenergy, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
