"""Frame tool: v2's flow agreement, a coarse-grained measure. Flow in, one value in [0, 1] per `block` cell out.

Of the pixels in a cell that resolved a flow, how many moved the same way: the length of the mean of
their unit vectors. Direction is circular, so this is a circular mean, and two pixels moving
opposite ways cancel rather than average to a direction nobody moved in. The mean runs over the
moving pixels only, so a cell half floor reports the agreement of the half that moved, not half of
it; a cell with no moving pixel reports 0, meaning nothing measured. The cell is this tool's, not
coarsegrain's, because the unit vectors have to be formed before they are averaged and the field
after coarsegrain(mean) no longer has them.
"""
import numpy as np

from tools.coarsegrain import reduce_blocks

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "agreement", "frame", "flow", "gray"
DEFAULTS = {"block": 32}


def run(frames, row, params):
    f = np.asarray(frames(row), np.float32)
    mag = np.hypot(f[..., 0], f[..., 1])
    moving = mag > 0.0
    unit = np.where(moving[..., None], f / np.where(moving, mag, 1.0)[..., None], 0.0).astype(np.float32)
    share = reduce_blocks(moving, params["block"], "mean")          # moving pixels over the cell's pixels
    mean = reduce_blocks(unit, params["block"], "mean")             # unit sum over the cell's pixels
    ok = share > 0.0
    resultant = np.hypot(mean[..., 0], mean[..., 1]) / np.where(ok, share, 1.0)
    return np.where(ok, np.minimum(resultant, 1.0), 0.0).astype(np.float32)


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_int("block", 1, 256, DEFAULTS["block"])
    return w


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import flow, gray

    sys.exit(play([gray, flow, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
