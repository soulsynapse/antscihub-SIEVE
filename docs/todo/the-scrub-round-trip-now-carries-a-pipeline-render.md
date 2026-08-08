---
title: The scrub round trip now carries a pipeline render, and the degradation it can trigger is a decode remedy
priority: high
phase: "7"
status: deferred
deferred_for: decision
gated_on: whether the viewport's render belongs inside the transport round trip — which cannot be settled without saying what `slider_to_preview` then measures, and which of the four readings below the ceiling is meant to hold
opened: 2026-08-08
---

# The scrub round trip now carries a pipeline render, and the degradation it can trigger is a decode remedy

07.12 put the viewport's render inside `VideoPlayer._on_arrival`. The window's
`_on_frame_changed` slot is connected to `frame_changed`, and it calls
`app._paint_viewport`, which calls `tuning.render_at`, which runs
`preview.render_frame` synchronously on the GUI thread. `player.py` publishes
`scrub_to_repaint` *after* that emit, deliberately, so the number covers the
picture the user is scrubbing to — the finding
(`findings/2026.08.08-the-loop-budget-is-met-through-the-gui.md`, 2026-08-08
amendment) records the charge as 2.87 → 5.38 ms and argues it is worth paying.
The measurement is not in dispute. Two consequences of *where* the render sits
are, and neither is written down anywhere a reader would meet them.

**The same number is the degradation trigger.** `player.py` hands
`round_trip_ms` to `ScrubPolicy.observe` on the line after it publishes it, and
the policy's threshold is `BUDGETS["scrub_to_repaint"].limit_ms` — the comment
above it says the trigger and the documented ceiling must not drift apart. So a
pipeline slow enough now degrades the *transport* into coarse mode and emits
`scrub_degraded`, whose notice the window words for the user. Coarse mode snaps
requests onto a grid, which is a remedy aimed at decode; it reduces the render
count only incidentally, by asking for repeated indices. Every number in the
finding is 160x120, which is the caveat that file leads with — the render scales
with pixels and the ~2.6 ms of thread-hop overhead does not, so the ratio that
makes this benign today is exactly the one that moves on real footage.

**Playback pays a render per displayed frame.** The same slot runs during
playback, once per frame the transport delivers. Playback already drops frames
by design, so nothing breaks; what changes is the achieved rate, and the item
that ported the transport (`transport-and-timeline-port-into-the-skeleton.md`)
left "render-fed playback needs a window render in the GUI" as a note about a
capability that did not exist. It exists now, one frame at a time, on the path
that was measured as decode.

What has to be decided: whether the viewport's render belongs inside the round
trip at all. The options are not equivalent and this item does not rule between
them. Keeping it there is what makes `slider_to_preview` mean a repaint, which
is 07.12's whole point — so moving the render off the slot cannot be done
without saying what the key then measures. Feeding `ScrubPolicy` the decode leg
alone while publishing the whole round trip splits one number into two and the
comment above `_SCRUB_BUDGET_MS` argues against exactly that. Leaving it and
raising the policy's threshold gives up the ceiling's meaning. A fourth is to
let the render be skipped while a drag is in flight and painted on the settle,
which is the shape `RequestKind.SCRUB` already exists to express.

Deferred on the decision rather than left open with a criterion: what a test
would assert here *is* the fork — a case pinning the render out of the round
trip and a case pinning `slider_to_preview` to a repaint are the same test with
opposite signs, so writing one now rules by the back door.
