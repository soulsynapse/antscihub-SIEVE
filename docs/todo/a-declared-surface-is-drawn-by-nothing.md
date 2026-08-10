---
title: A declared surface is drawn by nothing, so a band still has no handles
priority: high
phase: 9
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui tests/bench -q -k 'band_surface or band_drag_repaint'"
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

## Widened 2026-08-09 at review: the measurement has to be witnessed too

The section above was folded in by the review that minted this item, which said
in the same breath that `pytest tests/gui -q -k band_surface` would not witness
it — a picture that draws can be green while the cost stays unmeasured, which is
[a-folded-item-outgrows-a-criterion-that-cannot-be-widened-to-match](../findings/loop/2026.08.08-a-folded-item-outgrows-a-criterion-that-cannot-be-widened-to-match.md).
It is widened here rather than passed on. `band_drag_repaint` is already a real
row in `bench/budgets.py` and already declared in its `WITHOUT_PRODUCER` set —
the repo's own statement that nothing under `src/` measures it — so the second
half of this item is exactly the removal of that declaration, and
`test_declared_producerless_budgets_have_not_quietly_grown_one` goes red the
moment a producer appears without it. The criterion names the key, so a run that
draws the picture and leaves the budget unmeasured cannot report green.

`done_when` as widened, red because nothing matches:

    $ uv run pytest tests/gui tests/bench -q -k 'band_surface or band_drag_repaint'
    162 deselected in 0.66s
    exit: 5

`done_when` at minting, red because nothing matched:

    $ uv run pytest tests/gui -q -k band_surface
    122 deselected in 0.63s
    exit: 5

## Folded 2026-08-09: the four things PLAN says are waiting behind this item

`PLAN.md`'s Phase 10 parks four surfaces and names this item as what they wait
behind; `MOCKUP-MAP.md` says the same, that the heat rings and the in-band grid
"read a mask no node emits" and that this item carries it. Neither was true of
the body above, which is about `PreviewSession`'s request, the collector's extra
dimension, the `BAND` editor and the repaint budget, and says nothing about any
of them. This section is the repair — the claim made true rather than a fifth
Phase-10 item minted beside four that are already sequenced.

**The in-band ring.** v2 draws it off `detect`'s gate mask, which is no node's
product: `emissions` is `("gate",)` and the mask never leaves the node, so a
painter reaching for it would import the tool's module, which is the violation
[adr/gui-knows-kinds-not-tools.md](../adr/gui-knows-kinds-not-tools.md) names
outright. Its home is a `DisplaySurface` member on the preview-only channel —
the licensed revision of
[a-band-declares-the-surface-it-is-dragged-on.md](../adr/a-band-declares-the-surface-it-is-dragged-on.md)
rather than a second vocabulary beside it — which is to say it is another
consumer of exactly the read path this item builds, and the reason it waits is
the measurement in the section above: a watched node is never served from the
store, so asking the walked step for a fill costs its re-use on every frame of
every drag.

**The three alpha sliders and Shift-to-peek** wait with the ring they modulate.
`PLAN.md` states the reason and it is worth keeping because it is a scope fence
rather than a delay: with one opacity control and no ring, the control is peek —
so 10.1's single user-held opacity is not a first slider of three, and a session
that generalizes it into one has built the panel before the picture.

**The ancestor-emission toggle** is the odd one out and does not wait on the read
path at all.
[adr/the-walked-step-owns-the-canvas.md](../adr/the-walked-step-owns-the-canvas.md)
already settles it as view state; what it lacks is a subject, and it gains one
from a second picture-bearing ancestor or from the ring, whichever arrives first.

None of this widens `done_when`, and it should not: what is folded here is the
list of consumers this item's read path is being built for, so that the shape is
chosen against four of them rather than one. The surfaces themselves are their
own work and the review that closes this item should mint or sequence them then,
when the measurement above has said what they cost.
