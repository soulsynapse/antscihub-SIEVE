---
title: The outputs reach down behind the cards
step: "09.2"
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k reaches_down"
opened: 2026-08-09
---

# The outputs reach down behind the cards

The chain's edges are drawn under the stack's cards: an output leaves the
bottom of the card that made it and arrives at the top of the card that reads
it, vertical in its own lane the whole way down, passing *behind* any card in
between rather than around it — occlusion is the statement that the output
never left the chain. Arrowheads always point down; a port is named at the
arrowhead only where the destination has more than one input. MOCKUP-MAP.md
row "Arrow logic"; the referent's block comment above `_EDGE_STUB`, `_lanes`,
`_paint_edge` and `PORT_NAMES` carry the reasoning — lanes are assigned
shortest-span-first so the trunk stays with the neighbour edges, and geometry
is read off the cards at paint time because the stack is rebuilt on every
walk move. The multi-input picture this draws first is the background/
threshold/subtract branch VISION's scene describes.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/gui -q -k reaches_down
    119 deselected in 0.67s
    exit: 5
