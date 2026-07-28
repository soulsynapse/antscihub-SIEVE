---
title: A one-shot wall clock in the correctness gate
status: open
serves: [A2]
opened: 2026-07-28
gated_on: >
  nothing structurally — but the fix is a decision about how a budget is
  adjudicated, not a threshold to nudge, so it should not be taken as a
  one-line tolerance bump
reads:
  - tests/bench/test_density_rebuild.py
  - src/sieve/bench/budgets.py
  - noxfile.py
---

# A budget miss that was not one

Observed 2026-07-28. `uv run nox -s checks` failed on

    Band power arrives -> density rebuilt: 101.7 ms exceeds the 100 ms
    in-pipeline budget by 1.7 ms

with a docs-only working tree. The same test passed three times in isolation
immediately afterwards and the full gate passed on rerun. Nothing regressed;
the machine was busy.

## Why this one is exposed

`noxfile.py:48` runs `pytest --benchmark-disable`, and the comment there is
explicit that budget checks still run under it. So
`tests/bench/test_density_rebuild.py` takes **one** `perf_counter` reading,
with no repetition and no statistics, and hands it to `budgets.check()`,
which raises on any overage at all.

The margin is thin by design and correctly so. The test's own docstring makes
the argument: `B = MAX_BLOCKS` is the worst case the Block control still
admits, and "a benchmark at a comfortable block size would pass forever and
protect nothing." The bound is the producer rule 4 requires for
`gui/density_plot.MAX_BLOCKS`. Testing it anywhere other than the edge would
defeat it.

So the two halves are both right and they collide: the measurement must sit
at the edge of the legal range, and a single reading at the edge of the range
is decided by ambient load as much as by the code.

## Why it matters more than one flaky test

Rule 6, in its gate form. A miss that fires for reasons unrelated to the
change under test is a result that looks better-founded than it is, and the
cost is not the rerun — it is that a budget which cries wolf gets read as
noise. The next real regression at 103 ms is indistinguishable from this, and
by then the habit of rerunning until green is established. `IN_DEBT` exists
so that a *known* miss is declared rather than tolerated silently; a miss
that is neither real nor declared is the case that machinery does not cover.

It also undercuts the guardrail's own claim. `docs/AUTO-GUARDRAILS.md` says
which gates actually run in CI, and `.github/workflows/ci.yml` runs
`nox -s checks benchmark`. A CI job that fails on a busy runner reports a
regression that did not happen, on the shared branch, to whoever pushed next.

## Options

1. **Best-of-N in the non-benchmark regime.** Take the minimum of a few
   readings when `--benchmark-disable` is in force. The minimum is the right
   statistic for "can this machine do it in the budget" — ambient load can
   only add time, never subtract it — and it costs a few hundred ms of gate
   time. Keeps the edge-of-range shape intact.
2. **Move the timed half to `nox -s benchmark` only.** Cheapest, and wrong
   for the reason the test's docstring already gives: the bound then goes
   unchecked in the gate that actually runs on every change, which is
   precisely where a widget's refusal threshold should not become a magic
   number again.
3. **A declared tolerance for the disabled-benchmark regime** — the budget
   holds at its stated limit under `benchmark`, and admits a stated slack
   under `checks`. Honest only if the slack is written down as such and the
   two regimes are distinguishable in the failure message; otherwise it is a
   silently weaker budget wearing the same number.

**Recommendation: (1).** It is the only one that keeps the budget's stated
limit, keeps the check in the gate that runs on every change, and removes the
failure mode rather than relabelling it. The minimum-of-N argument is also
the one that generalises — any other budget check running single-shot under
`--benchmark-disable` has the same exposure, and the sweep for those is part
of this item.

## The diagnosis above is wrong, and the recommendation follows it (2026-07-28)

Reproduced during the aspirations work, again with a docs-only tree, and it is
not ambient load. It is a function of **how much of the suite pytest has
collected**, and it is deterministic:

| Invocation | Collected | Result |
|---|---|---|
| `pytest tests/bench` | 21 | passes |
| `pytest tests/gui tests/unit <file> -k density_rebuild` | 855 | passes |
| `pytest -k density_rebuild` (full collection, one test runs) | 962 | **fails, 3/3** |
| `nox -s checks` | 962 | **fails, 2/2** |

The third row is the load-bearing one: everything else is *deselected*, so only
this test executes. Nothing is running concurrently and nothing else has run
first. The slowdown is caused by what was **imported at collection**, not by
contention with other tests and not by the machine being busy. Overages across
the five failing runs: 7.1, 23.5, 39.9, 43.3, 44.0 ms — a 1.1x to 1.4x
systematic penalty with high variance on top, not a jitter around the limit.

Two consequences:

- **Best-of-N does not fix this.** The minimum is the right statistic for a
  disturbance that only ever adds time *sometimes*; here every reading in a
  full run is inflated, so the minimum of N is inflated too. Option (1) would
  have made the test pass on some machines and left it failing on others, which
  is worse than the current honest failure because it would look fixed.
- The original 1.7 ms observation was probably the same effect near its floor,
  not a busy machine — which means "passed three times in isolation
  immediately afterwards" was never evidence of a flake. It was the partial-
  collection case, and it was reproducing the *passing* condition.

The open question is now mechanistic and worth a finding rather than a guess:
what does importing the remaining ~100 test modules change for a NumPy
`bincount`-per-frame loop? The candidates worth checking first are thread-pool
or BLAS/OpenMP configuration set as an import side effect (`cv2` and `scipy`
both do this, and `scipy.fft's workers argument does nothing in this build`
is a finding that already shows this repo's threading assumptions failing
silently), and working-set growth from the imported modules degrading cache
locality. Measure before choosing an option; the three above were all written
against a cause that is not the cause.

## Scope

Audit every budget assertion that runs under `--benchmark-disable`, not just
this one. `test_density_rebuild.py` is the instance that fired; it is
unlikely to be the only single-shot wall clock in the gate. The collection-size
result above widens this: the audit should also ask whether any *passing*
budget check is passing only because it runs in a small collection.
