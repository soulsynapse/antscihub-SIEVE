---
title: The drag swaps the viewport's picture for the source, and the surface has no mark
priority: high
phase: "7"
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k source_badge"
opened: 2026-08-09
---

# The drag swaps the viewport's picture for the source, and the surface has no mark

`e745856` carried out the 2026-08-09 render-on-settle ruling: while a drag is in
flight `app._paint_viewport` is called with `render=False`, so `set_values` is
never reached and the canvas is handed the decoded source frame instead. For a
walk standing on a node whose output does not look like footage — a
`block_signal` mask, a `temporal_baseline` difference — the viewport changes
*kind* of picture the moment the drag starts and changes back on release, and
nothing on the surface says which of the two the user is looking at. The bench
case the same commit added asserts exactly this in pixels
(`test_a_drag_shows_the_decoded_frame_and_the_release_shows_the_render`): the
dragged image and the settled image are the same source index and different
pictures.

The ruling's third bullet says this "falls under the honesty half of the budget
scope: input never blocks, and a stale frame is labeled stale". The first clause
holds. The second has no referent on this surface: the only stale mark in the
GUI is `graph_panel.mark_stale` / `_STALE_NOTICE`, which belongs to the trace,
and `app._redraw`'s own comment already names an unmarked viewport showing the
previous node's output as "the stale-mark interval leaking onto a surface that
has no mark". The commit made that interval longer and gave it a new cause, and
the sentence that was supposed to cover it points at a mechanism `canvas.py`
does not have.

What has to be decided, and why this is deferred rather than open with a
criterion: the two answers want opposite tests. Either the viewport gets a mark
— and then the question is what it marks, because the source fallback already
fires for three older reasons (no answer yet, a node with no picture, a render
that failed) that were reviewed and accepted unmarked, so a mark introduced for
the drag alone would label the newest cause and not the oldest ones. Or the
ruling is corrected: a source frame at the *correct* index is not stale, only
unrendered, and VISION's honesty half is about a picture that is behind the
playhead rather than about which node's output it is. That reading is defensible
and would make `docs/VISION.md`'s sentence the thing to sharpen, not `canvas.py`
— but it is a narrowing of a product promise, which is Kendrick's line and not a
worker's.

Whichever it is, the mark question is the same one the three older fallbacks
raise, so the answer should rule on all four causes at once rather than on the
drag by itself. `the-viewport-shows-the-source-and-not-the-render.md` (done)
settled that `_paint_viewport` is the single place the transport and the
pipeline meet, which is where any mark would be decided.

## 2026-08-09: ruled — the viewport gets the mark, over all four causes

Kendrick took the mark, with the vocabulary that dissolves the fork's other
half: the mark names *what is shown* ("source"), not "stale". A frame at the
correct index is not temporally stale, so VISION's sentence is not narrowed —
it gains a referent on this surface instead of losing its subject. One state,
decided at `_paint_viewport`, on whenever the picture is not the watched
node's current output: brief for a drag (release plus one settle render) and
for the first render in flight, indefinite after a failed render — which is
the honesty payoff, a failure no longer leaves plausible source frames up
unmarked — and permanent for a node with no picture. `status`, `gated_on`,
and `done_when` moved on that; the criterion is red at the ruling
(`124 deselected`, exit 5).

Two edges are the work's to settle, not re-decisions: whether the badge or
the mockup's `NO_SURFACE_NOTE` owns the no-picture case (two chromes saying
one thing would be a collision, and the referent's note predates this
ruling), and whether the badge doubles as the settle render's
progress-visible signal, which
`findings/2026.08.09-the-settles-render-is-charged-to-a-ceiling-the-gui-does-not-publish.md`
is adjacent to but does not rule.

## 2026-08-09: built — one state on the canvas, raised at the fallback

`VideoCanvas` holds `showing_source`, raised by `mark_source()` and lowered only
by a `set_values` that lands, and `_paint_viewport` raises it on the one branch
all four causes share. A refused `set_values` deliberately leaves it alone: the
caller's next statement hands the source back and marks it, and clearing in
between would drop the badge on every repaint of a node with no picture.

Both edges settled as work, not as re-decisions. `NO_SURFACE_NOTE` is the
pinned step's line for a step with *no plot* (`mockup.py`, `_plots_for` empty),
which is a different surface from the viewport's picture — no collision, and
neither owns the other's case. The badge does not double as the settle render's
progress signal: it names the picture, and a mark that also meant "work is in
flight" would be false in the two causes where no render is coming (a node with
no picture, a render that failed) — which is the honesty half it was added for.
