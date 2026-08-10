---
title: An epsilon warmup denies a key to everything downstream, and VISION's lead scenario is all downstream
phase: 6
priority: high
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_cache_admission.py tests/bench/test_loop_budget.py -q -k 'a_settled_epsilon_node_is_admitted or the_background_chain_pays_its_lead_in'"
opened: 2026-08-09
---

# An epsilon warmup denies a key to everything downstream

`background_ema` declares `warmup_kind=WarmupKind.EPSILON`, and its own module
docstring says what that costs: it "is what denies it a key". `preview.py`'s
docstring says the rest — an epsilon-warmup node has no key at all, so a graph
containing one decodes and runs its whole lead-in on every render. VISION's lead
scenario is a generated background feeding a subtraction, so the scenario the
product is introduced with is on the uncacheable path by construction, and the
graph a user draws first is the one the store cannot help.

The remedy written down is a materialized checkpoint upstream of the node, and
it is behind three gates that nothing schedules — checkpoint read-back, then the
source-tool migration
([crop-serving-and-checkpoint-read-back-become-source-tools.md](crop-serving-and-checkpoint-read-back-become-source-tools.md)),
then the first source tool. That chain is not what this item asks for.

What it asks for is the reading that
[adr/cache-admission-is-bounded-warmup.md](../adr/cache-admission-is-bounded-warmup.md)
makes available and nobody has spent. That ADR keys admission on a **bounded
warmup** rather than on statelessness, and `background_ema` already computes its
own bound: `settle_frames(alpha, epsilon)` returns the frame at which the
oldest weight falls below `SETTLED_EPSILON`, and the spec carries the epsilon it
was computed against. A warmup that a function can name in frames is bounded in
the sense the ADR means, whatever the enum member is called — so either
`WarmupKind.EPSILON` is a second name for BOUNDED and the two tools carrying it
are admissible, or there is a reason it is not that the ADR does not state. This
item is where that is decided, and the gate is the ADR's own: bit-identity
against a cold run, so nothing here weakens
[adr/correctness-is-the-default.md](../adr/correctness-is-the-default.md).

The measurement comes first and is half the criterion. 06.3 counted recomputed
node outputs on a post-edit render; nobody has counted them on a chain with an
epsilon node in it, and the second `-k` term is that number. Admitting the node
without it would be a fast path argued from a docstring.

`done_when` at minting, red because nothing matched:

    $ uv run pytest tests/unit/test_cache_admission.py tests/bench/test_loop_budget.py -q -k 'a_settled_epsilon_node_is_admitted or the_background_chain_pays_its_lead_in'
    17 deselected in 0.62s
    exit: 5
