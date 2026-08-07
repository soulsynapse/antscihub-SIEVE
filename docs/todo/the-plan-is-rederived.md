---
title: The execution plan is re-derived
step: "03.5"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_plan.py -q"
opened: 2026-08-07
---

# The execution plan is re-derived

`pipeline/plan.py` re-derived against schema v1 and the two-sided window.
`tests/unit/test_plan.py` holds **14 cases in 6 classes**, and this item's
table has 14 rows.

This is where Phase 1's lookahead contract first has consequences. v2's
`_lead_in` walks the graph summing `input_warmup_frames` because a v2 window
only ever trailed; a v3 window has two sides, so the frames a node needs
before its first emission and the frames it needs after are both real and the
selected range is widened at both ends. The executor honours it by delaying
emission (03.6); this item is where the arithmetic is decided, and a case
that asserts a one-sided lead-in is *replaced by* a named v3 case rather than
dropped — the subject survives, the claim changes.

`CostEstimate` is not here: Phase 1 cut it and its consumer is VISION's
process screen, so a case whose subject is a cost estimate is *dropped*
citing `adr/declared-means-verified.md`. `Backend` and `LoweredPrefix` are
dropped the same way, on the decisions named in 03.3.
