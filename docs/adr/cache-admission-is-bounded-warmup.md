---
title: Cache admission is a bounded warmup, not a stateless tool
adr: 17
position: "04.03"
status: settled
decided: 2026-08-07
---

A tool is keyed when its warmup is **bounded**, stateful or not, and a run
entering a cached range re-settles its state over that warmup first. An
epsilon warmup is refused.

Bounded means a declared finite `W` for which output at frame `N` is fully
determined by the last `W + 1` input frames, so `cache_policy` decides on that
rather than on `stateful`.

Why: the refusal it replaces reads one bit that stands for two different
properties. `executor.py` gives the honest reason — a stateful node "is never
served a cache [hit]" because missing frame `i` "would leave the tool running
on a state that had seen" everything else — which is a claim about *continuing*
a run, not about whether the cached value is right. `block_signal` declares the
previous frame *is* its state and `warmup_frames = 1`; `detect` is a bounded
centred window. Both outputs are determined by their index, and both are
refused a key anyway. `background_ema` is the case the refusal is actually for,
and its module says so: an EMA's true warmup is infinite, and its 90 is where
the seed drops below 1% of the model's weight. One rule was doing two jobs.

The cost of not separating them is the loop's own claim. Phase 6 measured 58 of
87 node outputs recomputed on every post-edit render, so what the preview store
saves is the decode and not the arithmetic
([findings/2026.08.07-the-loop-budget-is-met-headless.md](../findings/2026.08.07-the-loop-budget-is-met-headless.md)).
The two nodes producing the graph are exactly the two this ADR admits.

The evidence that bounded is enough is v1. `core/stream_buffer.py` in
`../antscihub-optical-flow-detector` held one contiguous island of block-grid
results and reused any range inside it for free; it is *one* island because the
live state sits at the frontier, so the frontier is the only place a run can
extend from. Re-settling over `W` at each entry is what dissolves that
constraint: the entry cost replaces the contiguity requirement, so retention
may be scattered, which the existing `(node key, source index)` store already
is. Rejected for that reason: porting v1's ring as a second, span-shaped store.
It answers a question that was never the blocker — the store's shape was fine;
the policy would not let anything into it.

Also rejected, and deliberately left open: admitting `background_ema` and
`temporal_baseline` on a measured epsilon. Whether a difference below the
declared threshold survives into a detection flip is unmeasured, and nothing
here admits them. This ADR neither weakens
[correctness-is-the-default](correctness-is-the-default.md) — an admitted tool
is bit-identical to its cold run, not an approximation of it — nor
[one-execution-path](one-execution-path.md), since the rule is the executor's
and applies to a preview and a production run identically.

The gate is the bit-identity: for every tool admitted by this rule, a range
served from the store after re-settling equals the same range computed cold.
The declaration itself is refused at registration when absent
([declared-means-verified](declared-means-verified.md)).
