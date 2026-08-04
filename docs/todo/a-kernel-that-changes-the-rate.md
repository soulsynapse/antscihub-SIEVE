---
title: A kernel that changes the rate
status: deferred
opened: 2026-07-29T12:18:58-07:00
priority: normal
gated_on: >
  a decimator somebody needs — the rate arithmetic (output_rate as exact
  Fraction, input_warmup_frames, the monotone fold) is fully built and
  reachable by no filter, and building execution for it without a consumer
  would repeat the GPU machinery's mistake
after: [a-kernel-that-sees-a-span]
reads: [src/sieve/core/filter_base.py, src/sieve/pipeline/plan.py]
---

# A kernel that changes the rate

`rate_changing` execution. The arithmetic exists and is property-tested; what
is missing is the executor running a node whose output rate is not its input
rate, and the first filter that needs it.

The obligation that must land inside the same filter, not beside it: a
temporal decimator carries its own anti-alias lowpass, because decimating
without one folds high-frequency behaviour into the measured band disguised
as something slower — rule 6 through arithmetic (the standing obligation
recorded in ARCHITECTURE.md rule 6's list). The refusal in
`unrunnable_reason` shrinks by `rate_changing` when this lands.
