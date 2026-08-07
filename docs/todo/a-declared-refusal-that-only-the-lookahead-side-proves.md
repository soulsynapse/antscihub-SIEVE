---
title: A declared refusal that only the lookahead side proves
priority: normal
phase: 3
status: open
gated_on: nothing
opened: 2026-08-07
---

# A declared refusal that only the lookahead side proves

`core/tool_base.py`'s `input_warmup_frames` refuses a non-positive
`output_rate` with `ValueError`, and no test in the repo asserts it — the
sweep that found the gap ran over `pipeline/plan.py` and only its lookahead
twin `_input_lookahead_frames` was in that diff, so only that one is being
closed under 03.5
(`findings/loop/2026.08.07-a-fold-has-two-maxima-and-one-fork-fixture-exercises-the-inner-one.md`).

The guard is reachable: `ToolSpec` requires a `rate_changing` tool to override
`output_rate`, and nothing constrains what the override returns. A `Fraction(0)`
would make `at_input_of` divide by zero, and a negative one would run the whole
graph with a window pointing the wrong way.

What makes this a pool item rather than a line in 03.5 is that the two guards
are one conversion in two places, and where that conversion ends up living is
itself undecided (`todo/the-lookahead-conversion-picks-a-home.md`). If the pair
merges, this closes as a duplicate of 03.5's case; if `input_warmup_frames`
stays in `core`, its refusal wants a case in `tests/unit/test_tool_contract.py`
beside the two that already assert the *declaration* rule — that a rate-changing
tool must override `output_rate` and a streaming one must not.
