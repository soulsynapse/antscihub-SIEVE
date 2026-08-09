---
title: A declared surface is drawn by nothing, so a band still has no handles
priority: high
phase: 9
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k band_surface"
opened: 2026-08-09
---

# A declared surface is drawn by nothing

The declaration and the channel landed
([a-bands-axis-has-no-vocabulary-and-no-plot.md](a-bands-axis-has-no-vocabulary-and-no-plot.md)):
a band names a `DisplaySurface`, `detect` names three, and `execute(..., show=)`
fills them frame by frame beside the outputs. Nothing draws what comes back.
Three things stand between the channel and the ruling's own sentence about the
tuning centerpiece, and one commit is all three because none of them is worth
anything alone:

`PreviewSession` has no way to ask for a surface — the request stops at
`execute`'s keyword, so the GUI cannot reach it at all. Whatever assembles the
columns into a picture is `pipeline/series_collector.py`'s shape one dimension
wider: the collector stacks one value per frame and a surface is `(F, 1)` or
`(B, 1)` per frame, so what it holds is an image rather than a trace, and
whether that is the same class with a wider row or a second one beside it is
open. And the band editor itself, which
[composite-kinds-get-their-editors.md](composite-kinds-get-their-editors.md)
deferred outright: `REGION` got the canvas draw and `SPAN` got the timeline
handles, `BAND` got neither because there was no surface to hang handles on.
Now there is, and the editor generates per surface kind rather than per tool
(`adr/gui-knows-kinds-not-tools.md`) — three kinds, three ways to place a pair
of horizontal cuts, and `detect` supplying all three at once.

VISION's `Band drag → graphs repaint` row is the budget this is measured
against, and it is the first thing here that can be measured at all.

## Added 2026-08-09 at review: what the budget is up against

Measure before the picture is built rather than after, because the shape the
channel landed in is redundant by roughly the window length. `detect.display`
runs the whole gate chain a second time and then `morlet_power_profile` over
the *whole* bank — where `run` sums only the band's rows — and returns one
column of each, discarding the rest of a window that is `warmup + lookahead + 1`
frames wide. At `golden_params` that is 59 frames of transform per frame of
output, thrown away but for one column, on top of `run`'s own chain; and a
watched node is not served from the store, so none of it is amortized across a
re-drag. Whether the fix is a filler handed the span rather than the window, a
surface memoized across the frames of one drag, or the budget simply being met
anyway, is what the measurement decides — but a picture assembled first will
make the second of those look like a change to the drawing code rather than to
the channel.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/gui -q -k band_surface
    122 deselected in 0.63s
    exit: 5
