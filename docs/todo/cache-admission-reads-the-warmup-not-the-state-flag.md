---
title: Cache admission reads the warmup, not the state flag
step: "06.5"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_cache_admission.py -q -k a_bounded_warmup_tool_served_from_the_store_equals_its_cold_run"
opened: 2026-08-07
---

# Cache admission reads the warmup, not the state flag

`adr/cache-admission-is-bounded-warmup.md` is the decision; this is it built.
When it is done, `block_signal` and `detect` are keyed and served from the
store, and `background_ema` and `temporal_baseline` are still refused — by
their warmup being an epsilon, not by their being stateful.

Two things move. `cache_policy` stops returning `STATEFUL_ORIGIN` for a tool
whose warmup is bounded, which means the contract has to say which kind of
warmup a tool declares; `adr/declared-means-verified.md` puts that refusal at
registration rather than at the first cache lookup. And the executor gains the
re-settle: entering a cached range, a stateful tool is run over its warmup
frames with the output discarded before the first frame is emitted, which is
the same discard the warmup path already performs at the start of a run.

The criterion is the ADR's gate and it is the whole point of the item: a range
served from the store equals the same range computed cold, exactly, for a tool
this rule admits. Approximately-equal is a failure — an admitted tool is
bit-identical to its cold run or it is not admitted, which is what keeps
`adr/correctness-is-the-default.md` and `adr/one-execution-path.md` intact.
Assert it on `block_signal`, whose state is one frame, and on `detect`, whose
window is bounded on both sides; the second is the one that can go wrong, since
its lookahead means the range it needs is wider than the range it emits.

What this item does not do, so it does not grow: no retention or eviction
policy (PLAN.md's revival table holds it, gated on a real scrub pattern), and
no admission of the two epsilon-warmup tools. Whether their declared threshold
is tight enough to survive into a detection flip is unmeasured, and measuring
it is a finding, not this.

The reading that motivated it is
`docs/findings/2026.08.07-the-loop-budget-is-met-headless.md`: 58 of 87 node
outputs recomputed on a post-edit render, because the two nodes the graph is
drawn from are both refused a key. Re-run that measurement afterwards — if the
recomputed count does not fall, the admission did not reach the path the
preview actually takes, and the item is not done however green the criterion
is.
