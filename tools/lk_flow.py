"""Lucas-Kanade optical flow: sparse feature tracking between consecutive frames.

Detects corners in the previous frame with Shi-Tomasi (`goodFeaturesToTrack`),
tracks them to the current frame with pyramidal Lucas-Kanade
(`calcOpticalFlowPyrLK`), and reports displacement magnitudes — scattered onto
the image grid as a field, and averaged over successfully tracked points as a
reduction.

**Sparse where DIS is dense.** Each point is tracked individually through the
pyramid; the field carries magnitudes only at those points and zeros elsewhere.
The reduction counts only tracked points, so a mostly-static scene with a few
moving features produces a meaningful signal rather than one diluted by the
zero background.

**One product, and it is the reduction.** `flow` is the mean magnitude over
tracked points, one number per position. The field is drawn and discarded, so
it is offered to nothing and named in no edge — the contract's reasoning is on
`nodes.Step`.

**No persistent state.** `goodFeaturesToTrack` and `calcOpticalFlowPyrLK` are
both stateless calls — no solver object, no thread-local instance. Two threads
calling `field` concurrently share nothing.
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from sieve.contract import Tool
from sieve.contract.edges import VALUE
from sieve.contract.forms import Form
from sieve.contract.nodes import Produced, Step

_MAX_CORNERS = 500
_QUALITY = 0.01
_MIN_DIST = 7
_WIN_SIZE = 15
_MAX_LEVEL = 2

#: named once and read by both the declaration and `_field`, so a change to
#: what this admits cannot leave the arithmetic reaching for a row nobody
#: fetched. The previous position and the one being computed.
_OFFSETS = (-1, 0)


def _analysis_form(rect: tuple[int, int, int, int]) -> Form:
    x, y, w, h = rect
    return Form((x, y, w, h), (w, h), "gray")


def _field(frames: dict[int, Any], row: int) -> Any:
    prev = frames[row + _OFFSETS[0]]
    curr = frames[row]
    h, w = curr.shape[:2]
    pts = cv2.goodFeaturesToTrack(
        prev, maxCorners=_MAX_CORNERS, qualityLevel=_QUALITY,
        minDistance=_MIN_DIST, blockSize=7,
    )
    if pts is None:
        return np.zeros((h, w), dtype=np.float32)
    tracked, status, _ = cv2.calcOpticalFlowPyrLK(
        prev, curr, pts, None,
        winSize=(_WIN_SIZE, _WIN_SIZE), maxLevel=_MAX_LEVEL,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03),
    )
    good = status.ravel() == 1
    if not np.any(good):
        return np.zeros((h, w), dtype=np.float32)
    p0 = pts[good].reshape(-1, 2)
    p1 = tracked[good].reshape(-1, 2)
    mag = np.sqrt(np.sum((p1 - p0) ** 2, axis=1))
    out = np.zeros((h, w), dtype=np.float32)
    xs = np.clip(p0[:, 0].astype(np.intp), 0, w - 1)
    ys = np.clip(p0[:, 1].astype(np.intp), 0, h - 1)
    np.maximum.at(out, (ys, xs), mag)
    return out


def _reduce(field: Any) -> float:
    nonzero = field[field > 0]
    return float(np.mean(nonzero)) if nonzero.size else 0.0


TOOLS = (
    Tool(
        name="lk flow",
        version=1,
        role=Step(
            form_for=_analysis_form,
            offsets=_OFFSETS,
            field=_field,
            reduce=_reduce,
            produces=(Produced("flow", VALUE, dtype="float"),),
            params={
                "corners": _MAX_CORNERS,
                "quality": _QUALITY,
                "min_dist": _MIN_DIST,
                "win": _WIN_SIZE,
                "levels": _MAX_LEVEL,
                "cv2": cv2.__version__,
            },
        ),
    ),
)
