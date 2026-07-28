---
title: Accuracy feedback in the tuning loop
status: deferred
after: [annotation-spans]
serves: [A3]
gated_on: >
  a marks model plus one hand-labelled window — the same trigger as the
  deferred **Annotation spans on the timeline** item
  (docs/todo/annotation-spans.md)
reads:
  - docs/todo/annotation-spans.md
  - src/sieve/core/detection.py
  - docs/REFINED-VISION.md
---

# Accuracy feedback in the tuning loop

**Why not now.** It needs labelled spans and there is no marks model — this is
strictly downstream of the deferred **Annotation spans on the timeline** item,
docs/todo/annotation-spans.md, and shares its trigger.

**Why it is worth an entry anyway**, rather than being a line in that one: it is
the deepest gap between VISION as written and a tool that produces defensible
results, and naming it separately is what stops it being read as a rendering
detail of the annotation layer. VISION steps 4 and 5 build an elaborate feedback
loop about **cost** — the benchmark summary, the graph HUD, the per-operation
expense, the compaction prompt when memory climbs. There is nothing anywhere
about whether a parameter change made detection *better*. A user drags a
threshold and learns exactly what it cost and nothing about what it caught.

**What would make it the right time.** A marks model plus one hand-labelled
window. Not a corpus — one window is enough to make the curve below draw, and the
gap between "no accuracy signal" and "a noisy accuracy signal" is far larger than
the one between noisy and good.

**The shape of the answer, which is cheaper than it sounds.** The detection
threshold is a *slider* and the score series behind it is already cached, so
sweeping the threshold across a labelled window and drawing the resulting
precision/recall or detection-error tradeoff curve is one pass over an array the
system already holds — `gui/band_plot.py`'s family draws it. The user then tunes
against a curve instead of an impression, and the parameter that maximizes F1 or
minimizes total error is *read off* rather than hunted for.

**Two constraints inherited from the items above, both of which V1 got wrong.**
Labels belong to a **replicate**, not to the video. And a curve computed over
labelled spans must never be drawn as though it covered unlabelled ones — that is
the unexamined-versus-quiet collapse the deferred **Coverage and detection
lanes** item, docs/todo/coverage-and-detection-lanes.md, names as V1's standing
failure, arriving through a different widget.

Read: the deferred **Annotation spans on the timeline** item,
docs/todo/annotation-spans.md, `src/sieve/core/detection.py`,
`docs/REFINED-VISION.md` **F**.
