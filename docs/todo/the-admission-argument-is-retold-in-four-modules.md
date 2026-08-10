---
title: The admission argument is retold in four modules instead of cited once
priority: normal
phase: 8
status: open
gated_on: nothing
opened: 2026-08-07
---

# The admission argument is retold in four modules instead of cited once

`adr/cache-admission-is-bounded-warmup.md`'s second paragraph is the argument
that one bit was standing for two properties — `block_signal` keeps a frame of
state and is exactly determined by two frames, `background_ema` keeps the same
kind of state and is determined by all of them. 06.5 wrote that argument out
again, in its own words, in four places, each of which also cites the ADR:

- `core/tool_base.py`, `WarmupKind`'s class docstring, the paragraph beginning
  "v3 read `stateful` for the second question until 06.5" (6 lines).
- `pipeline/cache_key.py`, `cache_policy`'s docstring, the sentence beginning
  "Until 06.5 this read `stateful`, which refused `block_signal` (one frame of
  state, exact)" (4 lines).
- `tools/block_signal.py`, module docstring, "Until 06.5 it was refused a key
  for being stateful, which is the same declaration `background_ema` makes
  about a dependence that never ends" (3 lines).
- `tools/background_ema.py`, module docstring, "not `stateful`, which
  `block_signal` also declares and is keyed" (2 lines).

CLAUDE.md's three homes are the test: the module docstring holds the contract,
the ADR it cites holds the reasoning. Each of these four already has the
citation beside it, so the retelling is the part that can go — what stays is
the sentence saying what the field is and what reads it, which is the contract
and is not in the ADR. The fourth is a borderline call and is listed so the
next reader does not have to re-find it; the first two are not borderline.

Prose fractions across 06.5, before and after
([findings/2026.08.07-the-goal-with-no-gate-is-the-one-going-backwards.md](../findings/2026.08.07-the-goal-with-no-gate-is-the-one-going-backwards.md)
is the standard): `core/tool_base.py` 60.4% to 60.6%, `pipeline/cache_key.py`
70.6% to 70.5%, `tools/block_signal.py` 44.4% to 45.0%, `tools/background_ema.py`
63.4% to 63.6%. Nothing moved more than a point in either direction, so this is
not a file that got worse — it is a file that stayed at 70.5% while the one
paragraph that could have come out went in three more times.

No `done_when`. A prose fraction is a bad gate on its face for the reason that
finding's open question states, and "the argument appears once" is not
expressible as a command without pinning the sentences themselves. It is
drained by a reader at Phase 6's boundary, against the four line ranges named
above, and the check is that the ADR still says it and the four modules point
at the ADR.

## 2026-08-09: a fifth site, and its retelling is wrong rather than redundant

`pipeline/preview.py`'s paragraph beginning "**An epsilon-warmup node makes
every render pay its lead-in.**" is the fifth place the argument is told, and it
is the only one that adds a claim the ADR does not make: that such a graph
"decodes and runs its whole lead-in on every single render". Measured on the
chain VISION opens with, it re-runs the lead-in and decodes none of it — the
crop above the model keeps its key, its lead-in outputs are entries like any
others, and every render after the cold one reads all of them back
([findings/2026.08.09-the-epsilon-chain-repeats-its-lead-in-arithmetic-not-its-decode.md](../findings/2026.08.09-the-epsilon-chain-repeats-its-lead-in-arithmetic-not-its-decode.md)).
The decode half holds only for an epsilon node with nothing keyed above it.

So this site is not drained the same way as the four above. What comes out of
them is a retelling that is true; what has to come out of this one is a sentence
that is false as written, and what replaces it is the condition — the cost is
the arithmetic, and the decode is paid again only where the model is the root.
The reader draining this item is the one who should make that edit, because it
is the same paragraph and the same pass; naming it separately would be a second
item over one paragraph.

The sentence also carries the number "90 frames for `background_ema`", which is
a measurement quoted into a durable instruction and wrong for every `alpha` a
session actually configures — `warmup_frames` refines the bound and the plan
folds it with what the nodes below ask for. Same edit, same reason.

## 2026-08-10: ADR 33's closing sentence bills a remedy the tree already has

`adr/the-epsilon-admission-is-closed.md`'s last paragraph names
`todo/crop-serving-and-checkpoint-read-back-become-source-tools.md` in the
present tense — "the remedy ... carries" — for the re-walk an unkeyed model
imposes. Both halves are `done`: the crop half at `6076b1f`, and the checkpoint
half, which split out into
[a-checkpoint-is-read-back-as-a-source-tool.md](a-checkpoint-is-read-back-as-a-source-tool.md)
because a `-k` disjunction could not be widened to hold it, at `45bfc41`. So the
sentence reads as an outstanding bill for a mechanism that exists, and the
filename it points at no longer holds the half the ADR needs — a materialized
product upstream of the model is the checkpoint half.

Same class as the two sites above, and the same edit: a state claim quoted into
a durable instruction where a condition belongs ([CLAUDE.md](../../CLAUDE.md)).
Stated conditionally — a graph with an unkeyed model re-walks its lead-in, and
what removes it is available rather than owed — the paragraph is true either
side of the remedy landing. This is a wording change inside an ADR's argument
and not a change of decision, so it drains with this item rather than by
succession.
