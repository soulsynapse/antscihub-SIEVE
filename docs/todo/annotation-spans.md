---
title: Annotation spans on the timeline
status: deferred
gated_on: >
  a detector whose output is worth correcting by hand, or a labelling task that
  needs ground truth before one exists
reads:
  - ../antscihub-optical-flow-detector/gui/marks_store.py
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

Read: V1 `gui/marks_store.py`.
