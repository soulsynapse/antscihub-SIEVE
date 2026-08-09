---
title: A declared lag whose only reader is its own test
priority: low
phase: 8
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

## A third module in the same set, and it is not a params method

`dag.linear_order` is read by `tests/unit/test_dag.py` and by nothing under
`src/`
([finding](../findings/2026.08.09-linear-order-is-not-the-tool-stacks-redraw.md)).
It landed for a caller that was then written elsewhere: the tool stack walks
`gui/walk.node_order`, which never refuses, because a window has to render
whatever document was opened. So the pair above is no longer two modules that
happen to agree — it is three, and the third widens the question rather than
repeating it. `settle_frames` and `group_delay_frames` compute a real property
a test can measure; `linear_order` computes a real property of a graph and also
carries a *refusal* nothing can reach, which is the shape
`adr/declared-means-verified.md` is least ambiguous about. Whichever reading the
rule takes, the answer wants to cover all three at once, and this one is the
cheapest to act on: it is promoted to a front end that reads it or cut with its
cases.

## A fourth, and it is a branch rather than a symbol

`crop_serving.py`'s pair of edits each carry a no-fan-out branch — the one that
writes the record into the node's own parameters, because there is no replicate
to carry it — and no document can be in that state: `Project.with_crop` has one
caller under `src/`, `materialize_replicate`, whose `--replicate` is required,
so a project holding a crop record always has replicates
([finding](../findings/2026.08.09-the-no-fan-out-half-of-the-serving-pair-cannot-be-reached-or-killed.md)).
A mutation sweep disables either branch and the module's suite stays green.

It widens the question the same way `linear_order` did rather than repeating
it. The three above are symbols with a test and no caller; this is a branch
with neither, inside a function every front end calls — so "cut it with its
cases" has no cases to cut, and the reading that keeps it has to say what a
replicate-less served project is for. `serving_edit`'s half has been in the
tree since `b63f43f` and `unserving_edit`'s arrived in `ac29c6c` mirroring it,
which is the right way to write an inverse; the answer that covers all four is
still one answer.

The consumer, when it arrives, is an onset time leaving the process: a CSV of
detections wants its frame numbers corrected by this many frames, and the delay
matters most against a centred window, which has none of its own — mixing the
two means the latencies do not cancel and every reported onset is late. That
puts it in Phase 5 with the sinks, which is where either answer becomes
actionable: promote it to something a writer reads, or cut it and delete the
two cases that stand in for a reader.
