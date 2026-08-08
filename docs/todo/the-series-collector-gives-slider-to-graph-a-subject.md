---
title: The series collector gives slider_to_graph a subject
step: "06.6"
status: done
gated_on: nothing
done_when: "uv run pytest tests/bench/test_loop_budget.py tests/bench/test_budget_producers.py -q && uv run python -c \"from sieve.bench.budgets import TIMED, WITHOUT_PRODUCER; assert 'slider_to_graph' in TIMED and 'slider_to_graph' not in WITHOUT_PRODUCER\""
opened: 2026-08-07
---

# The series collector gives slider_to_graph a subject

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

## Ruled 2026-08-08 — the collector lands here, and this is the step

The plan revision that put Phase 7 ahead of the rest of 5 and 6 answered the
decision above the only way it could: the first cut's whole capability is a
param tuned with the graphs refilling inside the budget, so the collector has a
consumer either way, and the only question left was whether its first number is
taken headless or through Qt. Taken through Qt it is unattributable, which is
what Phase 6 exists to prevent. So it is a Phase 6 deliverable, this item is the
step that carries it, and `PLAN.md`'s Phase 6 now says so in its own words.

That closes the second branch: the gate is not amended down. `slider_to_graph`
moves from `budgets.WITHOUT_PRODUCER` into `budgets.TIMED` and the phase meets
the gate it stated.

## Reviewed 2026-08-08 — the criterion could not have failed, and now can

The two files the criterion named are bidirectional consistency guards: they
assert that `WITHOUT_PRODUCER` and `TIMED` equal what a scan of the tree finds,
which is true of a tree with no collector and true again of a tree with one.
The command was green on the unbuilt tree, so it could only ever have certified
work nobody did — recorded in
[findings/loop/2026.08.08-a-consistency-guard-as-a-criterion-is-green-on-both-sides-of-the-work.md](../findings/loop/2026.08.08-a-consistency-guard-as-a-criterion-is-green-on-both-sides-of-the-work.md).
The `done_when` now carries the membership check the section above already
states in prose, and is red until it is true.

The guards make the rest follow: `TIMED` may only name a key some `within_budget`
call site in `tests/bench/` passes, so the criterion cannot go green without the
benchmark, and the benchmark cannot be honest without the collector to measure.
What the criterion still does not carry is non-vacuity of the new gate's sample
count — every gate in `test_loop_budget.py` asserts on the number of samples it
judged, and this one owes the same.
