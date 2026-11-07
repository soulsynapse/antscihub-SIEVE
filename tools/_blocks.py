"""The block grid coarsegrain and agreement reduce a plane over. Not a tool; a tool imports it and
no other tool (tests/test_seams.py)."""
import numpy as np

METHODS = ("mean", "max", "sum", "fraction")


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
            raise ValueError(f"no method {method!r}; one of {METHODS}")
    return np.asarray(out, np.float32)
