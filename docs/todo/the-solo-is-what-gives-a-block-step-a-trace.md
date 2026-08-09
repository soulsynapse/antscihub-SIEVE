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

`done_when` at minting, red because nothing matched:

    $ uv run pytest tests/gui -q -k soloed_block
    181 deselected in 0.7s
    exit: 5
