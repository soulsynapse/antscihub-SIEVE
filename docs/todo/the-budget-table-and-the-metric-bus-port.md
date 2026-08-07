---
title: The budget table and the metric bus port verbatim
step: "06.1"
status: done
gated_on: nothing
done_when: "uv run pytest tests/bench/test_budget_table.py tests/bench/test_budget_debt.py tests/bench/test_budget_producers.py tests/unit/test_metrics.py -q"
opened: 2026-08-07
---

# The budget table and the metric bus port verbatim

`bench/budgets.py` and `bench/metrics.py` byte-identical modulo imports
(PLAN.md, porting discipline). The two-regime table is the numbers the whole
value proposition is stated in — <100 ms slider to preview, <200 ms slider to
graph — and v2's pin test is character-exact on purpose: a budget that can be
edited to match a measurement is not a budget. Port the pin test first and do
not touch its expected string.

`bench/retention_trace.py` is not in this item and has no disposition in
PLAN.md; leave it where it is rather than sweeping it in because it sits in
the same package.

Nothing measures anything yet — 06.3 is the measurement. This item is the
table and the bus that carries the readings, landing before there is a
reading so the numbers cannot be chosen after the fact.
