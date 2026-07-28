---
title: filter_tab.py is eleven jobs in one widget
status: open
opened: 2026-07-28

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

**The unit is one named responsibility, one commit.** Suggested order, easiest
seam first:

1. **The wizard lifecycle** — `_open_wizard`, `_on_chain_proposed`,
   `_on_hover_preview`, `_on_hover_ended`, `_on_wizard_accepted`,
   `_on_wizard_cancelled`, `_close_wizard`, `wizard`. Roughly 150 lines, and
   `gui/wizard_model.py` is already the state half waiting for it.
2. **The composite** — `_composite_target`, `_composite_grabber`,
   `_refresh_composite`, `_apply_composite`, `_update_composite_caption`,
   `_cropped_player_frame`, `_release_composite_slot`.
3. **The band drag/commit handlers** — `_on_freq_drag`/`_on_freq_commit`,
   `_on_value_drag`/`_on_value_band`, `_on_count_drag`/`_on_count_band`,
   `_count_frac_for`. Three plots repeating one shape.

**The test for a good seam, applied before writing code:** name the signals
that cross it. If the extracted object must hold a back-reference to the tab to
do its job, the seam is wrong and the right move is to route through the
document or emit a signal the tab connects — not to pass `self`.

**Do not** take this item as scaffolding for a model that has not read
`filter_tab.py` end to end. "Split filter_tab" is not a specification; each
numbered slice above is.
