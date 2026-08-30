"""Motion history at fixed lags: how much the picture moved, over three spans.

Absolute difference against three earlier positions rather than one, weighted
by how far back each sits and taken at the maximum, so a slow drift and a fast
event are both visible in one field. Ported from
`experiments/tool-experiments/tools.py`, where it is one of the three measured
loads, and it comes over unchanged in its arithmetic.

**The admitted set is not the reach.** Lags of 30, 20 and 10 admit four
positions and span thirty-one. Every other step in this tree has the two
numbers equal, which is exactly the case that lets a scheduler trimming by the
count of inputs pass its tests and be wrong — `nodes.Step.reach` and
`nodes.Step.needs` are different questions and this is the tool that keeps them
apart.

**One product, and it is the reduction.** `motion` is the mean of the weighted
field, one number per position. The field is drawn and discarded, so it is
offered to nothing and named in no edge.

**No persistent state.** A decayed accumulator would be the same picture with
bounded state, and would be `sequential` with offsets `(0,)` — and would replay
from a checkpoint on every jump, which is the trade this tool declines.
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from sieve.contract import Tool
from sieve.contract.edges import VALUE
from sieve.contract.forms import Form
from sieve.contract.nodes import Produced, Step

#: How far back each difference is taken, longest first once negated.
_LAGS = (30, 20, 10)

#: Named once and read by both the declaration and `_field`, so a change to
#: what this admits cannot leave the arithmetic reaching for a position
#: nobody fetched.
_OFFSETS = tuple(sorted(-lag for lag in _LAGS) + [0])


def _analysis_form(rect: tuple[int, int, int, int]) -> Form:
    x, y, w, h = rect
    return Form((x, y, w, h), (w, h), "gray")


def _field(frames: dict[int, Any], row: int) -> Any:
    cur = frames[row]
    out = None
    for rank, offset in enumerate(_OFFSETS[:-1]):
        # convertScaleAbs, not `* weight`: a Python float is a double, so
        # multiplying a uint8 image by one silently promotes the whole thing.
        # This scales in the same pass and stays uint8.
        weight = (rank + 1) / len(_LAGS)
        aged = cv2.convertScaleAbs(cv2.absdiff(cur, frames[row + offset]),
                                   alpha=weight)
        out = aged if out is None else cv2.max(out, aged)
    return out


def _reduce(field: Any) -> float:
    return float(np.mean(field))


TOOLS = (
    Tool(
        name="lag mhi",
        version=1,
        role=Step(
            form_for=_analysis_form,
            offsets=_OFFSETS,
            field=_field,
            reduce=_reduce,
            produces=(Produced("motion", VALUE, dtype="float"),),
            params={"lags": "-".join(str(lag) for lag in sorted(_LAGS))},
        ),
    ),
)
