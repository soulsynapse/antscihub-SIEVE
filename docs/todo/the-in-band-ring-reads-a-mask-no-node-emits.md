---
title: The in-band ring reads a mask no node emits, and the controls over it have no subject
priority: normal
phase: 10
status: open
gated_on: nothing
done_when: "uv run pytest tests -q -k in_band_ring"
opened: 2026-08-10
---

# The in-band ring reads a mask no node emits

`PLAN.md`'s Phase 10 and `MOCKUP-MAP.md` both park this behind
[a-declared-surface-is-drawn-by-nothing.md](a-declared-surface-is-drawn-by-nothing.md),
which is now `done`: the read path exists end to end and the measurement that
gate was waiting on has been taken
([2026.08.10](../findings/2026.08.10-the-display-channel-costs-a-watched-nodes-re-use-and-the-band-budget-holds.md)).
The gate lifts here rather than in prose nothing watches. This item is the
mint that lifting it owes, and the parked work is only sequenced by it while it
stays open.

v2 draws the ring off `detect`'s gate mask, which is no node's product —
`emissions` is `("gate",)` and the mask never leaves the node — so a painter
reaching for it would import the tool's module, the violation
[adr/gui-knows-kinds-not-tools.md](../adr/gui-knows-kinds-not-tools.md) names
outright. Its home is a `DisplaySurface` member on the preview-only channel,
the licensed revision of
[adr/a-band-declares-the-surface-it-is-dragged-on.md](../adr/a-band-declares-the-surface-it-is-dragged-on.md)
rather than a second vocabulary beside it. What is different when this is done
is that the walked step's canvas draws the ring from a surface `detect` declares
and fills, and no module under `gui/` names the tool.

Two things the read path has already settled that this does not get to redecide.
A surface arrives as a `Frame` per frame with no axis of its own — whether that
changes is
[a-surface-carries-its-values-and-not-the-axis-they-sit-on.md](a-surface-carries-its-values-and-not-the-axis-they-sit-on.md)
and not this — and the surfaces of the *walked* step are what the loop fills,
which is `gui/tuning.py`'s `show`, where a ring drawn on the canvas will have to
ask for the same node the canvas is already showing.

**The three alpha sliders, Shift-to-peek and the ancestor-emission toggle are
what this gives a subject, and they are not folded in here.** `PLAN.md` states
the fence and it is worth keeping: with one opacity control and no ring the
control is peek, so 10.1's single user-held opacity is not a first slider of
three. The ancestor toggle is settled as view state by
[adr/the-walked-step-owns-the-canvas.md](../adr/the-walked-step-owns-the-canvas.md)
and lacks only a second picture-bearing ancestor or this ring. **The review that
closes this item mints them**, when there is a picture for them to modulate —
the same obligation this item was minted under, discharged one layer down.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests -q -k in_band_ring
    1249 deselected in 0.93s
    exit: 5
