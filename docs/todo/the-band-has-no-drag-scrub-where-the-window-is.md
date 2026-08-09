---
title: The band has no drag scrub where the window is, and the window opens over everything
priority: normal
phase: 9
status: open
gated_on: nothing
done_when: "uv run pytest -q tests/gui/test_timeline.py::TestTheDragScrubSurvivesTheWindow"
opened: 2026-08-09
---

# The band has no drag scrub where the window is, and the window opens over everything

09.6 gave the working window's whole interior to the move gesture. That was the
item's instruction and the implementation is faithful to it, but it took two
gestures off those pixels and gave one back. The click seek returns as a press
that never travels; the drag — press, move, watch frames arrive, release — has
no equivalent, because travel is what makes the gesture a move. Measured in
`findings/2026.08.09-a-drag-inside-the-window-scrubs-nothing-and-the-bar-opens-inside-it.md`:
at the window the bar opens with, a drag across the band emits no `scrubbed`,
no `committed`, and one `window_moved` carrying the origin the window already
had.

The live preview is the half of the tuning loop the band exists for — VISION's
constraint is that graphs refill faster than the video plays, and the gesture
that exercises it is dragging, not clicking. So this needs a ruling and not a
patch. The three shapes available: a modifier that turns a body press back into
a scrub; the playhead itself becoming the drag surface inside the window; or
the move gesture giving back some of the pixels it took, which is what the
HANDLES toggle was introduced to avoid. `MockStrip` cannot settle it — the
mockup's strip has no playhead at all, so the referent never had the collision.

Whatever lands, the case has to drive `TimelineBar` and not the bare `strip`
fixture. Every existing case that asserts `scrubbed` uses a strip with no
window, where `grab_at` returns SCRUB everywhere; the bar cannot be in that
state, which is why nothing went red for this.
