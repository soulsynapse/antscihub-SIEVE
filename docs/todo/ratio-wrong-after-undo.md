---
title: Ratio wrong after undo
status: open
opened: 2026-07-27
gated_on: >
  nothing structurally — and take it first: two other items lean on selection
  and replicate signals firing reliably
reads:
  - src/sieve/gui/filter_tab.py
  - src/sieve/gui/document.py
---

# Ratio wrong after undo

Noticed `<=2026.07.27`: draw boxes, undo, click into a replicate, and the
aspect on screen is the *old* crop's. Two independent defects compose to
produce it, and either one alone would still be a hole.

**One.** `FilterTab._connect` (`src/sieve/gui/filter_tab.py:315`) subscribes to
`clip_changed`, `source_changed`, `selection_changed`, `tuning_changed`,
`detector_changed`, and `pipeline_changed` — but not `replicate_changed`
(`document.py:60`, emitted at `document.py:726`). A geometry edit therefore
never invalidates the composite. `SetReplicateROI`'s undo goes through
`replicate_changed` like every other ROI write, so Ctrl+Z on a crop leaves the
tab rendering the pre-undo geometry. The subscribers that *do* exist for
`replicate_changed` are `crop_tools.py:224`, `replicate_tab.py:184`, and
`replicate_table.py:70` — all on the replicate tab. Nothing downstream of the
crop listens.

**Two.** `ReplicateDocument.select` (`src/sieve/gui/document.py:454`)
early-returns on `index == self._selected`. That guard is right for its stated
purpose — selection is not a command, and re-emitting on a no-op select would
churn — but it means clicking into the replicate you are *already* on emits
nothing, so the one handler that would have papered over defect one
(`_on_selection_changed` → `resubmit`) never runs either. The user's gesture
looks like it should refresh and does not.

The fix is a `replicate_changed` connection on the tab plus a decision about
the `select` guard. Prefer fixing the missing subscription rather than
loosening the guard: a re-emit on identical selection would make `select` a
refresh primitive, which is not what its docstring says it is, and every other
caller would inherit that. ~5–15 lines.

This breaks the invariant that accepting a replicate always re-renders. The
**Stamp as the default gesture** item (`docs/todo/stamp-as-the-default-gesture.md`)
and any future selected-crop view inherit the same hole, which is why this one
goes first.

Two tests that fail for distinct reasons: undo of a crop edit repaints the
filter tab's composite; and selecting the already-selected row still leaves the
tab consistent with the document (whichever way the guard question lands).
