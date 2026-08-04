---
title: Name the fold, and give the combining rule to whoever fixes the strategy
status: open
opened: 2026-07-29T12:18:58-07:00
priority: low
gated_on: nothing
after: [ceilings-in-the-dimension-they-bound, a-kernel-that-sees-a-span]
reads: [src/sieve/core/filter_base.py, src/sieve/pipeline/plan.py]
---

# Name the fold, and give the combining rule to whoever fixes the strategy

Four instances of *declare per-node → compose over an axis → judge* exist or
are landing: `stored_bytes_ratio` over the graph, warmup over the chain, plan
cost over the graph, detection intervals over time. Four is enough for a
named reduction in `pipeline/` with the composition rule as a parameter.

The critical detail, learned the hard way in the old draft: **the combining
rule is not a graph property.** Sequential execution sums along the path;
parallel branches take the critical path; frame-pipelined execution is
bounded by the max over stages. So the rule belongs to whatever fixes the
execution strategy — `ExecutionPlan` if it does — and a fold placed where
the executor decides later is correct only for the sequential case. Calling
cost composition "the same fold `source_warmup_frames` gets" was the draft's
overreach; do not repeat it.
