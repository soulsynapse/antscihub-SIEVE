---
title: Annotation spans, and the accuracy feedback they unlock
status: deferred
serves: [A3]
gated_on: >
  a detector whose output is worth correcting by hand, or a labelling task that
  needs ground truth before one exists
reads:
  - ../antscihub-optical-flow-detector/gui/marks_store.py
  - src/sieve/core/detection.py
  - docs/REFINED-VISION.md
---

# Annotation spans on the timeline

**Why not now.** There is no marks model, no labelled-span sidecar, and no UI
that could create one. It is downstream of the deferred **Coverage and
detection lanes** item, docs/todo/coverage-and-detection-lanes.md, for a
practical reason as well as a temporal one: in V1 the way a span gets created is
"commit these detections as marks", so the detector is what makes the annotation
layer worth having rather than a drawing tool nobody uses.

**What would make it the right time.** A detector whose output is worth
correcting by hand, or a labelling task that needs ground truth before one
exists. VISION's classification work is the likely trigger.

**The design constraint worth recording now**, because it is the one V1 got
wrong first and fixed at cost: a mark belongs to a **replicate**, not to the
video. A span is one region's answer. V1 wrote every region into one
`Foo.marks.json` keyed by label, so saving a label from region 3 replaced region
2's provenance for that label. The palette is the exception and stays per-clip —
one behaviour label should be one colour across every replicate in a source,
which is a display contract about the clip and not about the region.

## Why the labels are worth the trouble: accuracy feedback

Folded in from a separate entry 2026-07-28, because it shared this trigger
exactly and reading it as a rendering detail of the annotation layer is the
only way to get it wrong.

VISION steps 4 and 5 build an elaborate feedback loop about **cost** — the
benchmark summary, the graph HUD, the per-operation expense, the compaction
prompt. There is nothing anywhere about whether a parameter change made
detection *better*. A user drags a threshold and learns exactly what it cost
and nothing about what it caught. That is the deepest gap between VISION as
written and a tool that produces defensible results.

One hand-labelled window is enough, not a corpus: the gap between no accuracy
signal and a noisy one is far larger than the gap between noisy and good. And
the answer is cheaper than it sounds — the detection threshold is a slider and
the score series behind it is already cached, so sweeping the threshold across
a labelled window and drawing the precision/recall curve is one pass over an
array the system already holds, in a widget `gui/band_plot.py`'s family already
draws. The user reads the optimum off a curve instead of hunting for it.

The replicate-scoped constraint above applies to the curve too, and a second
one with it: a curve computed over labelled spans must never be drawn as
though it covered unlabelled ones — the unexamined-versus-quiet collapse the
deferred **Coverage and detection lanes** item,
docs/todo/coverage-and-detection-lanes.md, names as V1's standing failure,
arriving through a different widget.

Read: V1 `../antscihub-optical-flow-detector/gui/marks_store.py`,
`src/sieve/core/detection.py`, `docs/REFINED-VISION.md` **F**.
