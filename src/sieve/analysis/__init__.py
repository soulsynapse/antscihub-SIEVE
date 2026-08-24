"""What a step produces, and the record of which positions have one.

`tool` is what a step declares before anything schedules or runs it: the form
it wants its inputs in, the offsets it admits as a set, and whether it can be
evaluated anywhere or only in order. `series` is where the answer goes — one
float per position per step over one source in one form, with coverage recorded
beside it rather than inferred from a zero, and a pts table saying what a row
means.

Nothing here decides when a value is computed or by whom. ADR-0005 settles that
— a value is recorded where its inputs landed, never on the cadence of anything
that draws — and this package is only the place the answer goes.
"""

from __future__ import annotations

from sieve.analysis.record import Recorder
from sieve.analysis.series import Series
from sieve.analysis.tool import (
    BUDGETED,
    COMMIT,
    FREE,
    FREE_RATIO,
    Tool,
    analysis_form,
    classify,
    residency,
)

__all__ = [
    "BUDGETED", "COMMIT", "FREE", "FREE_RATIO", "Recorder", "Series", "Tool",
    "analysis_form", "classify", "residency",
]
