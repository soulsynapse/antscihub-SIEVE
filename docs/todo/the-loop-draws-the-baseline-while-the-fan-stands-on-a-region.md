---
title: The tuning loop draws the baseline while the fan is standing on a region
priority: high
phase: 9
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k 'the_loop_renders_the_region_the_fan_is_standing_on'"
opened: 2026-08-09
---

# The tuning loop draws the baseline while the fan is standing on a region

`PreviewSession` takes a replicate and keys its store on one
(`pipeline/preview.py`, `set_replicate`). `TuningLoop` never hands it one, so
every render the window makes is the baseline's — and now that a knob edits the
selected region's own value, that is a picture of a region the fan is not
standing on.

It is invisible for as long as the user is editing, because
`Project.with_param_edit` moves the baseline alongside the pin: the region just
edited *is* the baseline, so the canvas and the graph agree with the last
gesture. It appears on the move between regions. Two regions each placed once,
then a click back onto the first square: the four spin boxes and the fan say
region 1, and the canvas is still cropping region 2's box, because nothing
between the click and the render carries which region the click chose.

`set_replicate`'s own docstring names the harder half — a session already
pointed at a written crop is aimed at *that* replicate's pixels, so re-aiming
one is refused there and the caller is told to rebuild. Which of the two the
window does is the question this item settles; what it must not do is keep
rendering a graph the surface has stopped describing. The store is keyed per
replicate, so the region a user clicks back to is a cache hit rather than a
re-render, which is what makes this an interactive-loop claim and not only a
correctness one (`docs/VISION.md`).

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/gui -q -k 'the_loop_renders_the_region_the_fan_is_standing_on'
    216 deselected in 0.67s
    exit: 5

## 2026-08-10 (work): re-aimed, not rebuilt

`done_when` now green:

    $ uv run pytest tests/gui -q -k 'the_loop_renders_the_region_the_fan_is_standing_on'
    1 passed, 232 deselected in 0.98s
    exit: 0

The question the item posed is settled the way its own last paragraph points:
the window re-aims the session (`TuningLoop.set_replicate` forwarding to
`PreviewSession.set_replicate`) and does not rebuild it. `set_replicate`'s
refusal is about a session reading a written crop, and the loop's session reads
the container the transport opened (`app._on_opened` hands it
`VideoMetadata.path`), so the refusal does not reach this caller — and rebuilding
would throw away the store, which is the cache hit the item names as what makes
this an interactive-loop claim rather than only a correctness one.

Pushed from `refill_graph`, beside the working window and for the same reason:
the bar owns the window and `_region` owns the selection, and a copy of either
inside the preview is the one that goes stale. That is also the one place it
needs to be, because every gesture that moves the selection redraws and every
redraw refills — and it aims both renders at once, the trace's and the
viewport's, since `_paint_viewport` runs `render_at` off the same session.

`selected_replicate` now derives from a new `selected_region`, so the window
still resolves `_region` against the document exactly once: the widgets take the
id and the preview takes the replicate.

What the case measures is the whole tail of the graph: two regions deviating at
the crop's box over `stirred_clip`, rendered at a node below the crop, before
and after a click onto the second square. Equal shapes and unequal pixels — the
shape half is what says the render *before* the click is aimed too, since a
baseline-aimed first render would be the whole frame.
