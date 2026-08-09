---
title: The outputs reach down behind the cards
step: "09.7"
status: done
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

## 2026-08-09 (work): occlusion did not wait, and the port name is the only clause left

The section above is half right, and the half it gets wrong is the one that
would have shortened this step. A card to pass behind needs an edge whose ends
are not adjacent in the walk, which is a *fan-out*; `Pipeline._check` refuses
two edges into one node and permits one node feeding two, and `node_order` is
depth-first, so `n0 -> n1` and `n0 -> n2` puts n1's card between the second
edge's ends. That graph loads and draws today, and the occlusion clause is
asserted on rendered pixels against it
([findings/2026.08.09-schema-v1-refuses-fan-in-and-not-fan-out-so-an-edge-has-a-card-to-pass-today.md](../findings/2026.08.09-schema-v1-refuses-fan-in-and-not-fan-out-so-an-edge-has-a-card-to-pass-today.md)).
The same finding is why the first review section's PLAN edit landed here as a
link rather than as a shrunk copy of an argument that does not hold.

What is *not* built is the port name at a multi-input arrowhead — the one clause
that does need a fan-in. Schema v1's `Edge` carries no port and nothing in the
tree produces a name for one, so an implementation would be inventing both the
second input and the word written beside it; 09.2 is where the two arrive
together and already owns the labeling
([the-output-is-a-step-and-its-ticks-are-edges.md](the-output-is-a-step-and-its-ticks-are-edges.md)
names `_port_name`'s output branch). `chain_stack.py`'s block comment says the
same thing at the site. So the review that closes this should decide whether an
unbuilt clause of the body leaves the item open behind 09.2 or closes with the
clause handed over; `done_when` reaches the four clauses that were buildable and
was not edited here.

## 2026-08-09 (review): done, with the port name handed to 09.2

`done`. The criterion is untouched and passes here (5 passed, 157 deselected),
the full suite is green at 1122, `ruff check`/`format --check` and
`doc_index --check` are clean, and the worktree was clean at the start of this
review. The schema reading the work section corrects checks out against
`Pipeline._check` and `walk.node_order`, and the four clauses `done_when`
reaches are all mutation-sensitive: `drawLine`, the arrowhead's shoulders, the
lane loop, the start point, and the column's own `fillRect` are each killed by
`tests/gui/test_chain_edges.py`.

The fork the work run left is answered by the rule
[the-review-has-a-path-for-a-partial-deferral.md](the-review-has-a-path-for-a-partial-deferral.md)
already states: the residue is a *subject* this item could not have built, not
an assertion it was supposed to satisfy, and it has a home — so `done` plus a
carried clause, not `open` behind a deferral that would serve a work run a green
criterion and an incentive to justify itself. 09.2 now names the arrowhead's
port explicitly in a section of its own; what makes this the third instance of
that shape, and the first where nothing was amended because the criterion was
never wrong, is
[findings/loop/2026.08.07-the-review-prompt-has-no-path-for-a-partial-deferral.md](../findings/loop/2026.08.07-the-review-prompt-has-no-path-for-a-partial-deferral.md).

Two lines of the painter are argued and held by nothing — the `drawPolygon` that
puts the arrowhead on the picture at all, and the guard that drops an upward
edge in a cyclic document. Both survive mutation under all of `tests/gui`.
Folded into
[the-seam-height-and-the-travel-flag-have-no-case.md](the-seam-height-and-the-travel-flag-have-no-case.md),
which is the same claim about 09.6's two lines.
