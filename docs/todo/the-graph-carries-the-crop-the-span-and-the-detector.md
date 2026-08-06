---
title: The graph carries the crop, the span, and the detector
status: open
opened: 2026-07-29T12:18:58-07:00
priority: high
gated_on: nothing
after: [the-crop-is-a-filter, the-span-is-a-filter, detection-is-a-filter, gui-cli-execution-parity]
reads: [src/sieve/pipeline/upgrade.py, src/sieve/core/pipeline_model.py, src/sieve/gui/document.py]
---

# The graph carries the crop, the span, and the detector

**The one migration** — the second of REWORK.md's ordering constraints, and
the repo's first *destructive* schema change: every bump v1→v5 was
additive-with-a-default, so this is also the first real upgrade function.

**The transform is built and proven; what is left is the flip.**
`pipeline/upgrade.py` `carry_into_graph` takes a saved document and returns one
whose graph carries the crop and the span, with the exact synthesized graph
pinned in `tests/unit/test_upgrade.py` and a frame-for-frame equivalence in
`tests/integration/test_upgrade_run.py` against a checked-in v5 fixture. So the
plausible-frame risk the ordering constraint exists to catch — a crop node in
the wrong coordinate numbering, a span node off by the lead-in — is closed
before the schema moves at all.

Two things the item as first written asked for and cannot have; the argument is
`docs/findings/2026.08.05-three-things-the-graph-migration-cannot-do-as-
written.md` and it is worth reading before re-proposing either:

- **Not a `model_validator(mode="before")` on `Project`.** Synthesizing a node
  means naming a filter, and `core/pipeline_model.py` is deliberately blind to
  the registry — a validator there fails
  `test_filter_id_spelling.py` and costs three permanent entries on a
  shrink-only list. The upgrade sits in `pipeline/`, which means **the v6
  reader does too**: something above `sieve.filters` has to upgrade the mapping
  before `Project` ever sees it, and both front ends have to go through that
  one thing. Deciding where that lives is this item's first step and its only
  genuinely open design question.
- **Not the detector.** `detect_cpu` is trailing and per-target; a saved
  `detector` field means centered whole-record semantics, and substituting one
  for the other is exactly what `detection-is-a-filter` settled against. So
  `Project.detector` and `Replicate.detector_overrides` stay on the model
  through this commit and leave in `the-detector-node-is-centered`, which
  `carry_into_graph` refuses by name until then.

That splits REWORK.md's "the saved-graph changes land as one schema migration,
not four" into two, and the split is forced rather than chosen — one of the four
cannot land at any date until a windowed kernel can express centered semantics.
**The constraint wants revising or explicitly excepting; that is Kendrick's
call, not this item's.**

So what this commit does: bump to schema 6, drop `Replicate.roi` and
`Project.clip` from the model, route every reader through the graph, and make
the GUI write nodes. The blast radius is the reason this is still a whole item
rather than a follow-up — `Replicate.roi` is read in eleven modules and
`ReplicateSet` is the GUI's live geometry, so `gui/document.py`'s gesture,
fitting and lock half, `video_view.py`, `replicate_table.py`, `crop_tools.py`,
`pipeline/crop_binding.py`, `materialize.py` and `CropArtifact.backs` all move
to reading a crop node's resolved region. `Replicate | None` collapses with it:
"no crop" is a full-frame ROI on a present node.

`Project.crops` is the one strand `carry_into_graph` leaves untouched and this
commit must not: `CropArtifact.backs` matches on `replicate.roi`, so the record
that says which file already holds an arena's pixels stops matching the moment
the field goes.

Demolition of the code paths the flip strands (`plan.roi`, `_crop`) is **not**
this commit — `the-executor-stops-cutting-frames` is that, with a green suite.
