---
title: A ceiling is denominated in the dimension of what it bounds
status: open
opened: 2026-07-29T12:18:58-07:00
priority: normal
gated_on: nothing
after: [a-number-says-how-it-was-founded]
serves: A2
reads: [src/sieve/bench/budgets.py, docs/ARCHITECTURE.md]
---

# A ceiling is denominated in the dimension of what it bounds

REWORK.md R6's budget half. User-perceived latency stays in wall time;
algorithmic cost moves to work units. The algorithmic budgets then become
machine-independent and CI-gated — predicted units against measured units,
conversion never invoked — and CI stops inheriting runner-load variance,
which is `budget-checks-under-ambient-load`'s disease at the root.

**Say which half this closes.** Work units measured as a deterministic count
catch *algorithmic* regression and are blind to *implementation* regression —
a kernel touching the same elements through a cache-hostile access pattern
passes unchanged. So the wall-clock half moves to a calibration job that is
explicitly not gating, and AUTO-GUARDRAILS §4 states the split; without that,
it acquires an ENFORCED entry that covers less than it appears to, which is
the exact failure that file exists to prevent.

Only `open_to_first_frame` and `scrub_settle` stay in wall milliseconds — the
hand-written entries that never came from a fold. Once `pipeline/` publishes
a number while naming no budget key, `test_budget_producers.py`'s AST check
becomes unnecessary rather than better — retire it deliberately, in the same
commit, with the reason in the entry.

Touches the budget table in ARCHITECTURE.md and its character-exact test;
budgets can carry declared debt through the transition (`IN_DEBT`), never a
silent renumbering.
