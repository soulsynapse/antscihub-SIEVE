"""Frame tool: |frame-to-frame difference|, gray or mask in, gray out; all zero where the row before is absent, at
row 0 and at the first row of a cut in time.

The difference is an image, not a number: what to make of it is downstream's choice (tools/reduce for a
per-row signal, tools/threshold for a mask of what moved, tools/rescale for a block mean).
"""
import cv2
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "motion", "frame", ("gray", "mask"), "gray"


def reach_in_rows(params):
    return 1, 0


def run(frames, row, params):
    f, before = frames(row), frames(row - 1)
    return np.zeros_like(f) if before is None else cv2.absdiff(f, before)


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import gray

    sys.exit(play([gray, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
