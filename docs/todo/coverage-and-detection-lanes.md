---
title: Coverage and detection lanes on the timeline
status: deferred
priority: unassessed
gated_on: >
  the executor recording, per replicate and per frame, that it ran and under
  which resolved params
reads:
  - ../antscihub-optical-flow-detector/gui/explorers/detection_timeline.py
  - ../antscihub-optical-flow-detector/gui/track_store.py
---

# Coverage and detection lanes on the timeline

**Why not now.** Nothing in this repo records what was examined or what was
found. `pipeline/` is `cache`, `cache_key`, `dag`, `executor`, `plan`; the
executor returns frames and writes cache entries, and neither is a claim about
coverage. Painting these lanes before a producer exists means inventing a
coverage model against zero data, and the one thing this layer must not get
wrong is precisely the thing an invented model would guess at — see below.

**What would make it the right time.** The executor recording, per replicate and
per frame, that it ran and under which resolved params. That is the trigger, and
it is also the smaller half of the work: the arrays are four per replicate
(`measure`, `gate`, `covered`, `current`), and everything here is a rendering of
them.

**The rule the layer exists to enforce, which is not a rendering detail.** Three
claims must never look alike:

- **unexamined** — nobody computed this stretch. A bare trough, no baseline
  rule, visibly *empty* rather than dark.
- **examined and quiet** — computed, and the answer was nothing. The baseline
  rule is lit, so "we looked" is visible independently of what was found.
- **examined under settings no longer in force** — desaturated, *not* dimmed. A
  dim red still reads as a weak detection; a gray one reads as a detection that
  is not being claimed.

V1's `detection_timeline.py` names the first two collapsing as the standing
failure of that codebase: a strip that paints unfilled regions the same colour
as a computed zero turns "nobody looked here" into "nothing happened here",
which is a false negative wearing the costume of a result.

**Two things in V1 that are decisions, not drawing.** A screen column is claimed
covered only if *every* frame in it is — `minimum.reduceat`, so a column
straddling a live frontier reads partly-unexamined rather than examined. And bar
height is `log1p` normalised over covered frames only, because the measure is a
count with a heavy tail: against a linear axis one large event sets the maximum
and every ordinary event below it draws one or two pixels tall, which is
indistinguishable from examined-and-quiet — the same collapse, arriving through
the axis instead of through the palette.

Carries a readout: "47% of the clip examined · 3 detections · 1.2 s detected ·
30 s under other settings", and a legend, because none of the above is legible
without one.

Read: V1 `../antscihub-optical-flow-detector/gui/explorers/detection_timeline.py`,
`../antscihub-optical-flow-detector/gui/track_store.py`.

---

## Detection ticks came here on 2026.07.27, and why

Item 8 of `docs/filter-tab-parity-plan.md` was split that day: the bracket and
the hover bubble stayed in the seeker item
(`docs/completed-todo/2026.07.27-seeker-upgrades.md`), and **detection
ticks and the `|<` / `>|` jumps moved here**, because they share this item's
trigger rather than the seeker's absence of one.

Ticks look free and are not. Detections exist only over the **working window**:
`gui/series_collector.py`'s frame axis is the rendered span's, `execute` yields
only frames at or after `plan.span.start`, and nothing anywhere persists a
detection outside the span currently rendered. A strip painting ticks from that
would show them across the ten seconds under the window and nothing across the
other twenty minutes — which reads as *no detections there*.

That is this item's own rule failing through a third route. The two collapses
already named above arrive through the palette and through the axis; this one
arrives through the **extent of the record**, and it is the same false negative
in the same costume. So ticks do not ship before coverage: the unexamined
stretch must be visibly empty at the moment the first tick is drawn, or the
first tick is a lie about everywhere it is not.

Both are downstream of one thing — the executor recording, per replicate and
per frame, that it ran and under which resolved params. That is already this
item's `gated_on` line, unchanged; ticks are a fifth array off the same record
(`detected`, beside `measure`, `gate`, `covered`, `current`), not a second
subsystem.

Two constraints for tick rendering, both from the mockup contract in
`docs/filter-tab-parity-plan.md` §Seeker: ticks are floored to 1 px so a
one-frame detection stays visible at any zoom, and green remains a status
colour used for nothing else. The variant is settled as `lanes`, so ticks share
the strip's top edge with the window header — watch that seam, since the seeker
mockup flagged it as possibly too crowded before it was deleted on 2026.07.27
(`docs/completed-todo/2026.07.27-seeker-upgrades.md`).
