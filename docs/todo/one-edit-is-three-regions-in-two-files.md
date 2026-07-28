---
title: One edit is three regions in two files
status: open
opened: 2026-07-28

gated_on: >
  nothing structurally — but the first step is a decision, and taking the
  mechanical half without making it is churn with no payoff

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
once by `redo` to act. `commands.py` imports `document.py` under `TYPE_CHECKING`
to avoid a cycle, and every command holds `self._document`. That back-reference
is exactly the test `docs/todo/filter-tab-is-eleven-jobs.md` states for a bad
seam, applied to a split that already happened: *if the extracted object must
hold a back-reference to do its job, the seam is wrong.*

## The pain is the trio, not the file boundary

This matters because the obvious move is the wrong size. Merging `commands.py`
into `document.py` removes the import cycle, the back-reference becomes `self`,
and the co-change number goes to zero by construction — and produces a
1,670-line file in which one edit is still three regions. The file boundary is
not where the axis of change runs; the *mechanism* is. A merge alone buys
locality, and locality is the aesthetic payoff this plan is supposed to cut.

So the item's first job is a decision, and the mechanical half is downstream of
it either way.

**Option A — merge, and stop.** `commands.py` moves into `document.py` beside
the methods each command serves. Cheap, mechanical, pyright-checked, no
behaviour change. Honest assessment: this is worth doing *only* if B is
rejected, because if B lands the command classes mostly stop existing and the
merge was churn against code about to be deleted.

**Option B — one undo mechanism instead of two, and the second one already
exists.** `DocumentState` is four immutable fields, `capture()` is documented as
cheap, and `RestoreSnapshot` already undoes by value rather than by displacement.
That is a working proof that a command need not hold a back-reference or
remember what it displaced: it can hold a before-state, an after-state, a text,
and a merge id. `EditTuningParams`, `EditDetector`, `ResetTuning`, `SetClip`,
`AddReplicate`, `RemoveReplicate`, `RenameReplicate` collapse toward one shape,
`apply_*` stops being public, and `_would_change` becomes `before != after`,
which is the same question asked once instead of twice.

**What would make B wrong, and it has to be checked rather than argued.**
`commands.py`'s docstring gives the reason for displacement-based undo: an
inverse "is always exact even after other edits have moved rows around". A
snapshot is immune to moved rows for a different reason — it does not name them
— so that specific argument survives the change. What does not obviously survive
is `mergeWith`: `SetReplicateROI` collapses a drag into one entry and
`ROI_MERGE_ID`/`DETECTOR_MERGE_ID` keep two gestures from merging into each
other. Snapshot merging is "keep the first before, take the latest after", which
is correct but is a claim, not a given. Pin it with a test over a simulated drag
before converting anything, and if it does not hold, B is dead and A is the
whole item.

**Do not convert the geometry gesture first.** `finish_roi_gesture`, `_Gesture`,
and the merge ids are the most intricate part of the stack and the part users
touch most. Convert `SetClip` first — one field, no merge, no index arithmetic —
and let it be the shape the rest follow or refute.

## What breaks if this is wrong

Holes in undo, which `document.py`'s own docstring names as discovered by users
rather than by tests. That is the cost line for the whole item and it is why the
sequencing above is worth obeying. The existing coverage is real but partial:
`tests/gui/test_document.py` and `tests/gui/test_history.py` exercise the stack,
and neither would fail if a converted command silently restored a field it
should have left alone — a snapshot restore writes all four fields every time,
so a bug here looks like an unrelated value quietly reverting. Any conversion
lands with a test that asserts the *untouched* fields are untouched across an
undo, which is the assertion the current mechanism gets for free and B does not.
