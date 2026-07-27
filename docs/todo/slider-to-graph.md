---
title: "`slider_to_graph`, which is gated on there being a slider"
status: deferred
gated_on: >
  a parameter control bound to a node — VISION step 4's "information on the
  specific filter applied", the panel beside the operations list
reads:
  - src/sieve/gui/preview_runner.py
  - src/sieve/core/filter_base.py
  - src/sieve/bench/budgets.py
  - docs/VISION.md
---

# `slider_to_graph`, which is gated on there being a slider

**Why not now.** The budget is "Slider drag → graph update" (200 ms), and
nothing in the GUI edits a parameter. `ReplicateDocument` holds the graph and
`set_pipeline` is the one write, but every caller of it is a project load —
there is no widget anywhere that changes a node's params, so there is no drag
for the ceiling to describe. `gui/preview_runner.py` would publish it in one
line and the line would never run.

This is deliberately *not* faked by publishing the key from something adjacent.
A graph re-render triggered by the working window moving is a real interval and
is not this one: the window change decodes frames the store does not have, and
the drag this budget names is supposed to decode nothing at all
(`pipeline/preview.py`). Putting window moves into the series would make a
200 ms ceiling look generous by measuring the wrong gesture.

**What would make it the right time.** A parameter control bound to a node —
VISION step 4's "information on the specific filter applied", which is the panel
beside the operations list. `core/filter_base.py` already declares
`primary_params`, which is what such a panel would build itself from, so the
gating is the widget and not the contract. `filter_to_first_tick` has a producer
as of `gui/preview_runner.py` and this is the last in-pipeline budget without
one.

**What it involves.** The panel reads `FilterSpec.primary_params` and the params
model's fields, writes through `Project.with_param_edit` so the edit lands as
the two writes that method already performs, and pushes a `QUndoCommand` like
every other document mutation. The render it triggers is
`PreviewRunner.request_render`, unchanged — the coalescing and the abandon rule
are already written against a caller that submits faster than renders finish.

Read: `src/sieve/gui/preview_runner.py`, `src/sieve/core/filter_base.py`
`primary_params`, `src/sieve/bench/budgets.py` `slider_to_graph`,
`docs/VISION.md` step 4.
