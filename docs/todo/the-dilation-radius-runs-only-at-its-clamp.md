---
title: The dilation radius runs only at its clamp
priority: low
phase: 4
status: open
gated_on: nothing
opened: 2026-08-07
---

# The dilation radius runs only at its clamp

`dilate_radius` returns `max(1, ceil(reach_blocks / (tau_seconds * fps)))`, and
every `dilate` case in `tests/unit/test_motion_history.py` runs where that
quotient is at most 1/15, so the clamp is what returns and the formula is
unexercised. Pinning it to `return 1` leaves all fifteen cases green
(`findings/2026.08.07-the-dilation-radius-is-the-one-motion-history-parameter-no-case-reaches.md`).

It is not decorative: it is how many blocks the dilation reaches per frame,
chosen so activity travels `reach_blocks` over one persistence time. A wrong one
produces a bloom of the wrong width that still stops growing and still sustains
its peak, which is every property the file currently asserts.

The reason it is not a one-line parametrize, and the reason this is `low` rather
than a decimal step: `SIDE = 41` and the `SIDE * SIDE // 3` guard were both
sized for `reach_blocks = 2`. Every configuration that lifts the radius above
its clamp blooms past that guard while still converging — 913 cells of 1681 at
`reach_blocks = 4, tau = 0.1`, the whole arena at `reach_blocks = 16` — so a
case that pins the radius brings its own geometry, and whoever writes it decides
what the assertion is: a golden at a reach the formula actually reads, or a
width the arena is wide enough to bound.

Nothing downstream waits on it. `04.8` reads `motion_history`'s output shape,
not its coupling width.
