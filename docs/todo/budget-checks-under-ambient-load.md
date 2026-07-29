---
title: A budget check gets slower the more of the suite pytest imported
status: open
priority: unassessed
serves: [A2]
opened: 2026-07-28
gated_on: >
  nothing — but the first step is a measurement of the mechanism, not a choice
  among fixes; every option written before 2026-07-28 was written against a
  cause that turned out not to be the cause
reads:
  - tests/bench/test_density_rebuild.py
  - src/sieve/bench/budgets.py
  - noxfile.py
---

# A budget check gets slower the more of the suite pytest imported

`uv run nox -s checks` fails on

    Band power arrives -> density rebuilt: 101.7 ms exceeds the 100 ms
    in-pipeline budget by 1.7 ms

with a docs-only working tree. It is not flakiness and it is not ambient load.
It is a deterministic function of **how much of the suite pytest collected**:

| Invocation | Collected | Result |
|---|---|---|
| `pytest tests/bench` | 21 | passes |
| `pytest tests/gui tests/unit <file> -k density_rebuild` | 855 | passes |
| `pytest -k density_rebuild` (full collection, one test runs) | 962 | **fails, 3/3** |
| `nox -s checks` | 962 | **fails, 2/2** |

The third row is the load-bearing one: everything else is *deselected*, so only
this test executes. Nothing runs concurrently and nothing else has run first.
The slowdown is caused by what was **imported at collection**. Overages across
the five failing runs: 7.1, 23.5, 39.9, 43.3, 44.0 ms — a 1.1x to 1.4x
systematic penalty with high variance on top, not jitter around the limit.

## Why the test is exposed to it at all

`noxfile.py:48` runs `pytest --benchmark-disable`, and the comment there is
explicit that budget checks still run under it. So
`tests/bench/test_density_rebuild.py` takes **one** `perf_counter` reading, no
repetition and no statistics, and hands it to `budgets.check()`, which raises
on any overage.

The thin margin is correct and must stay. The test's docstring makes the
argument: `B = MAX_BLOCKS` is the worst case the Block control still admits,
and "a benchmark at a comfortable block size would pass forever and protect
nothing." Testing it anywhere other than the edge defeats the producer rule 4
requires for `gui/density_plot.MAX_BLOCKS`.

**Best-of-N does not fix this**, and it was the original recommendation. The
minimum is the right statistic for a disturbance that only *sometimes* adds
time; here every reading in a full run is inflated, so the minimum is inflated
too. It would have made the test pass on some machines and left it failing on
others — worse than the current honest failure, because it would look fixed.

## Why this outranks one failing test

Rule 6 in its gate form. A miss that fires for reasons unrelated to the change
under test is a result that looks better-founded than it is, and the cost is
not the rerun — it is that a budget which cries wolf gets read as noise. The
next real regression at 103 ms is indistinguishable from this one, and by then
the habit of rerunning until green is established. `IN_DEBT` exists so a
*known* miss is declared rather than tolerated silently; a miss that is neither
real nor declared is the case the machinery does not cover. And CI runs
`nox -s checks benchmark`, so this reports a regression that did not happen, on
the shared branch, to whoever pushed next.

## The measurement to take first

What does importing the remaining ~100 test modules change for a NumPy
`bincount`-per-frame loop? Two candidates worth checking in order:

1. **Thread-pool or BLAS/OpenMP configuration set as an import side effect.**
   `cv2` and `scipy` both do this, and
   `docs/findings/2026.07.27-scipy-fft-workers-does-nothing-here.md` already shows
   this repo's threading assumptions failing silently.
2. **Working-set growth** from the imported modules degrading cache locality.

The result is a finding, and it decides the fix rather than the reverse. If the
cause is an import side effect, the fix is to neutralise it in the fixture and
the budget keeps its stated number; if it is working set, the honest answer is
a declared regime distinction with the two regimes distinguishable in the
failure message — never a silently weaker budget wearing the same number.

## Scope

Audit every budget assertion running under `--benchmark-disable`, not just this
one. `test_density_rebuild.py` is the instance that fired and is unlikely to be
the only single-shot wall clock in the gate. The collection-size result widens
the audit in the other direction too: ask whether any *passing* budget check is
passing only because it runs in a small collection.
