---
title: Seeker upgrades
status: open
opened: 2026-07-27
gated_on: >
  nothing structurally — this is item 8's ungated half; the tick and coverage
  half is the deferred coverage-lanes item and stays there
reads:
  - src/sieve/gui/timeline_bar.py
  - mockups/seeker/seeker_bar.py
  - src/sieve/gui/video_view.py
---

# Seeker upgrades

Item 8 of `docs/filter-tab-parity-plan.md`, **split on 2026.07.27 by what has a
producer.** The original item bundled bracket manipulation, the hover bubble,
detection ticks, and coverage tint into one entry; the first two can be built
today against state that already exists and the last two cannot, and bundling
them is what kept the whole thing untaken through three sessions. The tick and
coverage half now lives in `docs/todo/coverage-and-detection-lanes.md` — see
that item for why they must land together and not before.

**The variant is settled: `lanes`.** One strip carries it all, 64 px, ticks and
window header sharing the top edge. `split` is not built. If the top edge turns
out to crowd where ticks, the header, and the playhead flag coincide — the case
`mockups/seeker/README.md` said to feel for — that is a reason to revisit the
lane layout at tick time, not a reason to keep a second variant alive now.

## What has already landed — do not rebuild it

More of the mockup is real than the parity plan admits, because the plan is a
dated record and was not updated as pieces landed:

- **Length lockstep is done.** `_length_box` ↔ `document.set_window_length`,
  with `_write_boxes` (`timeline_bar.py:255-259, 338-352, 363-366`) keeping the
  spinbox and the window in step, ranged against fps and duration. The parity
  plan still lists "bracket + Length lockstep" as item-8 work; only the bracket
  half is outstanding.
- **The mapping is done and is not the strip's.** `Geometry`
  (`timeline_model.py`) is rebuilt per paint and per click (`geometry_now`,
  `timeline_bar.py:121-128`), deliberately uncached because width changes under
  the user and frame count under the file.
- **The strip owns no truth**, and must not start. Window is the document's,
  playhead is the player's; the module docstring argues why a copy of either
  here is the copy that goes stale.
- **The three-event scrub contract is done** and is unchanged by this item:
  press = commit, move = guess, release = commit
  (`timeline_bar.py:180-198`).

## What to build

**One. The window bracket is grabbable.** Edge handles resize, the header band
(the darker strip along the window's top) moves it whole, minimum 1 s, anything
else is a scrub. Hit order: edge (6 px) > header > scrub.

Three things this must not get wrong, each of which is a real defect and not a
polish note:

- **A press that lands on an edge must not seek.** `mousePressEvent`
  (`:180-185`) currently emits `pressed` unconditionally, and `pressed` is the
  seek. Grabbing the window's left handle would jump the playhead to it before
  the resize even starts. The press has to classify first and only emit
  `pressed` in the scrub case.
- **Hit-test the handles before containment**, which is the rule
  `video_view.py` already settled for crop handles and `docs/TODO.md`'s table
  records. A point on the edge is inside the window too; testing containment
  first makes the edge unreachable.
- **Commit on release only.** `SetClip` (`commands.py:366-393`) has no
  `mergeWith` and no `id()`, so it does not merge — a drag pushing one command
  per mouse-move is one undo entry per pixel travelled. This is the two-tier
  rule the mockup states for its own reason (continuous moves update the
  outline, release commits and triggers the re-render); here it is also the
  only thing standing between a window drag and a shredded undo stack. Paint
  the drag from a local outline, write through `SetClip` once.

**Two. The hover bubble.** Timecode + frame, floating at the strip's top,
clamped to the widget so it never follows the cursor off-screen. Its coverage
line and its nearest-detection line belong to the deferred item and are absent
here — the bubble ships with the two facts that have a producer, and gains the
other two when they do.

`mouseMoveEvent` (`:187-191`) returns early unless `_dragging`, and the widget
does not call `setMouseTracking(True)` — `composite_view.py:144` and
`video_view.py:176` are the two places that do, and are the pattern. A
`leaveEvent` to clear the bubble is required; the composite pane's
(`composite_view.py:195-199`) is the shape.

## Tests

The bracket and the spinbox can never disagree after a drag; a press on an edge
resizes without moving the playhead; a drag shorter than 1 s is refused rather
than committed; one window drag is one undo entry; and the bubble clears on
leave. `window_rect` (`:130-141`) exists precisely because a painted pixel is
not something a test can ask about — extend that exposure rather than testing
paint output.

## When this lands

`mockups/seeker/` is deleted, per `mockups/README.md`'s convention that a
mockup goes once the widget lands and the decision is written down. The
interaction contract survives in `docs/filter-tab-parity-plan.md` §Seeker and
in this item; nothing is copied out of the mockup into `src/`.
