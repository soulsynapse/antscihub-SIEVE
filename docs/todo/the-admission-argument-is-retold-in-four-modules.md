---
title: The admission argument is retold in four modules instead of cited once
priority: normal
phase: 6
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
