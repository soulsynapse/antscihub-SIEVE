---
title: The span is a filter; the decode range is an optimization
status: open
opened: 2026-07-29T12:18:58-07:00
priority: normal
gated_on: nothing
after: [the-crop-is-a-filter]
reads: [src/sieve/pipeline/plan.py, src/sieve/core/pipeline_model.py]
---

# The span is a filter; the decode range is an optimization

Which frames are in the answer is *what the result is* (hashed); pushing the
predicate down to the reader is *how fast it arrives* (never hashed) — the
span sits exactly on rule 7's line and this item puts each half on its side.
`src/sieve/filters/span.py`, with the planner's existing pushdown preserved:
`ExecutionPlan` already widens the span by `lead_in` into `decode_range`, and
that stays a planner optimization over an unchanged filter semantics.

Schema untouched, same as the crop item; reachable via `sieve run` on
hand-built YAML; the GUI keeps writing `Project.clip` until the flip.
