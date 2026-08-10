---
title: Hovering a cell solos it, and the solo is what gives a block step a trace
step: "10.4"
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k soloed_block"
opened: 2026-08-09
---

# Hovering a cell solos it, and the solo is what gives a block step a trace

Hovering a cell of the field picks it out; clicking latches it; moving off an
unlatched field drops it. The gesture is emitted and never self-applied — the
drawn marker moves when the model says so and not when the mouse does — which
is v2's discipline and the reason the latch is compared against the applied
solo rather than against a private record of what was asked for.

This is last in the phase because it is the only one of the four with a
consequence past the picture, and the consequence is the point: `graph_panel`
refuses a series carrying more than one value per frame, so a `BLOCK` step has
no trace under the canvas at all today. The solo is the reduction that makes
one value out of B, so this item is what first fills the pinned slot for a
block step. Whether that refusal's message changes with it is the work's to
settle; what must not happen is a second reduction invented here when the
selection already names one.

The gesture's own claims are painted — which cell carries the marker is not
readable off geometry the way a rect is — so the fixture is
`the-source-badge-is-painted-by-nothing.md`'s again, one layer in: the canvas
with cell *i* soloed differs in pixels from the same canvas with cell *j*
soloed, and neither differs from the other by the model having moved.

## Folded 2026-08-10: the field's colour axis is the pinned step's until this lands

10.3 draws the field against `graph_panel.value_range` — the reconciliation its
own body argues for, because a cell that renormalized per frame would say only
which block is loudest *now*. What that reads is the axis of whatever step is
*pinned*, which is only the field's own units when the pin is on the block step
or on something derived from it. On the reference chain it is `detect`'s gate,
whose axis is a count and not block power, so the field is coloured against a
range with no relation to it and the hot end means nothing in particular.

That is this item's subject arriving from the other side: the solo is what first
gives a `BLOCK` step a series, and a block step that can be pinned is a block
step whose field and whose trace read one axis. Nothing about the field needs
changing for it — `app._paint_viewport` already hands the panel's answer over per
repaint — so what this item owes is the pin, and then a case that the two agree.
Until then the colouring is fixed over the window (which is what 10.3 claimed)
but not denominated in the values it is drawn from (which nobody claimed, and a
reader looking at a coloured arena would assume).

The review of 57e43cb put a number on how far apart the two are, and it is
further than "means nothing in particular" reads:
`findings/2026.08.10-the-block-fields-ramp-is-exhausted-four-orders-below-the-values-it-draws.md`.
On the reference chain the ramp is spent inside the first 0.005% of the value
span, so what the user sees today is a two-colour field — cold where a block
measured nothing, hot everywhere else — and the whole of the gradient this item
is about is unreachable. That is the state the pin has to lift, and the case
that the two agree is the one thing that would go red if it did not.

## Folded 2026-08-10 (review of 57e43cb): the field is drawn unmagnified

`BlockField.draw`'s docstring rules on the magnified case — the grid runs far
outside the widget, so the array is bounded by the letterbox rather than by the
zoom — and nothing in the tree reads it back. Handing `draw` the letterbox in
place of the magnified view rect survives the whole GUI suite:

    $ uv run python scripts/mutation_sweep.py --file src/sieve/gui/canvas.py --mutant "self._field.draw(painter, painted, box) ==> self._field.draw(painter, box, box)" -- uv run pytest -q tests/gui -k "block_field or magnified or source_pixels_round_trip"
    SURVIVED  self._field.draw(painter, painted, box)

This is ordinary coverage debt rather than the paint-only blind spot
`findings/loop/2026.08.09-an-items-clause-that-lands-only-in-paintevent-is-outside-every-oracle.md`
names — the geometry is already exposed, as `view_rect` and `grid_edges` — and it
lands here because this item is where it stops being cosmetic: a hit test has to
read the edges the colours landed on, and under a magnification the two are the
same call or they are two rectangles. The case that fixes both is one case.

`done_when` at minting, red because nothing matched:

    $ uv run pytest tests/gui -q -k soloed_block
    181 deselected in 0.7s
    exit: 5
