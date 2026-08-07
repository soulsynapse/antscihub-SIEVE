---
title: A frame count does not enforce its own int
status: open
priority: normal
phase: 1
gated_on: nothing
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

Carry the `isinstance(count.frames, bool)` clause across when it does. It is
there because `bool` subclasses `int`, so `FrameCount(True)` passes the int
check alone; 01.3's review found that deleting the clause leaves all 57
contract tests green, which makes it the one line of the guard nothing
distinguishes. Whether `True` is worth refusing is part of the same decision.
