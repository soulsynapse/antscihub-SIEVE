---
title: edge
group: Substrate
position: 6
gloss: Three live senses. A named thing a node offers or wants, of a closed kind; an arrow the pipeline view draws between cards from list order; and the border of a rectangle.
origin: emergent
status: unsettled
raised: 2026-08-30
---

Three senses, and the dangerous pair is not the one that looks worst. The
substrate's edge is a named thing a [node](node.md) offers or wants, of a
closed kind. The pipeline view draws things it also calls edges, between cards,
and those are not that: they are arrows placed from list order. The third is
the border of a rectangle, which collides with neither.

## Senses

**A declared connection**, in `contract/edges.py`: a name, a kind out of
`KINDS`, and whichever of form, dtype and `Positioning` that kind needs —
closed, and SIEVE's alone to extend, because a node minting its own payload
type is ADR-0009's accretion moved into the type system.

**An arrow drawn down a gap**, in `gui/view/pipeline/view.py` ("the chain's
edges") and `gui/primitives/stack.py`.

**A rectangle's side**, in `gui/primitives/field.py`'s `EDGE` mix weight, in
locals holding a border colour across the primitives, and in
`gui/view/transport/geometry.py`. Not confined to the GUI: `PROXY_LONG_EDGE`
and `proxy_form`'s `long_edge` are this sense in the substrate, four modules
from where `store.py` reads `output.edge.form`.

## Fork

The third sense is a spelling collision, the same shape as
[surface](surface.md)'s fill sense. The first two are the problem: same kind of
noun, same graph, and they disagree about what makes one exist. A substrate
edge exists when a producer declares it by name and a consumer binds to it. A
drawn edge exists when two cards are adjacent in `_chain` — the source followed
by the steps in registration order — and `_lit` turns the arrow the accent
colour once *any* step has produced a value. Nothing on screen is derived from
a [binding](binding.md), because there are no bindings yet. When binding lands,
the picture and the contract will either agree by coincidence or the screen
will assert connections the substrate never made.

Renaming the drawing is cheap, and that code half-names it already — `_STUB`,
`_ARROW_W`, `drawPolygon`: it is an arrow, and saying so costs two docstrings.
The argument against is that the arrow is *meant* to become the bound edge made
visible, in which case the word is right and drawing it from adjacency is the
bug — a fix in `paint_ground`, not here. Those two readings want opposite
commits. The next person to draw a connector between two cards is picking one.
