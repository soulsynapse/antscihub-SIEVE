"""Drawing a step's output at display resolution.

Ported from ``experiments/tool-experiments/surfaces.py``, which prices the
two rules this module follows. The field arrives at analysis size and is
drawn at display size — the cheaper and more honest order (average the
quantity, then colour it, not the reverse). The ceiling is required rather
than auto-derived: an overlay that renormalises per frame makes a still
scene look exactly as active as a moving one.
"""

from __future__ import annotations

from typing import Any

import numpy as np

try:
    import cv2 as _cv2
except ImportError:
    _cv2 = None


def overlay(display: Any, field: Any, ceiling: float,
            alpha: float = 0.55) -> Any:
    """Blend a scalar field over the frame on screen.

    Uses cv2 when available (inferno colormap); falls back to a warm ramp
    in pure numpy otherwise.
    """
    h, w = display.shape[:2]
    if field.shape[:2] != (h, w):
        if _cv2 is not None:
            interp = _cv2.INTER_AREA if field.shape[1] > w else _cv2.INTER_LINEAR
            field = _cv2.resize(field, (w, h), interpolation=interp)
        else:
            ys = np.clip(np.arange(h) * field.shape[0] // h, 0, field.shape[0] - 1)
            xs = np.clip(np.arange(w) * field.shape[1] // w, 0, field.shape[1] - 1)
            field = field[np.ix_(ys, xs)]
    top = max(float(ceiling), 1e-6)
    normed = np.clip(field * (255.0 / top), 0, 255).astype(np.uint8)
    if display.ndim == 2:
        display = np.stack([display, display, display], axis=-1)
    if _cv2 is not None:
        heat = _cv2.applyColorMap(normed, _cv2.COLORMAP_INFERNO)
        return np.ascontiguousarray(
            _cv2.addWeighted(display, 1.0 - alpha, heat, alpha, 0))
    heat = np.zeros((h, w, 3), dtype=np.uint8)
    heat[:, :, 2] = normed
    heat[:, :, 1] = np.clip(normed.astype(np.int16) - 80, 0, 255).astype(np.uint8)
    blended = display.astype(np.float32) * (1 - alpha) + heat.astype(np.float32) * alpha
    return np.ascontiguousarray(np.clip(blended, 0, 255).astype(np.uint8))
