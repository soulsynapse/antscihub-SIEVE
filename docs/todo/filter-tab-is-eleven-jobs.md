---
title: filter_tab.py is eleven jobs in one widget
status: open
priority: unassessed
opened: 2026-07-28T12:57:15-07:00

gated_on: >
  nothing structurally — but take it one named responsibility per item, never
  as one split

reads:
  - src/sieve/gui/filter_tab.py
  - src/sieve/gui/wizard_model.py
  - src/sieve/gui/composite_view.py
  - tests/gui/test_filter_tab.py
---

# filter_tab.py is eleven jobs in one widget

> **One line added 2026-07-29:** the model-side extractions come first. The
> jobs that reach into `chain_model`/`detector_worker` internals (render
> pacing, detector orchestration, the cheap/expensive drag tiers) shrink to
> signal wiring when `detection-is-a-filter` and `detector-state-dies` land —
> attacking them here first would move the tangle around inside one file.
> The three seams below are the ones this item still owns either way.
>
> **2026-08-05:** two of those three no longer live here. The source boundary
> became its own item, the band handlers became a deferred one, and the
> composite was struck as a measured non-seam. What this item still holds is
> the wizard, the plan, and the seam test.

2,425 lines, one `QWidget`, about ninety-five methods. The responsibilities are
nameable from the outline alone: widget construction, layout, chain editing,
param submission to the document, detector orchestration and failure handling,
render lifecycle and per-frame cost telemetry, composite compositing and
cropping, band drag/commit for three separate plots, the whole wizard lifecycle,
transient solo and D-key state, and the HUD.

This is the one file in the repo where "who owns this" has no answer.

**Why it is not one item, and must not be attempted as one.** The coupling here
is Qt signal wiring, and that is invisible to both gates: a `connect()` call is
equally well-typed whichever object it lands on, and `.importlinter` sees
nothing because it is all one package. A bad split produces two files that each
need the other, and `tests/gui/test_filter_tab.py` passes throughout. The gate
that protects every other refactor in this repo does not protect this one, which
is the whole reason to go slowly.

**The unit is one named responsibility, one commit.** The order below was
reordered on 2026-08-05 against the measurement `filter-tab-many-secrets`
gathered on 2026-08-04 and then declined to act on. Ordering the seams by
reading the outline and ordering them by their commit history give opposite
answers, and the history is the one that has been right twice.

1. **The source boundary** — now `the-source-boundary-is-its-own-object`,
   taken out of this list because it is the only slice with evidence and
   because it wants to land before
   `the-graph-carries-the-crop-the-span-and-the-detector`. It was never on
   this list, which is the reading-the-outline failure in one line: the
   section three commits have stayed 85–92% inside is the one the outline
   made look least like a job.
2. **The wizard lifecycle** — `_open_wizard`, `_on_chain_proposed`,
   `_on_hover_preview`, `_on_hover_ended`, `_on_wizard_accepted`,
   `_on_wizard_cancelled`, `_close_wizard`, `wizard`. Roughly 150 lines, and
   `gui/wizard_model.py` is already the state half waiting for it. Git says
   nothing either way — `wizard.py` and `wizard_model.py` have never changed
   without `filter_tab.py`, so the wizard lifecycle has never earned its own
   commit — which means this rests entirely on the signal-crossing test below,
   and that judgement is cheaper made after `detector-state-dies`.
3. **The band drag/commit handlers** — moved to
   `the-band-handlers-are-one-shape-said-five-times`, `status: deferred`,
   because `detector-state-dies` deletes `reuse_band_power` and may leave
   fewer than three handlers to factor.

**The composite is not a seam, and this is the third time that has been
measured.** `_composite_target`, `_composite_grabber`, `_refresh_composite`,
`_apply_composite`, `_update_composite_caption`, `_cropped_player_frame`,
`_release_composite_slot` were slice 2 here until 2026-08-05. Struck so it is
not re-proposed: `composite_view.py` co-changes with `filter_tab.py` 10 times
against 1 commit where it changes alone (`filter-tab-many-secrets`,
2026-08-04), which is CLAUDE.md's own 2026-07-28 reading of the same pair (5
and 1) confirmed six days later; and blame puts only 66% of `Draw the step
composite` inside the section, against 85–92% for the source boundary's three
commits. The composite refresh state machine is also the one piece the wizard's
hover preview calls into directly — `filter-tab-many-secrets` decision 4 into
decision 1 — so extracting it does not remove a job from this file, it adds an
edge between two.

**The test for a good seam, applied before writing code:** name the signals
that cross it. If the extracted object must hold a back-reference to the tab to
do its job, the seam is wrong and the right move is to route through the
document or emit a signal the tab connects — not to pass `self`.

**Do not** take this item as scaffolding for a model that has not read
`filter_tab.py` end to end. "Split filter_tab" is not a specification; each
numbered slice above is.
