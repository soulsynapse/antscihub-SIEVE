





































from __future__ import annotations

from collections.abc import Callable, Sequence
from statistics import median

import pytest

from sieve.bench.budgets import BudgetMissError, check





ATTEMPTS = 3



BEST = min
TYPICAL = median


def within_budget(
    key: str,
    first_batch: Sequence[float],
    *,
    resample: Callable[[], float],
    statistic: Callable[[Sequence[float]], float],
    honor_debt: bool = True,
) -> None:


























    rounds = len(first_batch)
    best: float | None = None
    for attempt in range(1, ATTEMPTS + 1):
        batch = first_batch if attempt == 1 else [resample() for _ in range(rounds)]
        value = statistic(batch)
        best = value if best is None else min(best, value)
        try:
            debt = check(key, value, honor_debt=honor_debt)
        except BudgetMissError as miss:
            if attempt == ATTEMPTS:
                raise BudgetMissError(
                    f"{miss} — best of {ATTEMPTS} attempts x {rounds} rounds was {best:.1f} ms"
                ) from miss
            continue
        if debt is not None:
            pytest.xfail(f"{key} in declared debt: {debt.why}")
        return
