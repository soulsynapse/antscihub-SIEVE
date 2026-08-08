---
title: The viewport shows the source, so the repaint ceiling is measured on a render nobody sees
priority: high
phase: "7"
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/bench/test_gui_loop_budget.py -q -k the_frame_under_the_playhead_is_the_pipelines_and_not_the_sources"
opened: 2026-08-08
---

# The viewport shows the source, so the repaint ceiling is measured on a render nobody sees

`gui/canvas.VideoCanvas` is fed by `transport/player.py`, which decodes the
source and resamples it to `PROXY_WIDTH`. Nothing in the tree paints a frame the
pipeline produced. So the left half of the window shows the user their footage
while the graph under it shows their measurement, and moving a parameter changes
one of the two.

That is inside PLAN.md's first cut as written — "tune a param with the graphs
refilling inside the budget" names the graphs and not the picture — so this is a
gap by design rather than a defect in 07.11. What it costs is one budget row's
meaning. `slider_to_preview` is labelled "Slider drag → preview repaint" and
07.11 gates it through the GUI at 0.32 ms of 100 ms
(`findings/2026.08.08-the-loop-budget-is-met-through-the-gui.md`), which is
*lower* than the 1.95 ms it read headless — because headless it was a whole
`render_frame` and here it is the first frame of a window render on a warm
store. Two different gestures under one key, and the GUI's is the cheap one. A
green line that says the repaint ceiling is met by a factor of 300 is the shape
of compliance that `budgets.WITHOUT_PRODUCER` exists to keep out of the table,
arriving by a different route: not a ceiling with no producer, but a producer
that is not doing the thing the ceiling names.

What has to land: the canvas showing the watched node's output for the frame
under the playhead, refilled from the same store the graph is
(`pipeline/preview.render_frame` is the 100 ms path and has no caller in `gui/`).
Two decisions sit inside it and neither is settled here. A node emitting a
`(T, 1, 1)` gate has no image to show, so what the viewport falls back to when
the walk stands on the detector is a real question — the source, the last node
that had an image, or nothing. And the frame is in the node's own space rather
than the source's, which is the same denominator problem
`kind_editors.RegionEditor` answers for a drawn region: a viewport showing a
cropped frame is a viewport a region editor could then be offered on, which is
what `gui/app.source_fed_nodes` exists to refuse today.

`done_when` names a case in the GUI budget file rather than a new one, because
the claim is about that file's own subject: the key it gates has to be published
around a render the canvas then shows. Red today for the right reason — nothing
in `gui/` calls `render_frame`, so there is no frame to assert about.
