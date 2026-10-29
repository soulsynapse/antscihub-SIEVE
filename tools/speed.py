"""Frame tool: the flow field's magnitude in pixels per second. Flow in, a float32 plane out.

v2's flow_speed before its block reduction: hypot(u, v) times the source fps, which the player hands
the tool on `frames.fps`. Zero where the solve was degenerate. coarsegrain(mean) after it is v2's grid.
"""
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "speed", "frame", "flow", "gray"
DEFAULTS = {}


def run(frames, row, params):
    f = frames(row)
    return (np.hypot(f[..., 0], f[..., 1]) * frames.fps).astype(np.float32)


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    return ParamWidget(parent)   # no knobs


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import flow, gray

    sys.exit(play([gray, flow, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
