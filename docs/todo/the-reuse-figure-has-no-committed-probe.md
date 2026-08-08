---
title: The reuse figure the loop budget rests on is produced by no committed probe
phase: 6
priority: normal
status: open
gated_on: nothing
done_when: "uv run pytest tests/bench/test_loop_budget.py -k reuse_on_a_post_edit_render -q"
opened: 2026-08-08
---

# The reuse figure the loop budget rests on is produced by no committed probe

`docs/findings/2026.08.07-the-loop-budget-is-met-headless.md` carries a reuse
row — node outputs recomputed against node outputs served, on a post-edit window
render — and it has been measured three times by three sessions, each from a
scratch file it deleted afterwards. Nothing in the tree produces it, so no review
can check it and every future change to the admission rule re-orders the same
hand-built harness ([findings/loop/2026.08.08-a-number-an-item-orders-re-measured-is-taken-by-a-probe-the-tree-does-not-hold.md](../findings/loop/2026.08.08-a-number-an-item-orders-re-measured-is-taken-by-a-probe-the-tree-does-not-hold.md)).

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
