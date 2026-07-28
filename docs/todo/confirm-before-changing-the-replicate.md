---
title: Confirm before changing the replicate
status: deferred
opened: 2026-07-27
gated_on: >
  the save/history policy going the other way — settled 2026-07-27 in
  `docs/todo/no-save-prompts-keep-history.md` as rollback-not-confirmation, so
  building this now knowingly contradicts a decision already taken; the trigger
  is that decision being revisited, not an event
reads:
  - docs/todo/no-save-prompts-keep-history.md
  - src/sieve/core/replicates.py
  - src/sieve/gui/document.py
---

# Confirm before changing the replicate

Noticed `<=2026.07.27`: "if the user sets the replicate and tries to change it,
it should ask for confirmation as a box."

**Closed by the answer, 2026-07-27.** The tension was never about effort. The
**No save prompts, keep history** item
(`docs/todo/no-save-prompts-keep-history.md`) settled the policy as rollback,
not confirmation: the user is not asked to predict a mistake when they can undo
it, and a confirmation modal in front of a geometry edit is exactly the pattern
being removed one screen over. This item is kept rather than deleted because the
two gaps below are real findings about the model that outlive the dialog, and
because a future session that wants this modal should meet the decision rather
than rediscover the request.

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
