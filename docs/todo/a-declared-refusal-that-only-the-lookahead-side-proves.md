---
title: A declared refusal that only the lookahead side proves
priority: normal
phase: 3
status: done
gated_on: nothing
done_when: "uv run pytest tests/unit/test_tool_contract.py tests/unit/test_plan.py -q -k warmup_side"
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

## The criterion names both files, because the home is the other item's

The case spells `warmup_side`, mirroring
`test_a_non_positive_output_rate_is_refused_on_the_lookahead_side` in
`tests/unit/test_plan.py` — which is the twin's case, says in its own docstring
that the warmup guard answers for both its graphs, and points here. Naming both
files means the criterion is indifferent to where
[the-lookahead-conversion-picks-a-home.md](the-lookahead-conversion-picks-a-home.md)
puts the pair: the refusal is owed a case of its own either way, and if the two
functions merge into one the case merges with them rather than the item lapsing.

Asserted against `input_warmup_frames` directly and not through
`source_warmup_frames` or `ExecutionPlan.build`, for the reason the twin's
docstring already gives: reaching it through a fold proves whichever guard the
fold hits first, which is how this one came to be the unproven side.

## What the proof of red measured

`input_warmup_frames` stayed where it is, so the case landed in
`tests/unit/test_tool_contract.py` as `TestRate`'s
`test_a_non_positive_output_rate_is_refused_on_the_warmup_side`, over a
`StalledParams` whose `rate` field covers zero and negative. Deleting the two
guard lines does not make the call succeed — `at_input_of` refuses the same
rate one line later — so the case is red on the *message*, `output rate must be
positive to convert frames, got 0` in place of `stalled: output_rate must be
positive`. That is the guard's whole subject: it names the node, and the one
below it names only the number.
