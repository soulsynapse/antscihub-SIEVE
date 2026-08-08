---
title: A frame count does not enforce its own int
status: open
priority: normal
phase: 1
gated_on: nothing
done_when: "uv run pytest tests/unit/test_tool_contract.py -q -k whole_frames && uv run pytest tests/unit/test_tool_contract.py tests/unit/test_types.py tests/unit/test_quantities.py -q"
opened: 2026-08-07
---

# A frame count does not enforce its own int

`FrameCount` annotates `frames: int` and `__post_init__` checks only the sign,
so `FrameCount(2.5)` constructs and every count in the system admits a
fraction. 01.3 needed the refusal for `lookahead_frames` — dividing a window
length in half is the obvious way to produce one — and put it in
`tool_base._whole_lookahead`, which guards that one field and nothing else.
`warmup_frames`, `at_input_of`'s result, and every `FrameCount` a decode range
is built from are still unguarded.

The refusal belongs in `FrameCount.__post_init__` beside the sign check, and
that is why this is an item rather than a line: `core/types.py` is the
copy-verbatim anchor (01.1), so adding a check to it is a decision about what
verbatim survives to, not a fix. The two ways out are to widen the anchor's
terms deliberately or to leave the guard at the declaration boundaries and say
so — either is fine, neither should happen by reflex. Whichever wins,
`_whole_lookahead` collapses into it.

It is not the only item asking that question of that file.
[a-centred-window-counts-its-target-from-the-wrong-end.md](a-centred-window-counts-its-target-from-the-wrong-end.md)
wants `FrameSpan` to carry which of its frames is the target, and stops for the
same reason in the same words — widening 01.1's anchor is a decision about that
file. One decision, two subjects, and this one drains first (phase 1 before
phase 3), so the session that takes it settles the terms and the window item
spends them rather than re-arguing them. State the terms in whatever lands here:
whether the anchor admits a guard the v2 file did not have, a constructor it did
not have, or neither.

Carry the `isinstance(count.frames, bool)` clause across when it does. It is
there because `bool` subclasses `int`, so `FrameCount(True)` passes the int
check alone; 01.3's review found that deleting the clause leaves all 57
contract tests green, which makes it the one line of the guard nothing
distinguishes. Whether `True` is worth refusing is part of the same decision.

## The criterion is neutral between the two ways out

The cases land in `tests/unit/test_tool_contract.py` and spell `whole_frames`,
whichever way the decision goes. They cannot land in `tests/unit/test_types.py`:
that file is 01.1's ported spec and the porting discipline refuses rewriting a
ported test, so the file that would be the obvious home for a `FrameCount`
constructor case is the one file the work may not add one to. What the criterion
pins is therefore the hole rather than the fix — a fractional `warmup_frames`
declared on a `ToolSpec` is refused, and so is every other declaration boundary
the body names — which is true if the guard moves into `FrameCount.__post_init__`
and true if it stays at the boundaries. The second half runs the ported spec
beside the contract, because widening the anchor is the branch that could land
green while quietly moving what 01.1 froze.
