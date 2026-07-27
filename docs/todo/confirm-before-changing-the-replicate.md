---
title: Confirm before changing the replicate
status: deferred
opened: 2026-07-27
gated_on: >
  the save/history policy in `docs/todo/no-save-prompts-keep-history.md` being
  settled — if automatic rollback is the safety net, this modal is the pattern
  that item rejects
reads:
  - docs/todo/no-save-prompts-keep-history.md
  - src/sieve/core/replicates.py
  - src/sieve/gui/document.py
---

# Confirm before changing the replicate

Noticed `<=2026.07.27`: "if the user sets the replicate and tries to change it,
it should ask for confirmation as a box."

Deferred on a direct tension, not on effort. The **No save prompts, keep
history** item (`docs/todo/no-save-prompts-keep-history.md`) asks for the
open/save modals to go away in favour of automatic history with rollback. If
rollback is the safety net, then a confirmation modal in front of a geometry
edit is the same pattern being removed one screen over — the user is asked to
predict a mistake instead of being allowed to undo it. Settle that policy
first; this item is either built or closed by the answer.

**There is a second, prior gap: "the replicate is set" has no representation in
the model today.** `Replicate` (`src/sieve/core/replicates.py:52-86`) carries
`roi`, `name`, `replicate_id`, `overrides`, and `detector_overrides` — no
confirmed or locked flag. A confirmation box has nothing to test. Adding one is
not a free field either; rule 7 applies. A "confirmed" flag changes only
whether the GUI interposes a dialog, not what a result *is*, so it must not be
hashed — which by rule 7's own construction is an argument that it does not
belong on `Replicate` (whose identity is `replicate_id` and whose geometry is
hashed) any more than `checkpoints` and `outputs` belong on `Node`. Where it
does belong is the real design question here, and it should be answered before
any dialog code.

Third consideration, if it is built: `ReplicateDocument` already has undo for
ROI edits, with `SetReplicateROI` merging per press token so one drag is one
undo entry (`docs/TODO.md`'s settled table). A confirmation that fires per
merged command is one box per drag; one that fires per `set_roi` is a box per
mouse-move. That distinction has already bitten a test once — the settled table
records that a drag with a single mouse-move cannot see merge behaviour at all.
