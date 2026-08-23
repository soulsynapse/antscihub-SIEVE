"""Drawing a step's output at display resolution, from data reduced to it.

Every freeze in the session explorer's tuning loop traced to the
presentation layer and none to the tier stack, so paint cost is a subject
here rather than whatever is left after the interesting work. Two rules,
each with a measured reason that lives in `results/01-paint-cost-*.json`
rather than being quoted into this docstring where a later measurement
could not supersede it.

**Reduce to display resolution before drawing, once per data change.** A
series drawn into a strip is one column per pixel; drawing every point is
work for pixels that land on top of each other, and it is the enormous
scatter the freeze hunt found. The same for a field: resize the *field* and
colour-map what is shown, rather than colour-mapping at analysis size and
resizing the colours. The cheaper order is also the truer one — averaging a
quantity and then colouring it is what a colour bar claims is happening, and
averaging colours is a different picture by enough to see.

**The live surface and the report surface are different code.** A
rasteriser costs enough per refresh to matter against a frame period; these
reductions cost effectively nothing. Moving a rasteriser off the GUI thread
stops the hiccup and leaves the work running, which in this folder means the
renderer becomes another consumer competing with the loop, and a contention
number taken beside it is partly about it. So live surfaces draw painter
primitives over reduced arrays, and a rasteriser renders the session figure
once, at save time, where its cost is free.

Nothing here imports Qt. What these produce is arrays at display size; the
widget that blits them is the explorer's business, and keeping the split
means the reductions can be measured without a GUI.
"""

from __future__ import annotations

import cv2
import numpy as np


def to_columns(values: np.ndarray, covered: np.ndarray,
               columns: int) -> dict[str, np.ndarray]:
    """Reduce a series to one column per pixel: min, max, and how covered.

    Min and max rather than a mean, because a decimated mean hides exactly
    what a tuning loop is looking for — a one-position spike averaged with
    its neighbours is a spike that never reaches the screen, and the user is
    hunting events rather than levels.

    Coverage travels beside the values instead of being folded into them. A
    column drawn as zero because nothing was computed and a column that
    really is zero are otherwise the same picture, which is
    coverage-inferred-from-a-zero at display. A caller draws the uncovered
    ones as absent — a gap, a hatch, a dimmer ink — and never as a value.

    The result is always `columns` wide. A reduction whose output length
    depends on its input length is one every caller has to branch on, and
    the branch is the bug: a short series drawn into a wide strip indexes a
    mask of the wrong shape. Fewer positions than pixels means each is
    stretched across several columns, which is what drawing a short series
    into a wide strip means anyway.
    """
    n = len(values)
    if columns <= 0 or n == 0:
        empty = np.zeros(0, dtype=np.float32)
        return {"min": empty, "max": empty, "covered": empty}
    if n <= columns:
        take = (np.arange(columns) * n // columns).astype(np.int64)
        return {"min": values[take].astype(np.float32),
                "max": values[take].astype(np.float32),
                "covered": covered[take].astype(np.float32)}
    per = -(-n // columns)                      # ceil: columns * per >= n
    pad = columns * per - n
    vals = np.concatenate([values, np.zeros(pad, np.float32)]).reshape(columns, per)
    seen = np.concatenate([covered, np.zeros(pad, bool)]).reshape(columns, per)
    lo = np.where(seen, vals, np.inf).min(axis=1)
    hi = np.where(seen, vals, -np.inf).max(axis=1)
    frac = seen.mean(axis=1).astype(np.float32)
    blank = frac == 0
    lo[blank] = 0.0
    hi[blank] = 0.0
    return {"min": lo.astype(np.float32), "max": hi.astype(np.float32),
            "covered": frac}


def overlay(display: np.ndarray, field: np.ndarray, ceiling: float,
            alpha: float = 0.55,
            colormap: int = cv2.COLORMAP_INFERNO) -> np.ndarray:
    """Blend a scalar field over the frame already on screen.

    The field arrives at analysis size because that is where it had to be
    computed — a threshold or a flow taken on a downscaled image is not the
    downscale of the one taken at full size, and what is tuned against has
    to be what gets committed. It is *drawn* at display size, which is both
    the cheaper and the more honest order.

    `ceiling` is required rather than defaulting to the field's own maximum.
    An autoscaling overlay renormalises every frame, so a still scene looks
    exactly as active as a moving one and the display lies about the single
    quantity being tuned. A caller that does not yet know its ceiling should
    take one and hold it, saying so, rather than renormalising quietly.
    """
    if display.ndim == 2:
        display = cv2.cvtColor(display, cv2.COLOR_GRAY2BGR)
    height, width = display.shape[:2]
    if field.shape[:2] != (height, width):
        interp = cv2.INTER_AREA if field.shape[1] > width else cv2.INTER_LINEAR
        field = cv2.resize(field, (width, height), interpolation=interp)
    top = max(float(ceiling), 1e-6)
    heat = cv2.applyColorMap(
        cv2.convertScaleAbs(field, alpha=255.0 / top), colormap)
    return cv2.addWeighted(display, 1.0 - alpha, heat, alpha, 0)
