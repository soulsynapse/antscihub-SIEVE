---
title: A frame count does not enforce its own int
status: awaiting-review
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

## The anchor is widened, and it had already moved without being spent

The guard is `FrameCount.__post_init__`'s, beside the sign check, and
`_whole_lookahead` is gone — `ToolSpec.__post_init__` and
`node_lookahead_frames` both dropped their call, because a fractional count now
raises at the `return` inside the tool that computed it, which is where the
negative one has always been met. The two lookahead cases 01.3 wrote still pass
unchanged: they match on `whole frames`, and both `FrameCount(2.5)` expressions
raise inside the `pytest.raises` block before the spec or the step is built.
Their comment is rewritten, because it described the shape the code has left.

**The terms.** The anchor admits a guard the v2 file did not have. It does not
admit a constructor, because nothing here needed one and that is the whole
test — a later item whose entire subject *is* the change may make it, and
nothing else may. What decided this is not an argument about how much verbatim
is worth: `core/types.py` stopped equalling v2's blob at 02.1, for a docstring
that named two schema fields schema v1 had deleted, and no gate noticed. The
measurement and the reasoning are in
[findings/loop/2026.08.07-the-copy-verbatim-anchor-stopped-being-verbatim-two-commits-after-it-landed.md](../findings/loop/2026.08.07-the-copy-verbatim-anchor-stopped-being-verbatim-two-commits-after-it-landed.md).
So the thing the two items were deferring to had already ended, and deferring
again would have been deferring to nothing. Verbatim is a rule about how a port
lands, not a freeze afterwards.

What the window item may therefore spend: `FrameSpan.centred_on` is **not**
refused by this ruling — that item's own fallback ("if it ruled that the anchor
holds and guards live at the declaration boundaries") does not fire. It is free
to weigh the two shapes on their merits. What it may not do is add the
constructor as a convenience beside some other work; the change has to be the
item's subject, as this one's was.

**The `bool` clause is carried, with its own reason and its own message.** It is
not the fractional refusal — `True` *is* whole, it is one — so it no longer
shares the fractional refusal's sentence, which said "must be whole frames, got
True" and was false about its own subject. It is refused because it is the
silent direction: a truthiness value where a count goes is one frame of lead-in,
and one frame of lead-in is a legal declaration nothing downstream has grounds
to question, where 2.5 would at least have been visible to whatever rounded it.
The clause 01.3's review found undistinguished is now distinguished — the sweep
over the three clauses of the guard kills all three:

```
$ uv run python scripts/mutation_sweep.py --file src/sieve/core/types.py \
    --mutant "if isinstance(self.frames, bool): ==> if False:" \
    --mutant "if not isinstance(self.frames, int): ==> if False:" \
    --mutant "if self.frames < 0: ==> if False:" \
    -- uv run pytest -q tests/unit/test_tool_contract.py \
       tests/unit/test_types.py tests/unit/test_quantities.py
KILLED    if isinstance(self.frames, bool):
KILLED    if not isinstance(self.frames, int):
KILLED    if self.frames < 0:
mutation_sweep: 3 killed, 0 survived
```

The four cases are `TestWholeFrames` in `tests/unit/test_tool_contract.py`, and
each was shown failing against the unchanged tree before the guard landed. Three
of them are the declaration boundaries the body names — a `warmup_frames` bound,
a `warmup_frames` refinement through `input_warmup_frames`, and the constructor
that `at_input_of` reads through, which is the one that argues for the anchor
over the boundaries: `ceil` turns 2.5 frames behind a 10:1 decimator into 25
source frames of decode range that no declaration ever stated.

```
$ uv run pytest tests/unit/test_tool_contract.py -q -k whole_frames
....                                                                     [100%]
4 passed, 75 deselected in 0.16s

$ uv run pytest tests/unit/test_tool_contract.py tests/unit/test_types.py tests/unit/test_quantities.py -q
........................................................................ [ 67%]
..................................                                       [100%]
106 passed in 0.20s
```

The whole gate is green: `ruff check` clean, 6 import contracts kept, 729 tests.

What this ruling deliberately does not settle is whether the verbatim claim
should be checkable at all, for this file or the ports still to land:
[whether-a-verbatim-port-stays-verbatim-after-its-review.md](whether-a-verbatim-port-stays-verbatim-after-its-review.md),
deferred because a blob gate goes red on the intended edit too and what the
table does about that is a decision rather than an afternoon.
