---
title: Hover to peek
status: open
opened: 2026-07-27
gated_on: >
  nothing structurally — but the collision with the block readout needs a rule
  chosen before any code, and the geometry item lands first
reads:
  - src/sieve/gui/composite_view.py
  - src/sieve/gui/video_view.py
---

# Hover to peek

Noticed `<=2026.07.27`: "instead of shift to peek, it should just let you hover
with mouse to peek."

Peek exists and works: `_CompositePane.peek` (`composite_view.py:143`) drops
every overlay so the frame underneath can be read bare, `paintEvent` honours it
at `:229` and `:234`, and the trigger is a Shift key watched at the application
level (`:349`, `:473-481`) so it works wherever the pointer is.

**The obstacle is a collision, and it must be resolved before code is written.**
Hover already means something on this exact widget: `mouseMoveEvent`
(`composite_view.py:188-193`) emits `hover_changed` with the block index under
the cursor, and the view's footer replaces its idle caption with that readout
(`:497`). "Hover to peek" and "hover to read a block" cannot both be the
unqualified meaning of moving the mouse over the grid. Candidate rules, none
obviously right:

- **Dwell.** Peek after the pointer is still for some interval; a moving
  pointer means block readout. Adds a timer and a "how long" number nobody has
  a basis for yet.
- **Outside the grid only.** Peek when the pointer is over the image but off
  `grid_rect` (`:170`); the readout keeps the grid. Cheap and stateless, but
  useless when the grid fills the image, which is the normal case.
- **Grid off.** Peek on hover only when `set_grid_visible` is false
  (`:388-389`) — there is no readout to collide with then. Honest, but it means
  the gesture is absent exactly when the overlay is heaviest.

Pick one, write down why, and keep Shift working as the unconditional override
regardless — it is the only trigger that works while a drag is in progress.

Do this after `docs/todo/zoom-on-the-composite-view.md`: peek is decided by
where the pointer is relative to the grid, and zoom moves that mapping.

Tests: the chosen rule engages and disengages peek without ever losing the
block readout it shares the widget with; Shift still peeks under every state of
the new rule; and leaving the widget clears both.
