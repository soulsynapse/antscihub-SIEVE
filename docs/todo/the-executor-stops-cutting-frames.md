---
title: The executor stops cutting frames
status: open
opened: 2026-07-29
priority: normal
gated_on: nothing
after: [the-graph-carries-the-crop-the-span-and-the-detector]
reads: [src/sieve/pipeline/executor.py, src/sieve/pipeline/plan.py]
---

# The executor stops cutting frames

Demolition, first tranche — everything the flip stranded on the crop/span
side, each row unreachable and therefore a deletion with a green suite:
`plan.roi`, the executor's crop branch and `pre_cropped`,
`FrameResult.source_cropped` and the `source`/`source_cropped` pair that
existed only because the crop was a special case, and the last of the
`Replicate | None` propagation through `ExecutionPlan.build`, `resolved_*`,
and the target helpers.

The one judgment call: `FrameResult.source_cropped` is also the cited
precedent for provenance flags ("a value that could be either says which").
The *principle* moved to `a-number-says-how-it-was-founded`; the field can
go.
