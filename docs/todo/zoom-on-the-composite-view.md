---
title: Zoom on the composite view
status: open
opened: 2026-07-27
gated_on: >
  nothing structurally — but do the geometry first of the three composite-view
  items, or the other two's hit-testing gets rewritten
reads:
  - src/sieve/gui/composite_view.py
  - src/sieve/gui/video_view.py
  - src/sieve/gui/filter_tab.py
---

# Zoom on the composite view

Noticed `<=2026.07.27` as "the zoom function should work on the replicate tab
too". **The bullet's tab names look inverted and that should be confirmed
before the first edit.** The replicate tab is `VideoView`
(`replicate_tab.py:82`), which has zoom today — `zoom_changed` is wired to the
tools panel's readout at `replicate_tab.py:175` and `fit_requested` back to
`reset_zoom` at `:179`. The tab with no zoom is the filter tab, whose view is
`StepCompositeView` (`filter_tab.py:254`). This item is written for that
reading; if the user meant something specific about the replicate tab's zoom
being wrong rather than absent, the item needs rescoping, not building.

`VideoView` already holds the whole mapping and its rules: `_zoom` clamped
between `MIN_ZOOM` and `MAX_ZOOM` (`video_view.py:188, 439`), a pan centre in
normalized source coordinates (`:189`), `view_rect` returning `content_rect`
itself at zoom 1.0 so a wheel-out storm cannot produce something smaller than
the fit (`:297-318`), and unrounded mapping because rounding makes the zoom
anchor drift (`:326`). None of that should be re-derived — the note in
`docs/TODO.md`'s settled table on crop gestures says `view_rect` is the mapping
and `content_rect` is only the floor it is clamped against, and that is the
part that costs a day.

**Do this one first of the three.** `_CompositePane.block_at`
(`composite_view.py:174`) and `_content_rect` (`:150`) map widget coordinates
to blocks against the un-zoomed content rect. Introducing zoom changes that
mapping. Hover-to-peek (`docs/todo/hover-to-peek.md`) and right-click-back
(`docs/todo/right-click-back-to-the-replicate-tab.md`) both add mouse handling
on the same pane; building either before the geometry moves means rewriting its
hit-testing afterwards. Batch all three as one composite-view pass, geometry
first.

Tests: a block hit-tested at zoom 1.0 is the same block after a zoom-in and pan
that keeps it under the cursor; zooming out cannot produce a view smaller than
the fit; and the grid overlay stays registered to the image at every zoom.
