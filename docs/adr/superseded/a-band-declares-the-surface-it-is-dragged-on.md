---
title: A band declares the surface it is dragged on, and the tool fills it
adr: 23
status: superseded
superseded_by: a-parameters-space-is-resolved-by-the-graph
decided: 2026-08-09
---

A `BAND` param names a `DisplaySurface` — a picture kind, never a unit — and its
tool fills it on a preview-only channel: never emitted, never keyed, and refused
unless both halves are declared.

The filler is called only for the node a caller asked to show, and what it
returns is not a product — not typed by `emits`, not on `emissions`, never in
the store — so nothing selects it and no save screen can offer it. Each half is
refused in the absence of the other, at registration and again at the fill.

The surface kind is the vocabulary a later decision about what a tool shows on
the canvas is answered in, or by a revision of it — never by a second parallel
declaration beside it.

Why: `BAND` is the one stereotype whose control a generator can build and cannot
place, because an ordered lo/hi on an axis that is not the timeline says nothing
about which plot the handles are grabbed on. The obvious alternative — declaring
the axis, or binding the band to a named emit of the tool's own `emissions` —
was refused twice on the same ground and by different work
(`docs/todo/a-band-has-no-stereotype-of-its-own.md`,
`docs/todo/composite-kinds-get-their-editors.md`): `detect`'s three bands are Hz,
the upstream node's own output units, and a dimensionless fraction, so no unit
enum is honest across them, and the series they cut never leave the node, so an
`emissions` binding would have `detect` name `"gate"` three times — well-formed,
verified, and false, which `declared-means-verified.md` exists to refuse. Naming
the *picture* is honest because units ride with the data at run time, where the
upstream node has already run.

Preview-only is what keeps this from growing a second product stream. A display
that arrived in `outputs` would be a stream the graph never declared, and the
first thing that would happen to it is a save screen offering it — so the
channel is filled per request rather than by default, and a watched node is
never served from the store, since a hit skips the call and the display was
never in the store to be skipped with it. That trade is deliberate: watching a
node costs this run its own re-use, and the alternative is a plot with holes in
it exactly where the run went fastest.

What this does not settle: nothing draws the surfaces yet, and the budget row it
has to meet is VISION's `Band drag → graphs repaint`
(`docs/todo/a-declared-surface-is-drawn-by-nothing.md` carries both).
