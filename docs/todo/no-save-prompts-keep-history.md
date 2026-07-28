---
title: No save prompts, keep history
status: open
opened: 2026-07-27
gated_on: >
  nothing — the policy is decided (2026-07-27, below); this item is now the
  autosave half, and the prompts come out only after it lands
reads:
  - src/sieve/gui/main_window.py
  - src/sieve/gui/document.py
  - src/sieve/core/pipeline_model.py
---

# No save prompts, keep history

Noticed `<=2026.07.27`: "it shouldn't ask to save the project or load the
project. But it should automatically keep project history so if the user messes
stuff up it can roll back."

## Decided 2026.07.27: rollback is the safety net, and it lands first

**Rollback, not confirmation.** The user is not asked to predict mistakes.
*Rejected side:* confirmation as the net, which would have made automatic
history redundant for the case it covers and left the user answering a question
about a mistake they have not made yet.

*Scope correction, same day.* This was first written as closing
`docs/todo/lock-a-visited-replicate.md`, on the reading that any box in front of
a geometry edit is the pattern being removed here. It is not. That item's box is
conditional on the replicate having been tuned against, which makes it a
statement about work that exists downstream rather than a request to foresee an
error. Rollback is the net for the accidental case; that lock is the deliberate
case. Both stand.

**Autosave lands before the prompts come out.** The obvious order is the wrong
one. `confirm_discard` exists because every path it guards silently destroyed a
session's work; that reason is transferred to autosave, not retired by deleting
the dialog. Removing the dialog first opens a window in which *neither* net is
in place. So: this item is the autosave half. The ~70–90 lines of prompt removal
follow it, as a separate item, and are trivial once history exists.
*Rejected side:* dialogs-first because it is cheap — cheap and unsafe in that
order, and the item's own reading of `confirm_discard` says why.

**A snapshot is keyed to an undo-stack entry**, not to wall-clock time. The
stack already knows what a user-meaningful action is (`SetReplicateROI` merges a
whole drag into one entry), and time-based snapshots cut across gestures.
*Rejected side:* interval autosave, which would have needed no new keying and
would have produced checkpoints in the middle of drags.

**The neighbour-project modal is not a save prompt and is settled separately:**
`_offer_neighbour_project` (`:524-543`) becomes `_open_neighbour_project` —
open it, then say so in the status bar. Its argument survives in the announcement
rather than in the question: the user still learns which project was restored and
from where, without being asked. That also dissolves the second placement
constraint in `docs/todo/video-autoplays.md`.
*Rejected side:* keeping the question, and silent restore with no announcement.

The two halves are wildly different in size.

**Killing the prompts is cheap: ~70–90 lines.** Three sites, all in
`main_window.py`. `confirm_discard` (`:444-468`) guards every path that
replaces or drops the document, and its docstring records why it exists — each
of those paths silently destroyed a session's work before it. That reason does
not go away when the dialog does; it is transferred to autosave, which is why
the halves cannot be sequenced dialog-first. `_offer_neighbour_project`
(`:524-543`) asks whether to open the project filed beside a video, and argues
that silently restoring twelve replicates the user cannot see the provenance of
is a worse surprise than one question — that argument survives this item and
should be answered, not deleted, if the modal goes. And `save_project` /
`_write_project` (`:505-522`) is the canonical write path, so autosave routes
through it rather than growing a second one; `undo_stack.setClean()` and
`_update_title` are already the dirty-state machinery an autosave trigger would
hang off.

**Rollback history is a new subsystem: ~300–500 lines.** A snapshot store, a
retention policy, and restore UI. None of it exists. The one real design
decision is what a snapshot is keyed to: undo-stack steps are the obvious
answer because the stack already knows what a user-meaningful action is
(`SetReplicateROI` merges a whole drag into one entry — `docs/TODO.md`'s
settled table), and time-based snapshots would cut across gestures. Note also
that `Project.save` writes a whole document, so "history" is a series of whole
documents unless someone decides otherwise; at replicate-scale that is fine and
at output-scale it may not be, which rule 7 already anticipates by keeping
`checkpoints` and `outputs` on `Project` rather than on `Node`.

**The subsystem's remaining decisions, settled 2026-07-27 so the item is
takeable without a design stop:**

- **Where snapshots live: a `<project>.history/` directory beside the project
  file.** Whole documents (per the rule-7 note above), named by monotonic
  sequence plus the undo action's text, so a directory listing already reads
  as history. *Rejected sides:* inside the project file — turns every
  snapshot into a rewrite of the artifact the CLI reads and makes history
  travel where preferences must not; an app-data directory keyed by project
  path — history that silently detaches when a project is moved or copied.
- **What is written and when: on undo-stack index change, coalesced to
  idle.** The keying decision above already picked the stack; coalescing
  means a burst of commands writes once, and writing routes through
  `_write_project` — the canonical path, not a second serializer.
- **Retention: the last 50 snapshots plus the first of each session.** At
  replicate scale a document is small enough that 50 whole copies are noise;
  the session-start snapshot is the "before today" restore point that pure
  LRU would age out mid-session. Revisit only when outputs make documents
  heavy — the rule-7 note above already anticipates which fields would do it.
  *Rejected side:* unbounded — a policy nobody chose, enforced by disk.
- **Restore is an undoable action, not an open.** File > History lists
  action text plus age; choosing one pushes a restore command onto the undo
  stack. Restoring is therefore itself covered by the net, and a mistaken
  restore is one Ctrl+Z, not a hunt through the history of histories.
  *Rejected side:* restore-as-file-open, which discards the stack and makes
  the safety mechanism the one destructive gesture in the app.

This item is now scoped to *the autosave half only*. Prompt removal is its own
item, taken after this one lands; 300–500 lines with a new store does not fit
one context window alongside the removal, which is why they are two.

The estimates above are readings of the current code, not measurements.
