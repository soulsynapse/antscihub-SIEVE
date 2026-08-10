---
title: The tuning loop draws the baseline while the fan is standing on a region
priority: high
phase: 9
status: open
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
