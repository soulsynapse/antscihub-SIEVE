---
title: The graph carries the crop, the span, and the detector
status: open
opened: 2026-07-29
priority: high
gated_on: nothing
after: [the-crop-is-a-filter, the-span-is-a-filter, detection-is-a-filter, gui-cli-execution-parity]
reads: [src/sieve/core/pipeline_model.py, src/sieve/gui/commands.py]
---

# The graph carries the crop, the span, and the detector

**The one migration** — the second of REWORK.md's ordering constraints, and
the repo's first *destructive* schema change: every bump v1→v5 was
additive-with-a-default, so this is also the first real upgrade function.
Schema v6: a `model_validator(mode="before")` on `Project` that, for incoming
documents `< 6`, synthesizes a crop node at every root from `Replicate.roi`,
a span node from `Project.clip`, and a detect node from `Project.detector` /
`Replicate.detector_overrides`, then drops the four fields from the model.
`Replicate | None` collapses — "no crop" is a full-frame ROI on a present
node. GUI commands write nodes from here on.

Why `gui-cli-execution-parity` is in `after:` and must stay there (the fourth
ordering constraint): this commit's failure mode is a **plausible frame** — a
synthesized crop node in the wrong coordinate numbering, a span node off by
the lead-in `decode_range` used to absorb — and the parity diff is the only
instrument that can see it. Landed after the flip it can only confirm both
front ends agree about the same wrong thing.

The two tests that convert plausible into failing, both in this item:

- a checked-in v5 fixture with `roi`, `clip`, and `detector` all populated,
  and an upgrade test pinning the synthesized graph exactly;
- an equivalence test: the v5 document's rendered output, committed as a
  fixture from the pre-flip executor, diffed frame-for-frame against the v6
  document through the new one.

Demolition of the code paths the flip strands (`plan.roi`, `_crop`,
`DetectorState`, `sieve detect`) is **not** this commit — each is a separate
deletion item with a green suite. One schema commit, staged demolition
around it.
