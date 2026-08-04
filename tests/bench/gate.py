"""How a budget is adjudicated in a gate, as opposed to what the budget is.

`sieve.bench.budgets` is the table and `check()` is the verdict on one number.
Neither knows how many numbers a test should take or what to do when the
machine is busy, and neither should: that is harness policy and it does not
ship with the application. This module is that policy, in one place, because
`docs/todo/budget-checks-under-ambient-load.md` is about the adjudication and
not about any single threshold.

**The statistic is the kind of claim, not a house style.** Two kinds live in
this suite and they take opposite statistics:

- A *capability* bound — "the largest B the density surface can be rebuilt at
  inside the budget", which is what `gui/density_plot.MAX_BLOCKS` rests on —
  asks whether the machine can do it at all. Ambient load only ever adds time,
  so the **minimum** is the reading with the least foreign work in it and every
  other sample is that one plus noise.
- A *felt latency* budget — `open_to_first_frame`, `scrub_settle` — is a claim
  about what a user experiences, and a limit only the best round meets is a
  limit missed half the time. Those take the **median**.

Getting this backwards is not a tuning error in either direction: a median on a
capability bound fails on a busy machine for no reason, and a minimum on a
latency budget passes on a machine nobody could use.

**A miss is retried before it is believed, and the limit never moves.** The
failure this exists for fired twice in the gate and did not reproduce in
isolation, and the honest reading of that is not that the budget is wrong but
that one batch of readings on a contended machine is not enough evidence to
call a regression. So a batch that misses is re-taken, up to `ATTEMPTS`, and
the best of the batches decides. This is deliberately *not* option (3) from the
item — no slack is granted and the stated limit is what is enforced. What
changes is how much evidence is required before declaring the machine cannot
meet it, and the failure message says how many attempts were spent so a real
regression still reads as one.

Retries cost nothing on the passing path, which is the ordinary path: the extra
batches only run after a miss.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from statistics import median

import pytest

from sieve.bench.budgets import BudgetMissError, check

#: Batches taken before a miss is believed. Three, because the observed
#: failures were single-digit-percent overages on a machine with other work on
#: it — one repeat is enough to clear that and a fourth is gate time spent on
#: an answer the third already gave.
ATTEMPTS = 3

#: The two statistics, named so a call site states which kind of claim it is
#: making rather than passing a bare function. See the module docstring.
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
    """Judge `statistic` of `first_batch` against `key`, re-taking a miss.

    `first_batch` is the batch pytest-benchmark already drove, so the plugin's
    own report is over the real function rather than over a stub — the
    `benchmark` session selects with `--benchmark-only`, which skips a test
    that does not use the fixture, so the fixture cannot simply be dropped.

    `resample` returns one further interval in milliseconds and is called
    `len(first_batch)` times per retry. It must be self-contained — a round
    that reuses the previous round's warmed state measures a different function
    than the budget names, which is why `test_density_rebuild.py` builds a
    fresh array per round.

    `honor_debt` defaults to True because every caller here is the gate, and
    the gate's policy is that a declared debt xfails visibly rather than
    failing: rule 4's "a miss is visible" applied to the gate's own output.

    Raises:
        BudgetMissError: if every attempt missed. Re-raised from the last
            attempt with the attempts spent appended, so a genuine regression
            is not mistaken for the contention this retry absorbs.
        KeyError: immediately, if `key` is not a budget. Not retried — an
            unknown key is a typo in the test and no number of readings makes
            it true.
    """
    # A budget is a claim about a machine, and under `-n` the machine is running
    # five other workers. The retry below absorbs contention; it cannot absorb
    # being deliberately oversubscribed, and a debt xfailed for that reason
    # reads as evidence about the code when it is evidence about the harness.
    if os.environ.get("PYTEST_XDIST_WORKER") is not None:
        pytest.skip(f"{key} is a timing budget; re-take it serially with -n0")
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
            pytest.xfail(f"{key} in declared debt ({debt.why}) — repaid by {debt.item}")
        return
