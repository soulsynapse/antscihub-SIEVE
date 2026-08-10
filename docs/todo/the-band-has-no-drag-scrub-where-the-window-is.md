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

Noticed 2026-08-10, same fact read from the other side: `tests/gui/test_app.py`
says "the bar holds no window until something asks for one" and then sets one,
and both halves are dead. `TimelineBar._on_opened` calls `bind_source`, which
adopts `whole_of(frame_count)` — so by the time that line runs the bar already
holds the whole source, the `set_window` beside the comment restates a span the
bar chose for itself, and the comment describes a shape the code has left
behind. Whatever settles the gesture is written against a bar that is never
windowless once a container is open, so the correction belongs beside it rather
than as a second answer to when the bar has a window.

## 2026-08-10 at review: what the criterion above does not reach

The fold is in the right home — the paragraph is a constraint on how this item's
own case must be written — but `done_when` is a pytest node on the gesture and
cannot see two dead lines in another file. The review that closes this item
checks the correction landed as well as the class going green:

    grep -c "holds no window" tests/gui/test_app.py    # 0

Left in prose rather than folded into `done_when` because a criterion is one
string and this is a second command; the shape is
[a folded item outgrows a criterion that cannot be widened to match](../findings/loop/2026.08.08-a-folded-item-outgrows-a-criterion-that-cannot-be-widened-to-match.md),
amended the same day with this instance.
