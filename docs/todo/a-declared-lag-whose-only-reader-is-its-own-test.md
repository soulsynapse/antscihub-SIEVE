---
title: A declared lag whose only reader is its own test
priority: low
phase: 5
status: open
gated_on: nothing
opened: 2026-08-07
---

# A declared lag whose only reader is its own test

`MotionHistoryParams.group_delay_frames()` and `.group_delay_seconds()` landed
with 04.7 because v2 had them and the ported test file has two cases on them.
Nothing else in `src/` calls either. That is the shape
`adr/declared-means-verified.md` refuses — except that the rule is written
about `ToolSpec` fields, and these are params methods computing a real property
of the kernel, which a test can measure and does: the measured centre of the
impulse response equals the declared number to 1e-3.

So the question is which of the two readings the rule takes, and it is not a
question about this tool. `settle_frames` on `background_ema` is the same shape
and was kept without anyone asking; a future tool exposing a derived quantity
with a test and no caller has no precedent to read off the tree, only two
modules that happen to agree.

The consumer, when it arrives, is an onset time leaving the process: a CSV of
detections wants its frame numbers corrected by this many frames, and the delay
matters most against a centred window, which has none of its own — mixing the
two means the latencies do not cancel and every reported onset is late. That
puts it in Phase 5 with the sinks, which is where either answer becomes
actionable: promote it to something a writer reads, or cut it and delete the
two cases that stand in for a reader.
