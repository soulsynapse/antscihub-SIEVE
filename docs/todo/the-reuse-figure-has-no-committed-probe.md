---
title: The reuse figure the loop budget rests on is produced by no committed probe
phase: 6
priority: normal
status: open
gated_on: nothing
done_when: "uv run pytest tests/bench/test_loop_budget.py -k reuse_on_a_post_edit_render -q && uv run pytest tests/bench/test_loop_budget.py -k stack_share_of_a_refill -q"
opened: 2026-08-08
---

# The reuse figure the loop budget rests on is produced by no committed probe

`docs/findings/2026.08.07-the-loop-budget-is-met-headless.md` carries a reuse
row — node outputs recomputed against node outputs served, on a post-edit window
render — and it has been measured three times by three sessions, each from a
scratch file it deleted afterwards. Nothing in the tree produces it, so no review
can check it and every future change to the admission rule re-orders the same
hand-built harness ([findings/loop/2026.08.08-a-number-an-item-orders-re-measured-is-taken-by-a-probe-the-tree-does-not-hold.md](../findings/loop/2026.08.08-a-number-an-item-orders-re-measured-is-taken-by-a-probe-the-tree-does-not-hold.md)).

06.6's amendment to the same finding added a second number of this shape and it
is cheaper to produce than the reuse row: `slider_to_graph` is a window render
plus the stack that makes it drawable, and the claim that the stack is 0.22-0.26
ms of the 5.12 ms span — the argument that the collector is not what costs, and
the one that decides whether a longer window is the render's problem or the
assembly's — came from instrumentation the run deleted. No new clock is needed
for it: the `GRAPH_EDITS` refills already publish `full_preview_render` on the
same bus inside the span, so the split is a subtraction over samples the fixture
holds and drops. That is the same drop
[the-per-sample-gate-sees-every-sample-the-run-published.md](the-per-sample-gate-sees-every-sample-the-run-published.md)
owns, and it is why these two want doing in one pass. The `stack_share_of_a_refill`
half of the criterion above is that subtraction published as a reading, not a
gate — no ceiling on it has been argued for.

`tests/bench/test_loop_budget.py` already renders the reference workload against
a `MemoryFrameStore`, cold and then post-edit, which is exactly the run the
figure is counted over — what it does not do is count. `FrameResult.from_cache`
is the field, and the count is per render rather than per run, since the row's
meaning is "one post-edit render reused this much".

What should be different: the reuse counts are published by the same reading the
timings are, so a session that changes what may be keyed re-runs the harness
rather than rebuilding a probe, and a review can re-run it too. Whether the
figure gates anything is a separate question and this does not decide it — a
ceiling on reuse would be a number nobody has argued for, and the value here is
that the finding's row has a producer. If a gate is wanted later,
`the-per-sample-gate-sees-every-sample-the-run-published.md` is where the
collection this would join is being reshaped, and the two want reading together.
