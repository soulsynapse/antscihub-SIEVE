"""Series tool: dense Lucas-Kanade motion on a block grid, the signal SIEVE v2 ran.

Per row, the frame is measured against the previous one through the structure tensor: the
temporal difference and the spatial gradients, their products Gaussian-blurred with sigma 2 (the
blur is the tensor's window, fixed as in v2), then block-mean reduced to one float per block.
`flow` off is v2's `change_energy`, the blurred <I_t^2>; `flow` on is v2's `flow_speed`, the per-pixel
2x2 LK solve, speed in px/s, zero exactly where the solve is aperture-degenerate, reduced after the
solve so the aperture problem is not coupled to the block size. The per-row scalar is the mean over
blocks, there is no gate: this tool measures and the overlay shows the measurement. `grids` keeps
every row's grid and `draw` paints the current one over the frame as a heat map in v2's colouring,
cold-to-hot by value with the window's running maximum at full heat.
"""
import cv2
import numpy as np

NAME, KIND, EXPECTS = "lk_flow", "series", "gray"
DEFAULTS = {"flow": False, "block": 16}
SIGMA, DET_EPS = 2.0, 1e-6  # v2's constants; every v2 threshold was tuned against this blur

_cache = {}  # (series.key, flow, block) -> grids computed so far; the stack only grows under one key


def _blur(a):
    return cv2.GaussianBlur(a, (0, 0), SIGMA)


def _block_mean(f, block):
    h, w = f.shape
    ny, nx = -(-h // block), -(-w // block)
    pad = np.full((ny * block, nx * block), np.nan, np.float32)
    pad[:h, :w] = f
    return np.nanmean(pad.reshape(ny, block, nx, block), axis=(1, 3)).astype(np.float32)


def _grid(prev, cur, flow, block, fps):
    prev, cur = prev.astype(np.float32), cur.astype(np.float32)
    it = cur - prev
    if not flow:
        return _block_mean(_blur(it * it), block)
    iy, ix = np.gradient(cur)
    xx, yy, xy, xt, yt = (_blur(a) for a in (ix * ix, iy * iy, ix * iy, ix * it, iy * it))
    det = xx * yy - xy * xy
    safe = np.abs(det) > DET_EPS
    inv = np.where(safe, 1.0 / np.where(safe, det, 1.0), 0.0)
    u, v = -(yy * xt - xy * yt) * inv, -(xx * yt - xy * xt) * inv
    return _block_mean(np.hypot(u, v) * fps, block)


def run(series, params):
    d = series.data
    flow, block = bool(params["flow"]), int(params["block"])
    tk = (series.key, flow, block)
    grids = _cache.get(tk, [])[: len(d)]
    if not grids and len(d):
        grids = [_grid(d[0], d[0], flow, block, series.fps)]  # row 0 has no other side: zeros
    grids += [_grid(d[i - 1], d[i], flow, block, series.fps) for i in range(len(grids), len(d))]
    _cache.clear()
    _cache[tk] = grids
    signal = np.array([g.mean() for g in grids], np.float32)
    top = max((float(g.max()) for g in grids), default=0.0)
    return {"signal": signal, "grids": grids, "shape": d.shape[1:], "top": top}


# v2's overlay: every block tinted cold-to-hot through its turbo-like ramp at 0.6 alpha.
HEAT_STOPS = ((48, 18, 59), (69, 91, 205), (62, 155, 254), (24, 214, 203), (72, 248, 130),
              (164, 252, 60), (226, 220, 56), (254, 163, 49), (239, 89, 17), (194, 36, 3), (122, 4, 3))
HEAT_ALPHA = 0.6
_LUT = np.stack([np.interp(np.linspace(0, 1, 256), np.linspace(0, 1, len(HEAT_STOPS)),
                           [c[k] for c in HEAT_STOPS]) for k in (2, 1, 0)], axis=1).astype(np.uint8)  # BGR


def draw(painter, row, result, start):
    """Called by the player with the painter in frame pixels: the row's block grid, v2's colouring."""
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QImage, QPainter

    i = row - start
    if not isinstance(result, dict) or not 0 <= i < len(result["grids"]):
        return
    g, (h, w), top = result["grids"][i], result["shape"], max(result["top"], 1e-6)
    ny, nx = g.shape
    bgr = _LUT[np.clip(g / top * 255, 0, 255).astype(np.uint8)]
    bgra = np.ascontiguousarray(np.dstack([bgr, np.full((ny, nx), int(HEAT_ALPHA * 255), np.uint8)]))
    img = QImage(bgra.data, nx, ny, bgra.strides[0], QImage.Format_ARGB32).copy()
    painter.setRenderHint(QPainter.Antialiasing, False)
    painter.drawImage(QRectF(0, 0, w, h), img)


def settings(parent=None):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPainter, QPen
    from PySide6.QtWidgets import QWidget

    from sieve_player import ParamWidget

    class _Plot(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.sig, self.start, self.playhead = None, 0, 0
            self.setMinimumHeight(120)

        def paintEvent(self, _):
            p = QPainter(self)
            p.fillRect(self.rect(), QColor(30, 30, 30))
            if self.sig is None or not len(self.sig):
                return
            n, w, h = len(self.sig), self.width(), self.height()
            top = max(float(self.sig.max()), 1e-6)
            xs = np.arange(n) * (w / n)
            p.setPen(QPen(QColor(120, 160, 220), 1))
            pts = [(int(xs[i]), int(h - 1 - self.sig[i] / top * (h - 2))) for i in range(n)]
            for a, b in zip(pts, pts[1:]):
                p.drawLine(*a, *b)
            i = self.playhead - self.start
            if 0 <= i < n:
                p.setPen(QPen(QColor(255, 200, 60), 2))
                p.drawLine(int(xs[i]), 0, int(xs[i]), h)

    class _Widget(ParamWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.add_bool("flow", DEFAULTS["flow"])
            self.add_int("block", 1, 64, DEFAULTS["block"])
            self.plot = _Plot()
            self.layout().addWidget(self.plot)

        def show_result(self, result, start, fps):
            self.plot.sig, self.plot.start = result["signal"], start
            self.plot.update()

        def set_playhead(self, row):
            self.plot.playhead = row
            self.plot.update()

    return _Widget(parent)


if __name__ == "__main__":
    import sys

    from sieve_player import play

    sys.exit(play([sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
