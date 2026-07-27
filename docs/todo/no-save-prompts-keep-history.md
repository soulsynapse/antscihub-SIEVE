---
title: No save prompts, keep history
status: open
opened: 2026-07-27
gated_on: >
  nothing structurally — but it is a policy decision two other items wait on,
  so decide it before building either half
reads:
  - src/sieve/gui/main_window.py
  - src/sieve/gui/document.py
  - src/sieve/core/pipeline_model.py
---

# No save prompts, keep history

Noticed `<=2026.07.27`: "it shouldn't ask to save the project or load the
project. But it should automatically keep project history so if the user messes
stuff up it can roll back."

**Decide the policy before building either half.** This item gates
`docs/todo/confirm-before-changing-the-replicate.md`, which asks for a modal in
front of a geometry edit — the same pattern this one removes. The two cannot
both be right: if rollback is the safety net, the user is not asked to predict
mistakes; if confirmation is the safety net, automatic history is redundant for
the case it covers. Answer it once, here, and record the rejected side.

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

This item is scoped to the *decision plus the cheap half*. If rollback is
chosen, split it out as its own item rather than growing this one — 300–500
lines with a new store does not fit one context window alongside the removal.

The estimates above are readings of the current code, not measurements.
