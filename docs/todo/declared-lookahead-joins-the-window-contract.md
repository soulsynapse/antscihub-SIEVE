---
title: Declared lookahead joins the window contract
step: "01.3"
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/unit/test_tool_contract.py -k lookahead -q"
opened: 2026-08-06
---

# Declared lookahead joins the window contract

`lookahead_frames` beside `warmup_frames`, same bound/refinement/cross-check
discipline — the declaration v2's trailing-only window lacked and the
detector node needs (PLAN.md, Phase 1). Contract-side only: the executor
honors it in 02.3; here it is declared, validated, and refused where it is
nonsense — negative, fractional, or set by a spec whose mode has no window.
Test names carry `lookahead` so the `-k` gate above selects exactly this
item's claim.

## Landed as warmup's shape on the other side of the frame

`lookahead_frames` is a `ToolSpec` field, a `ParamsBase` instance method, and a
`max_lookahead_frames` classmethod the decorator reads for the bound — the
three pieces `warmup_frames` already has, in the same arrangement, so the two
halves of a window are declared the same way. `node_lookahead_frames` picks
refinement over bound and refuses a refinement above it. The bound is derived
rather than a decorator keyword, which is why `decorator_keywords()` now
subtracts two names instead of one.

The three refusals the item names land in three different places, and the
spread is the answer rather than an inconsistency:

- **Negative** is `FrameCount`'s, unchanged. It fires at the `return` inside
  the tool that computed the number, which is a better place to meet it than
  any check here could be.
- **Fractional** is new, in `_whole_lookahead`, applied to both the bound and
  the refinement. `FrameCount` annotates `frames: int` and enforces only the
  sign, so `FrameCount(2.5)` constructs — and a half-window is exactly how one
  gets made. It raises `TypeError` where the file's other refusals raise
  `ValueError`, because it refuses a value that is not the declared type at
  all rather than one out of range for the tool; `ruff`'s TRY004 says the same
  thing. That the guard covers lookahead only, while `warmup_frames` and every
  other count stay unguarded, is
  [a-frame-count-does-not-enforce-its-own-int](a-frame-count-does-not-enforce-its-own-int.md)
  — the real home is `FrameCount.__post_init__`, and that file is 01.1's
  copy-verbatim anchor.
- **A mode with no window** is `__post_init__`'s, and it is the cross-check
  warmup has no equivalent of. It is one-directional in `state_factory`'s
  direction: `WINDOWED` with no lookahead is v2's trailing window and stays
  legal, while `STREAMING` with lookahead is a contradiction — a node emitting
  on consumption has no later frame it could have read.

Nothing propagates lookahead along a path. `input_warmup_frames` is untouched,
there is no `source_lookahead_frames`, and the emission delay is 02.3's, as the
item says.

```
$ uv run pytest tests/unit/test_tool_contract.py -k lookahead -q
..........                                                               [100%]
10 passed, 47 deselected in 0.12s
```

The whole gate is green: `ruff check` clean, 5 import contracts kept, 123
tests. `ruff format --check` fails, on a line this change did not touch and
that already failed on `ba20afb` —
[the-gate-does-not-check-formatting](the-gate-does-not-check-formatting.md).
