---
title: An output's kind is the picture it makes
adr: 29
position: "05.06"
status: settled
decided: 2026-08-09
---

The canvas paints an output by its `ElementKind` — `PIXEL` an image, `BLOCK` a
field of cells over its frame, `FRAME` no picture — and no member is ever added
for a tool.

This is the kind vocabulary
[the-walked-step-owns-the-canvas.md](the-walked-step-owns-the-canvas.md)
deferred to its first consumer, and it is not a new declaration: it is on
every node already, folded
down the chain by `pinned.element_kinds`, and branched on by
`pinned.draws_a_trace` and by `app.frame_bearing`'s climb past a gate — a climb
that is `FRAME`'s entry in this table, stated here so the two are one rule
rather than two over one question. What the phase adds is a consumer, which is
the direction [declared-means-verified.md](declared-means-verified.md) asks
declarations to grow in.

`DisplaySurface` is the neighbouring vocabulary and this is not a second
declaration beside it. That enum answers what a tool *shows* — filled per
request on the preview-only channel, never emitted, never keyed, never in the
store ([a-parameters-space-is-resolved-by-the-graph.md](a-parameters-space-is-resolved-by-the-graph.md)).
`ElementKind` answers what a node's output *is*, which the store keys and the
save screen offers. Two questions over two bodies of data, and each keeps its
own: a picture a tool wants shown over the footage is a `DisplaySurface`
member and a revision of that ADR, never a fourth `ElementKind`; a node's
output is drawn by this table and never by a fill.

Why: the alternative is one enum answering both, and it fails on the honesty
that made ADR 23 name surfaces instead of units. A node's output would then
declare a picture it does not produce — `detect` emits `gate` and shows a
scalogram, a trace and a count, and reconciling those into one field means one
of the four is false, which `declared-means-verified` exists to refuse. The
cost of two vocabularies is that a reader must know which question is being
asked; the cost of one was a declaration that could be well-formed, verified,
and wrong.
