---
title: The epsilon admission question is owed a measurement, and VISION's lead scenario is what pays for it
phase: 6
priority: high
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/bench/test_loop_budget.py tests/unit/test_background_ema.py -q -k 'the_background_chain_pays_its_lead_in or a_sub_epsilon_difference_reaches_a_detection'"
opened: 2026-08-09
---

# The epsilon admission question is owed a measurement

Minted this morning proposing that `settle_frames` makes an epsilon warmup
bounded and therefore admissible. That is wrong and
[adr/cache-admission-is-bounded-warmup.md](../adr/cache-admission-is-bounded-warmup.md)
says why, in the paragraph naming this exact tool: bounded means output at frame
`N` is *fully determined* by the last `W + 1` inputs, and an EMA's true warmup is
infinite — its 90 is where the seed drops below 1% of the model's weight, which
is a claim that the residual is small and not that it is zero. The ADR's gate is
bit-identity against a cold run, and a small residual is not bit-identity. The
item was re-arguing a settled decision from a docstring, and the ADR had already
heard the argument.

What survives is the half the ADR itself leaves open and marks as owed: "Also
rejected, and deliberately left open: admitting `background_ema` and
`temporal_baseline` on a measured epsilon. Whether a difference below the
declared threshold survives into a detection flip is unmeasured, and nothing here
admits them." That is a revival condition with a measurement attached and no one
holding it. This item holds it — not to admit the tools, but to produce the
number that decides whether admitting them on a measured epsilon is a live option
or a closed one.

The reason it is worth taking now rather than at its number is the other half,
which is true regardless of how the measurement lands. `background_ema` has no
key, so nothing downstream of it has one either — `preview.py`'s own docstring
says a graph containing such a node decodes and runs its whole lead-in on every
render — and VISION's lead scenario is a generated background feeding a
subtraction. The chain the product is introduced with is the chain the store
cannot help, and nobody has counted what that costs. 06.3 counted recomputed node
outputs on a post-edit render and did it on a graph with no epsilon node in it.
The first `-k` term is that count on a chain that has one.

The remedy if the number is bad is not this item's to build and is already
written down: a materialized checkpoint upstream of the node, behind checkpoint
read-back and the source-tool migration
([crop-serving-and-checkpoint-read-back-become-source-tools.md](crop-serving-and-checkpoint-read-back-become-source-tools.md)).
What this item can do is say whether that chain is worth scheduling, which is
more than anyone can say today.

`done_when` at minting, red because nothing matched — the criterion as first
written named `a_settled_epsilon_node_is_admitted`, which would have asserted the
thing ADR 17 refuses:

    $ uv run pytest tests/bench/test_loop_budget.py tests/unit/test_background_ema.py -q -k 'the_background_chain_pays_its_lead_in or a_sub_epsilon_difference_reaches_a_detection'
    24 deselected in 0.65s
    exit: 5

## 2026-08-09: both halves measured, and the epsilon half closes the ADR's option

Neither number lives here. The epsilon question is answered yes — a residual at
0.28% of the footage's range, a quarter of what the tool declares, moves the
windowed in-band count through 3% of its own tunable range and a threshold
placed in that band disagrees on 3 frames of 80
([findings/2026.08.09-a-sub-epsilon-residual-flips-a-detection.md](../findings/2026.08.09-a-sub-epsilon-residual-flips-a-detection.md)).
Admitting the two tools on a measured epsilon is closed rather than deferred,
and the ADR's paragraph inviting it is now an invitation with an answer beside
it. Amending a settled decision is not this run's edit; whether that takes a
successor ADR is Kendrick's.

The cost half is measured too and is smaller than the item assumed: a post-edit
render on the lead scenario's chain drops reuse from 0.667 to 0.250 and costs 75
tool calls against 10 for the same 10 answered frames, but it decodes nothing —
the crop above the model keeps its key and its lead-in entries are read back
([findings/2026.08.09-the-epsilon-chain-repeats-its-lead-in-arithmetic-not-its-decode.md](../findings/2026.08.09-the-epsilon-chain-repeats-its-lead-in-arithmetic-not-its-decode.md)).
`preview.py`'s sentence that such a graph "decodes and runs its whole lead-in on
every single render" is therefore true only for an epsilon node at the root; the
correction is folded into
[the-admission-argument-is-retold-in-four-modules.md](the-admission-argument-is-retold-in-four-modules.md),
which already owns that module's prose about the admission rule.

The remedy this item points at is no longer behind anything: both
[crop-serving-and-checkpoint-read-back-become-source-tools.md](crop-serving-and-checkpoint-read-back-become-source-tools.md)
and its checkpoint half are `done`. What the reading above says about scheduling
it is that the ratio is 7.5x on 160x120 footage and the repeated work is per
pixel, so the number that decides is one nobody has at resolution.
