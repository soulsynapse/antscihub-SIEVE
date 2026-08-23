"""Drawing a tool's output at display resolution, from data reduced to it.

Every freeze in the session explorer's tuning loop traced to the
presentation layer and none to the tier stack
(`docs/findings/2026.08.22-what-froze-the-felt-loop.md`), so this folder
treats paint cost as a first-class subject rather than as whatever is left
over after the interesting work. Two rules, and a measured reason for each.

**Reduce to display resolution before drawing, once per data change.** A
series drawn into a strip is one column per pixel; drawing every point is
work for pixels that land on top of each other, and it is the 37k-point
scatter the freeze hunt found. Same for the overlay: a field drawn into a
smaller canvas resizes the *field* and colour-maps what is shown, rather
than colour-mapping at analysis size and resizing the colours. The cheaper
order is also the truer one — averaging a quantity and then colouring it is
what a colour bar claims is happening, and averaging colours is not the same
picture, by enough to see. Both halves of that are priced in
`results/01-paint-cost-*.json`, which is also where a later measurement
supersedes them.

**The live surface and the report surface are different code.** A
rasteriser costs enough per refresh to matter against a frame budget and the
reductions below cost effectively nothing (same result file). Moving Agg off
the GUI thread — the fix that stopped the 150-400 ms hiccups — keeps it out
of the event loop but leaves the work running, which in this folder means
the graph renderer is a *third consumer* contending with the sweep and the
player, and a contention number taken alongside it is partly about it. So:
live surfaces draw painter primitives over reduced arrays, and matplotlib
renders the session figure once, at save time, where its cost is free.

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

    The min/max pair rather than a mean, because a decimated mean hides
    exactly the thing a tuning loop is looking for — a one-frame spike
    averaged with its eleven neighbours is a spike that never appears on
    screen, and the user is hunting events, not levels.

    Coverage travels with the values instead of being folded into them: a
    column drawn as zero because nothing was computed there and a column
    that really is zero are the same picture, which is the failure
    `docs/decode/ideas.md` records as coverage inferred from a zero. A
    caller draws the uncovered columns as absent — a gap, a hatch, a dimmer
    ink — and never as a value.
    """
    n = len(values)
    if columns <= 0 or n == 0:
        empty = np.zeros(0, dtype=np.float32)
        return {"min": empty, "max": empty, "covered": empty}
    if n <= columns:
        # always `columns` wide, never `n`. A reduction whose output length
        # depends on its input length is one every caller has to branch on,
        # and the branch is the bug: a short series drawn into a wide strip
        # indexes a mask of the wrong shape. Fewer rows than pixels means
        # each row is stretched across several columns, which is what
        # drawing a short series into a wide strip means anyway.
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
    """Blend a scalar field over the frame the user is already looking at.

    The field arrives at analysis size because that is where it had to be
    computed — a threshold or a flow taken on a downscaled image is not the
    downscale of the one taken at full size, and an overlay the user tunes
    against has to be the thing that will be committed. It is *drawn* at
    display size, which is the cheaper and the more honest order.

    `ceiling` is required rather than defaulted to the field's own maximum.
    An autoscaling overlay renormalises every frame, so a still scene looks
    exactly as active as a moving one and the display lies about the one
    quantity being tuned. A caller that does not yet know its ceiling should
    hold the frame's own maximum over a window and say so, not renormalise
    silently.
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
