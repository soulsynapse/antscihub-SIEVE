"""What a step produces, and the record of which positions have one.

`series` is one float per position per step over one source in one form, with
coverage recorded beside it rather than inferred from a zero, and a pts table
saying what a row means. It is the tier the storage plan named and did not
build.

Nothing here decides when a value is computed or by whom. ADR-0005 settles that
— a value is recorded where its inputs landed, never on the cadence of anything
that draws — and this package is only the place the answer goes.
"""

from __future__ import annotations

from sieve.analysis.series import Series

__all__ = ["Series"]
