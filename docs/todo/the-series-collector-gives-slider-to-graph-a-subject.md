---
title: Half of Phase 6's stated gate has no subject in the tree
status: open
phase: 6
priority: high
gated_on: nothing
opened: 2026-08-07
---

# Half of Phase 6's stated gate has no subject in the tree

`PLAN.md`'s Phase 6 gate reads "in-pipeline budgets (<100 ms slider->preview,
<200 ms slider->graph) measured headless through the preview session". 06.3
measured the first and could not reach the second: `slider_to_graph` is the
interval from a drag to a *graph* updating, and nothing in this repo assembles a
node's per-frame outputs into a series anything could draw. The key is still in
`budgets.WITHOUT_PRODUCER` and absent from `budgets.TIMED`, so the gap is
declared rather than hidden — but the phase closes claiming a gate it met half
of, and that is worth deciding rather than discovering in Phase 7.

`PLAN.md` already names the missing piece and its home: `pipeline/
series_collector.py`, under "Landing later than v2 would suggest" — "it
assembles a node's per-frame outputs into the series a graph is drawn from,
which is the plotting path and not the run path". It is the only module the plan
assigns to Phase 6 with no item attached to it.

The decision this item carries, and it should be made before the module is
written: whether a series collector in Phase 6 is a real deliverable or a
Phase-7 one that the plan mis-filed. The argument for now is the same one the
whole phase rests on — a budget measured before the GUI exists is attributable,
and after it is not, so `slider_to_graph` measured through a collector plus the
preview session is the last number Phase 7 can be held to. The argument for
later is that a collector with no plot is a declaration with no consumer, which
`adr/declared-means-verified.md` refuses; v2's collector fed a widget, and this
one would feed a benchmark and nothing else until the graph panel lands.

Whichever way it goes, the outcome is visible: either a
`within_budget("slider_to_graph", ...)` call site in `tests/bench/` with the key
moved out of `WITHOUT_PRODUCER` and into `TIMED`, or an amended Phase 6 gate in
`PLAN.md` that promises what the phase can actually measure.
`docs/findings/2026.08.07-the-loop-budget-is-met-headless.md` is the reading
that exposed the gap.
