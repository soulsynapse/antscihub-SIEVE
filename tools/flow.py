"""Frame tool: v2's Lucas-Kanade optical flow, per pixel. Gray or mask in, a flow field out; row 0 is zero.

The field is (H, W, 2) float32: u along columns and v along rows, in pixels per frame. Each pixel
solves [[Jxx, Jxy], [Jxy, Jyy]] (u, v) = -(Jxt, Jyt) on the gradient products blurred with `sigma`,
the tensor window, and a pixel whose determinant is under DET_EPS is aperture-degenerate and reads
exactly zero rather than a near-zero divide. The solve runs at pixel grain so that coarsegrain's cell
is not coupled to it: speed and agreement read the field, and coarsegrain(mean) is the block's mean vector.
"""
import cv2
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "flow", "frame", ("gray", "mask"), "flow"
DEFAULTS = {"sigma": 2.0}
DET_EPS = 1e-6   # v1's cutoff: below it the spatial tensor is rank-deficient and the flow is zero


def lk(prev, gray, sigma):
    """(u, v) per pixel, float32, zero where the solve is degenerate."""
    it = gray - prev
    iy, ix = (np.asarray(g, np.float32) for g in np.gradient(gray))
    blur = lambda p: cv2.GaussianBlur(p, (0, 0), sigma)  # noqa: E731
    xx, yy, xy, xt, yt = blur(ix * ix), blur(iy * iy), blur(ix * iy), blur(ix * it), blur(iy * it)
    det = xx * yy - xy * xy
    safe = np.abs(det) > DET_EPS
    inv = np.where(safe, 1.0 / np.where(safe, det, 1.0), 0.0)
    u = -(yy * xt - xy * yt) * inv
    v = -(xx * yt - xy * xt) * inv
    return np.dstack([u, v]).astype(np.float32)


def run(frames, row, params):
    g = np.asarray(frames(row), np.float32)
    if row == 0:
        return np.zeros(g.shape + (2,), np.float32)
    return lk(np.asarray(frames(row - 1), np.float32), g, params["sigma"])


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_float("sigma", 0.5, 8.0, DEFAULTS["sigma"], decimals=1)
    return w


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import gray

    sys.exit(play([gray, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
