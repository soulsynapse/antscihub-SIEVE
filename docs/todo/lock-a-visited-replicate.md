---
title: Lock a replicate that has been tuned
status: open
opened: 2026-07-27
gated_on: >
  nothing — the rule and the state it needs are decided (2026-07-27, below);
  the earlier deferral read this as a confirmation modal, which it is not
reads:
  - src/sieve/core/replicates.py
  - src/sieve/core/pipeline_model.py
  - src/sieve/gui/document.py
  - src/sieve/gui/crop_tools.py
---

# Lock a replicate that has been tuned

Noticed `<=2026.07.27`: "if the user sets the replicate and tries to change it,
it should ask for confirmation as a box."

Sharpened 2026-07-27: **once a replicate has been opened in the filter tab, its
geometry is locked.** An edit is refused, the user is told what the edit would
cost, and if they accept that they get the move.

## Why this is not the pattern the save decision rejected

`docs/todo/no-save-prompts-keep-history.md` settled that rollback, not
confirmation, is the safety net — the user is not asked to predict mistakes.
This item was deferred on the reading that it contradicted that, and briefly
closed on it. **That reading was wrong**, and the difference is the condition:

- A modal in front of *every* geometry edit asks the user to predict a mistake.
  That is the rejected pattern.
- A lock that engages *only after the geometry has been tuned against* protects
  an invariant. The user is not being asked to foresee an error; they are being
  told that work exists downstream of the thing they are about to move. That
  information is not recoverable from the gesture itself, and undo does not
  substitute for it — undo restores the geometry, but the user has to know to
  reach for it, and the cost is paid in recomputation either way.

Rollback stays the net for the accidental case. This is the deliberate case.

## Decided 2026.07.27: visitation is recorded, and the lock refuses first

**The trigger is "was ever opened in the filter tab", not "has pins."** Deriving
it from non-empty `Replicate.overrides` / `detector_overrides`
(`replicates.py:77,87`) would have been free and needed no new state, and it was
rejected: a replicate can be opened, looked at, and used to validate the
*shared baseline* without ever taking a pin of its own. That is real tuning done
against that geometry and it leaves no deviation behind, so the derived version
would leave exactly those replicates unlocked.

**Where the visitation set lives is settled by rule 7, and the item's own prior
gap.** It must not sit on `Replicate`: identity there is `replicate_id`, the
geometry is hashed, and whether the GUI interposes a dialog changes nothing
about what a result *is*. It goes on `Project`, unhashed, beside `checkpoints`
and `outputs` (`pipeline_model.py:689-690`) — the same construction, for the
same reason, and their docstring already states the test ("recorded here and
never hashed … that must not change a single cache key"). A set of
`replicate_id`s is the shape.

It persists with the project. Reopening a file and dragging a replicate that was
tuned last week must warn; a lock that evaporates on close protects only the
session that did not need it.

**The lock refuses, then offers the move.** Rejected alternatives — *allow and
warn afterwards*, where the warning arrives after the thing it warns about; and
*confirm per drag with no accept path*, which is the every-time modal above.

The exact sequence, specified 2026-07-27:

1. The drag runs normally and the box follows the pointer. Nothing is
   interrupted mid-gesture, and no dialog ever appears under a held button.
2. **On release**, the dialog. This is the merged-command boundary — one drag,
   one question — which is why the note below insists the hook is
   `SetReplicateROI` and not `set_roi`.
3. **Declined: the box snaps back and nothing happened.** Not an edit followed
   by an undo — no command reaches the stack at all, so the undo history has no
   entry to step through and the document never went dirty. The user should be
   unable to tell afterwards that they dragged.
4. **Accepted: the new position is kept and every result computed against the
   old one goes stale.** Functionally a new replicate.

"Functionally a new replicate" has a consequence worth stating: **the lock
re-arms.** The replicate leaves the visitation set on an accepted move, because
it has not been opened in the filter tab *at this geometry*. It locks again the
next time it is.

Note that staleness needs no mechanism — the ROI is hashed, so a moved box
misses every cache entry keyed on the old one by construction. `replicate_id`
therefore does **not** need to be regenerated to make the data go away, and
should not be: it is what `overrides`, the visitation set, and the undo history
are all keyed on, and rotating it would orphan the lot to achieve an
invalidation the hash already gives for free.

**Be concrete about the loss, because rule 6 applies to warnings too.** "New
replicate" is the right description of the *results*, not of the settings.
Moving the ROI moves hashed geometry, so:

- Parameters **survive** — `overrides` and `detector_overrides` are pins, not
  results, and they re-resolve against the new geometry untouched.
- Everything *computed* against the old geometry is **stale**: every cache entry
  keyed on it, the collected series, the band power, the detections. The next
  look recomputes from scratch.

Decided 2026-07-27: **pins survive an accepted move.** They were never
invalidated by the geometry moving — an override is a parameter choice, and it
re-resolves against the new box unchanged. *Rejected side:* clearing them too,
for consistency with "functionally a new replicate", which would take from the
user something the move did not cost them.

So the warning is about recomputation, not about settings, and **it enumerates
both sides explicitly** — what stays, then what goes — rather than warning in
general terms. It costs a line of dialog and removes any ambiguity about what
was agreed to.

"You may lose your work" is the kind of overstatement rule 6 forbids in the
other direction, and it is worse than useless here: a user who has been told
their tuning is at risk will decline moves that were free, and will stop reading
the box by the third time.

## Implementation notes carried over

`ReplicateDocument` already has undo for ROI edits, with `SetReplicateROI`
merging per press token so one drag is one undo entry (`docs/TODO.md`'s settled
table). **The refusal must hang off the merged command, not off `set_roi`** — the
latter fires per mouse-move and would put a dialog under the pointer mid-drag.
That distinction has already bitten a test once: the settled table records that
a drag with a single mouse-move cannot see merge behaviour at all, so a test
here needs at least two.

Tests: a replicate never opened in the filter tab drags freely; declining on a
locked one leaves the geometry exactly as it was **and pushes nothing onto the
undo stack**; accepting keeps the new position and drops the replicate from the
visitation set; the visitation set survives a save/load round trip; and adding a
replicate id to it does not change any cache key. The drag tests need at least
two mouse-moves — one cannot see merge behaviour at all.
