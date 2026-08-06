---
title: The source boundary is its own object
status: open
opened: 2026-08-05T18:08:08-07:00
priority: high
gated_on: nothing structurally
reads:
  - src/sieve/gui/filter_tab.py
  - src/sieve/gui/materialize_worker.py
  - src/sieve/pipeline/crop_binding.py
  - tests/gui/test_crop_boundary.py
---

# The source boundary is its own object

`filter_tab.py`'s `# ---- the source boundary` section — the card's four-state
wording, the materialize gesture, the write-completion handlers, and discard —
is 213 lines that have never changed for the same reason as anything else in
the file. It is `filter-tab-is-eleven-jobs`' unit-of-one-responsibility rule
applied to the one slice with evidence behind it, and it is not on that item's
numbered list, which is the amendment that goes with this item.

**The seam is already drawn everywhere except in the source file.** The tests
split there: `tests/gui/test_crop_boundary.py` is 427 lines and imports
`FilterTab` only to drive it, while `test_filter_tab.py` is 182 lines with zero
references to crops, materialize, or the card. The collaborators are already
separate modules (`materialize_worker.py`, `crop_binding.py`, and `SourceCard`
in `chain_stack.py`). `filter-tab-many-secrets` measured the co-change and
found `materialize_worker`/`crop_binding` at 5 commits with `filter_tab.py`
against 33 where it changed alone — the loosest coupling in the file.
Blame agrees from inside: discounting the rollback and the initial assembly,
`The source boundary gets a card` put 119 of its 146 lines inside the section,
`The crop stops holding things still` 12 of 13, and `Move the Qt-free logic
out` 11 of 16. Nothing else in the file is that confined — the composite is
66%, the wizard 58%.

**Done is** `src/sieve/gui/source_boundary.py`: a `QObject` holding
`_refresh_source_card`, `_boundary_detail`, `_artifact_stamp`,
`_on_materialize`, `_on_crop_written`/`_failed`/`_cancelled`,
`_resume_after_write`, `_on_discard_crop`, the `MaterializeRunner`, the
`_writing_row` state, and the eight `document.*_changed` connections that
currently sit in `FilterTab._connect`. It is constructed with the
`ReplicateDocument` and the `SourceCard` — both downward reads — and emits
`render_hold(bool)`, `render_stale()`, and `status_message(str)`. `FilterTab`
keeps four lines: construct, connect three signals, forward `shutdown`, and
keep the `materializer` property the tests reach for.

That passes `filter-tab-is-eleven-jobs`' seam test as stated: name the signals
that cross, and hold no back-reference to the tab. The only reaches out of the
section today are `self._runner.set_paused` / `release_files` and
`self.resubmit()`, and those are exactly the three signals.

**The thing to not get wrong.** `_on_discard_crop` pauses the runner and calls
`release_files()` *synchronously* before `path.unlink`, because an open handle
makes the unlink fail on Windows — which is how that gesture came to silently
do nothing the first time. Both objects live on the GUI thread, so
`render_hold.emit(True)` runs its slot to completion before returning; the day
someone makes that connection queued, the delete races the release and the
gesture regresses to a no-op with no error anywhere. The emit carries a comment
saying so, and the regression check is the existing discard test in
`test_crop_boundary.py` asserting the file is gone.

**Take it before `the-graph-carries-the-crop-the-span-and-the-detector`.** That
item moves the ROI off `Replicate` and into the graph, which re-keys
`document.crop_backing(index)` from replicate index to node. Done in this
order, that is an edit to one 230-line file whose whole subject is the crop
boundary; done in the other order, it is an edit to a region inside 2,400 lines
and this extraction still has to happen afterwards. Most of the section does
not move under that item at all — the four-state wording, the full-source cut,
the verify-then-register pass, and the discard ordering all survive it. This is
a preference, not a gate, which is why it is stated here and not in that item's
`after:`.

**Nothing here is protected by a gate.** A `connect()` call is well-typed
wherever it lands and `.importlinter` sees one package, so `test_crop_boundary`
passes before and after either way. The review is by reading, and what to read
for is whether the controller ever needs something from the tab that is not one
of the three signals. If it does, the seam is wrong and this item stops.
