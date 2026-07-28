---
title: Hover to solo
status: open
opened: 2026-07-27
gated_on: >
  nothing — the rule is decided (2026-07-27, below); this was filed against the
  wrong mechanism and the collision it described does not exist
reads:
  - src/sieve/gui/composite_view.py
  - src/sieve/gui/filter_tab.py
---

# Hover to solo

Noticed `<=2026.07.27`: "instead of shift to peek, it should just let you hover
with mouse to peek."

**This item was filed against the wrong mechanism.** Clarified 2026-07-27: the
gesture meant is *solo* — the one the caption calls `CLICK TO SOLO` — not
*peek*. The two are separate and only the first is in scope.

- **solo** — a grid click emits `solo_toggled` (`composite_view.py:276-283`),
  `DetectorState.solo_block` holds it, and the soloed block's trace is overlaid
  on the density plot (`filter_tab.py:952-954`). This is what should follow the
  pointer.
- **peek** — Shift drops every overlay so the frame underneath reads bare
  (`:565-573`, honoured at `:309` and `:314`). **Untouched by this item.** It
  stays on Shift, application-level, and remains the only trigger that works
  while a drag is in progress.

The earlier draft of this file argued a three-way collision between "hover to
peek" and the block readout, and asked for dwell, or grid-off, or
outside-the-grid-only. None of that applies: peek is not moving to hover, so
nothing collides with the footer readout, which keeps working as it does now.

## Decided 2026.07.27: hover previews, click pins

Solo has two tiers. **Hover solos transiently** — the block under the pointer is
soloed as you move. **Click latches** the block under the cursor, and a latched
block survives the pointer leaving the grid. `leaveEvent` (`:269-274`) reverts
to the latched block, or to none if nothing is latched.

The reason is that the point of soloing is to *look at the trace*, and the trace
is drawn in the density plot, which is not the grid. A rule where solo is
strictly the block under the pointer destroys the thing it was asked for at the
instant the user looks at it.

*Rejected sides:* solo clears on leave — simplest, and self-defeating for the
reason above. Last-hovered sticks with no click tier — needs no new state, but
leaves no way to clear solo and no way to say "I meant this one", so every
traverse of the grid on the way to somewhere else rewrites what you were
looking at.

## What makes this cheap, and the one thing to measure

`hover_changed` already fires only when the block under the pointer *changes*
(`:262-267`), not per mouse sample, and `_refresh_hover` (`:255-260`) keeps that
true across a zoom. So the wiring is hover into `_on_solo` (`filter_tab.py:1410`)
alongside the existing `solo_toggled`, not a new event path.

Solo re-derives through `_derive(reuse_band_power=True)` — the cheap tier that
runs no transform at all and reuses the retained band power
(`filter_tab.py:863-877`). One block crossing therefore costs one cheap-tier
re-derive on the GUI thread. That is the right order of magnitude, but it is a
reading and not a measurement: **traversing the grid diagonally is now a burst
of re-derives at pointer speed, where before it took a click each.** Measure it
before assuming the cheap tier is cheap enough at that rate. If it is not, the
fix is coalescing on a zero-timer, not a dwell delay — the gesture should stay
immediate.

Solo stays *looking, not tuning*: it never reaches the document or a save
(`filter_tab.py:1411-1413`, `chain_model.py:214`), which is what makes it safe
to drive from something as involuntary as pointer position.

Tests: hovering across blocks solos each in turn without a click; leaving the
grid with nothing latched clears solo, and with a block latched reverts to it;
a click latches the hovered block and a second click on it un-latches; Shift
still peeks under every state of the above; and the footer block readout is
unaffected throughout.
