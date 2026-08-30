---
title: edge
group: Substrate
position: 6
gloss: Three live senses. A named thing a node offers or wants, of a closed kind; an arrow the pipeline view draws between cards from list order; and the border of a rectangle.
origin: emergent
status: unsettled
raised: 2026-08-30
---

Three live senses, and the dangerous pair is not the one that looks worst. The
substrate's edge is a named thing a [node](node.md) offers or wants, of a
closed kind, and it is the most carefully specified record in the contract. The
pipeline view draws things it also calls edges, between cards, and those are
not that: they are arrows placed from list order. The third sense is the border
of a rectangle, which collides with neither.

## Senses

**A declared connection**, in `contract/edges.py`: a name, a kind out of
`KINDS`, and whichever of form, dtype and `Positioning` that kind needs —
closed, and SIEVE's alone to extend, because a node minting its own payload
type is ADR-0009's accretion moved into the type system. `Source.offers` is a
tuple of edge kinds; `bind` in `experiments/chain-experiments` builds the
`Output` that serves one. The word means the same thing every time it appears
in the substrate or in a tool.

**An arrow drawn down a gap**, in `gui/view/pipeline/view.py` ("the chain's
edges", `paint_ground`) and `gui/primitives/stack.py` ("a chain draws its
edges").

**A rectangle's side**, in `gui/primitives/field.py`'s `EDGE` — a mix weight
for a border colour, imported by `check`, `segmented` and `select` — in the
local `edge` holding a border colour (a `QColor` in `card.py`, `nav.py` and
`gui/view/project_list/card.py`, a CSS string in `button.py`), in "the widget
edge" in half the paint methods, and in `gui/view/transport/geometry.py`'s
"left edge of the column". It is not confined to the GUI: `PROXY_LONG_EDGE` and
`proxy_form`'s `long_edge` are this sense in the substrate, and `session.py`
says "bounded to the proxy's long edge" four modules from where `store.py`
reads `output.edge.form`.

## Fork

The third sense is a naming collision and nothing more; it is the same shape as
[surface](surface.md)'s fill sense, and `gui/primitives/button.py` pairs them
in one line — `fill, ink, edge = _rest(self._kind)`. The first two are the
problem, because they are the same *kind* of noun about the same graph and
disagree about what makes one exist. A substrate edge exists when a producer
declares it by name and a consumer binds to it. A drawn edge exists when two
cards are adjacent in `_chain`, which is the source card followed by the step
cards in registration order; `_lit` turns the arrow the accent colour once
*any* step has produced a value. Nothing on screen is derived from a
[binding](binding.md), because there are no bindings yet. When binding does
land, the picture and the contract will either agree by coincidence or the
screen will assert connections the substrate never made, and there is nothing
that would go red for it.

Which of the two graph senses keeps the word. Keeping it in the contract and
renaming the drawing is the cheap direction, and the drawing code half-names it
already — `_STUB`, `_ARROW_W`, `_ARROW_H`, `drawPolygon`: it is an arrow, and
calling it one costs two docstrings and a section comment. The argument against
is that the arrow is *meant* to become the bound edge made visible, in which
case the word is right and what is wrong is that it is being drawn from
adjacency; then the fix is in `paint_ground` and not in the vocabulary. Those
two readings want opposite commits, which is why this is here and not settled.
Not decided: the next person to draw a connector between two cards is picking
one.
