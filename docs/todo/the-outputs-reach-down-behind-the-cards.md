---
title: The outputs reach down behind the cards
step: "09.7"
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

This sits late in the phase rather than beside the cards because its subject
arrives late. Every edge long enough to pass behind a card comes from a merge
or from the output step's ticks, and schema v1 gives a node one input — so on
the linear chain the earlier steps draw, no edge ever has a card to occlude
and the occlusion clause cannot be shown false. 09.2, which makes the output a
node with one edge per ticked product, is the first step that puts two edges
into one node; this one runs after it and paints what it built.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/gui -q -k reaches_down
    119 deselected in 0.67s
    exit: 5

## 2026-08-09 (review): the falsifiability argument now has two homes

The paragraph above and `PLAN.md`'s Phase 9 ordering sentence make the same
argument in the same words — schema v1's one input per node, so no edge has a
card to occlude until 09.2 lands. One fact, one home: when this step is built,
one of the two becomes a link to the other, and PLAN is the one that should
shrink, since the reason a step sits where it does belongs to the step. While
both stand, PLAN's version also overstates its own sequence: it says the edges
are "drawn under all of it last", and 09.8's crop fan lands after this step.

## 2026-08-09 (review): 09.2 is deferred, so the multi-input half of this has no subject

Read before starting. The step this one says it "runs after" is now
`deferred_for: decision` — the output node needs a ruling on whether the tool
contract admits a node that consumes and emits nothing, which is Kendrick's and
not a work run's. The consequence here is partial, not a block: lanes,
arrowheads and the down-edges of a linear chain are buildable now, and only the
occlusion clause and the port name at a multi-input arrowhead wait on 09.2. If
this step is reached with 09.2 still deferred, say so rather than inventing a
second-input fixture to paint against — the whole reason this step sits late is
that no such graph exists yet.
