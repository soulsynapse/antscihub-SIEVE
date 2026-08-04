---
title: "`slider_to_graph` names a gesture two other budgets now time"
status: open
priority: unassessed
opened: 2026-07-25
gated_on: >
  nothing — the trigger this item was written against ("a parameter control
  bound to a node") fired, and what is left is a decision about the budget
  table rather than a panel to build
reads:
  - src/sieve/bench/budgets.py
  - src/sieve/gui/param_form.py
  - src/sieve/gui/filter_tab.py
---

# `slider_to_graph` names a gesture two other budgets now time

**The premise this item was deferred on is false.** It said "there is no widget
anywhere that changes a node's params, so there is no drag for the ceiling to
describe". `gui/param_form.py` now builds a settings surface from any filter's
registered params model and routes edits through `document.edit_params`
(`filter_tab.py:2063`), and the downsample spin box has been writing
`rescale.scale` and `block_signal.scale` on `valueChanged` since the parity
work. The panel exists; `slider_to_graph` is still in `WITHOUT_PRODUCER`, and
the comment beside it still says it is "waiting on there being a slider at
all".

**Two rows already time that gesture end to end.** An upstream knob edit arms
`_knob_armed_at` and publishes `knob_to_first_partial` (500 ms, "when could I
start reading it") and `knob_to_graphs` (3000 ms, "when is it complete"). A
third row, `band_drag_repaint` (50 ms), covers the continuous cheap tier. So
the interval `slider_to_graph` describes is not unmeasured — it is measured
twice, against different ceilings.

## The decision

`slider_to_graph`'s 200 ms was anchored to a gesture that **decodes nothing**:
the item's own words were that the drag "is supposed to decode nothing at all",
every frame already in the store, two perceptual beats from knob to redrawn
graph. `knob_to_graphs` folds that case in and prices it at 3000 ms, because
its comment says the store rather than speed is what meets the ceiling after
the first render — which means the all-cached edit, the one case where 200 ms
is the honest bar, is currently adjudicated against a ceiling fifteen times
looser and can regress without anything firing.

Three ways out, and the item exists to pick one rather than let the row sit in
`WITHOUT_PRODUCER` describing work that has been done:

1. **Publish it, conditioned on a store hit.** The arm already exists; the
   render knows whether it decoded. A row that only fires when nothing was
   decoded is the 200 ms claim stated honestly, and it is the only option that
   keeps the tight ceiling on the case that deserves it.
2. **Retire the row.** `knob_to_first_partial` and `knob_to_graphs` are the
   intervals a user actually waits through, and a third row over the same
   gesture is a ceiling nobody reads. Cheapest, and it gives up the cached-edit
   guarantee.
3. **Redefine it in place.** Rejected before it is proposed, for the reason
   `knob_to_first_partial`'s own comment gives about why *it* was added as a
   second row: redefining a key silently rewrites what the findings already
   written against it measured.

**Recommendation: (1), and measure before setting the condition.** Whether a
knob edit over a warm store lands near 200 ms is not recorded anywhere, and if
it does not, (1) is a budget that fires constantly and (2) becomes right. Take
the number first; it belongs in `docs/findings/` either way.

Whichever lands, `WITHOUT_PRODUCER`'s comment loses its "waiting on there being
a slider" clause and the pointer to this file, because both are now false.
