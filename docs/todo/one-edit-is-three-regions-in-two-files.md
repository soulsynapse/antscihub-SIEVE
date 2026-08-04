---
title: One edit is three regions in two files
status: open
priority: unassessed
opened: 2026-07-28T12:57:15-07:00

gated_on: >
  nothing — scoped to option A on 2026-07-28 after 937ac91 refused option B

reads:
  - src/sieve/gui/document.py
  - src/sieve/gui/commands.py
  - tests/gui/test_document.py
  - tests/gui/test_history.py
---

# One edit is three regions in two files

`gui/commands.py` has been edited in seven commits. `gui/document.py` was
edited in all seven. Nothing else in the repo has that shape — the next highest
coupling is `detector_worker.py` inside `filter_tab.py`, which is a slice of one
widget by another name. Seven of seven is the co-change matrix saying these two
files have never had a reason to change apart.

The mechanism is visible in one edit. Adding or changing an editable field
means touching, in order:

1. `ReplicateDocument.edit_params` — the public entry, which decides whether the
   edit is a no-op and pushes.
2. `EditTuningParams` in `commands.py` — which recomputes the same thing to do
   it, keeps what it displaced, and calls back into the document.
3. `ReplicateDocument.apply_params` — a second public surface that exists only
   for step 2 to call, mutating without history.

`edited_params` is called twice per edit, once by `_would_change` to decide and
once by `redo` to act.

## The snapshot rewrite was considered and refused (937ac91, 2026-07-28)

Recorded so it is not re-proposed. `DocumentState` is four immutable fields and
`RestoreSnapshot` already undoes by value, so collapsing every command onto
one before/after shape looked like one undo mechanism instead of two. It is
wrong for a reason the co-change number does not show: **each `apply_*` is the
per-edit signal contract, not duplication.** Collapsing onto `apply_state`
makes every Ctrl+Z a full broadcast, and leaves `replicate_changed(index)` —
the only parameterized signal — with no producer.

## What is left, and it is worth doing

Kill the displacement bookkeeping while each command keeps its own targeted
`apply_*`. The double computation of `edited_params` goes; the back-reference
stays, because with the signal contract intact it is what the command is
*for* rather than a seam defect. `commands.py` moves into `document.py` beside
the methods each command serves — cheap, mechanical, pyright-checked, no
behaviour change, and no longer churn against code that was about to be
deleted, which is the only thing that made it not worth doing before.

Be honest about what this buys: locality and one fewer computation, not a
smaller mechanism. One edit is still three regions; they are now three regions
in one file. The 1,670-line result is the cost, and the axis-of-change test in
`CLAUDE.md` says it is the right trade here specifically because seven of seven
means nothing declares the coupling today.

## What breaks if this is wrong

Holes in undo, which `document.py`'s own docstring names as discovered by users
rather than by tests. `tests/gui/test_document.py` and `tests/gui/test_history.py`
exercise the stack, and neither would fail if a command silently restored a
field it should have left alone. Land the merge with a test that asserts the
*untouched* fields are untouched across an undo — the current mechanism gets
that assertion for free and nothing states it.
