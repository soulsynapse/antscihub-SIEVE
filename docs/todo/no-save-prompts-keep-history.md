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
`docs/todo/confirm-before-changing-the-replicate.md` is closed by this — a
modal in front of a geometry edit is the pattern being removed one screen over.
*Rejected side:* confirmation as the net, which would have made automatic
history redundant for the case it covers and left the user answering a question
about a mistake they have not made yet.

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

This item is now scoped to *the autosave half only*. Prompt removal is its own
item, taken after this one lands; 300–500 lines with a new store does not fit
one context window alongside the removal, which is why they are two.

The estimates above are readings of the current code, not measurements.
