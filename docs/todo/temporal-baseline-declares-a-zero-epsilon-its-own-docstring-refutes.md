---
title: temporal_baseline declares a zero epsilon its own docstring refutes
priority: high
phase: 4
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/unit/test_tool_contract.py -k an_epsilon_warmup_declares_a_nonzero_epsilon -q"
opened: 2026-08-07
---

# temporal_baseline declares a zero epsilon its own docstring refutes

`temporal_baseline` registers `settling_epsilon=0.0` and, since 06.5,
`warmup_kind=WarmupKind.EPSILON`. The two cannot both be true.
`WarmupKind.EPSILON`'s own docstring says two runs "agree to within that
tolerance and not bit-for-bit", and `cache_key._uncacheable_clause` prints the
value in the refusal it hands the user — so the message a reader gets today is
that the tool's output "still carries where the run began — to within 0.0,
which is not to within nothing". The module docstring says as much in prose:
"The declared `settling_epsilon=0.0` predates that reading and understates it."

A docstring that names its own declaration as false is the honest half. The
declaration is still on the shelf, and `settling_epsilon` is not decorative —
`adr/declared-means-verified.md`'s generic gate compares two runs against it,
so a tool declaring zero is asserting bit-identity that the same commit's
reasoning says it does not have.

What should be different: `ToolSpec.__post_init__` refuses `EPSILON` beside a
`settling_epsilon` of `0.0` or `None`, for the reason it already refuses a
nonzero `warmup_frames` with no epsilon — a settling claim with no tolerance is
not a claim. That refusal makes `temporal_baseline` unregisterable until its
epsilon is measured, which is the point: the number is a measurement and the
measurement is what is owed. Take it the way `background_ema`'s `SETTLED_EPSILON`
was taken — two runs entering the same frame from different origins, the largest
per-cell difference once the declared warmup has elapsed — and mint it as a
finding the tool cites, not as a number chosen to make the refusal pass.

The criterion names the refusal rather than the number, because the number is
the finding's and this item is the contract's. `block_signal` and `detect` are
unaffected: both declare `BOUNDED` with `settling_epsilon=0.0`, which is the
consistent pair.
