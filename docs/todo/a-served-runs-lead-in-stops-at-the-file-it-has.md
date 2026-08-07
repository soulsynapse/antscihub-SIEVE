---
title: A served run's lead-in stops at the file it has
priority: high
phase: 5
status: open
gated_on: nothing
opened: 2026-08-07
---

# A served run's lead-in stops at the file it has

`plan.SOURCE_FRAME_ZERO` is the floor `decode_start` clamps at, and its comment
says Phase 5's read-back path is what makes a written crop's own start the floor
instead. 05.2 built that path and left the floor at zero, so the two disagree in
a way that only a stateful graph shows: a run served by a record spanning
`[10, 16)` whose graph declares any lead-in plans a `decode_start` below 10, and
`OffsetFrameSource.read` raises `VideoDecodeError` for a frame that is before the
file begins. Correct refusal, wrong outcome — those frames are unavailable from
*any* file, which is the same unfixable shortfall a span near frame 0 has and is
already reported by `lead_in_shortfall`.

`the-plan-is-rederived.md` dropped two v2 rows onto this: 03.5's table records
`lead_in_before_the_artifact_begins_is_a_shortfall_not_a_request` and
`a_span_beginning_before_the_artifact_clamps_rather_than_raising` as deferred to
Phase 5 rather than deleted, so their cases belong with whatever lands the floor.

05.2's own cases do not reach it — `crop` and `downsample` are both streaming and
declare no window, so nothing in `test_crop_serving.py` asks for a frame before
the span. That is why this is a separate item and not a bug in what landed: the
seam is untested rather than broken, and the case that exercises it needs a
stateful tool in the served graph.

What the floor is denominated in is `ResolvedSource.first_index`, which is the
value the read-back path already carries, so this is one argument to
`ExecutionPlan.build` and two properties reading it rather than a new concept.
