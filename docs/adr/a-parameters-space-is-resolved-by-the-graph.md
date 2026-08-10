---
title: "A parameter's coordinate space is resolved by the graph"
adr: 37
position: "01.07"
status: settled
decided: 2026-08-10
---

A tool declares the space a parameter's value is denominated in — an extent, an
axis, its label — absolutely or relative to its input. The graph folds it
forward, and `None` refuses the editor.

The spaces are the extent of the frame a `REGION` or a `POINT` indexes and the
axis a `BAND`'s handles are read on. The declaration is shaped like
`ToolSpec.element`: an absolute answer, or a relation to what the node was
handed. The per-node conversion sits beside `node_element`, the walk that
supplies the upstream sits in `pipeline/dag.py`, and the resolved value folds
forward beside `elements` and `source_indexed`. `None` is *undeclarable*,
propagates, and never recovers — so a refusal is a state of a graph and not a
property of a kind, and the same parameter takes handles in one pipeline and not
in another.

Carried forward from ADR 23 unchanged: a `BAND` param names a `DisplaySurface` —
a picture kind, never a unit — and its tool fills it on a preview-only channel,
never emitted, never keyed, and refused unless both halves are declared.

Why: ADR 23 rested on one sentence — naming the picture is honest because "units
ride with the data at run time, where the upstream node has already run" — and
the first tool to draw its surfaces spent it. A surface arrives as a `Frame`, so
what rides with it is the *values*; the axis they are indexed on rides with
nothing, and a scalogram's rows cannot be turned into the Hz `freq_band` is
stored in. The same hole predates the display channel: `crop`'s region is
denominated in the frame its node reads, the window knows only the footage's own
size, and the editor is refused for every `crop` that is not a graph root — a
capability the vocabulary declares and the app cannot reach.

What buys the addition is that no existing member can carry it, which is the
price `gui-knows-kinds-not-tools.md` sets. `param_surfaces` names a picture and
is a constant, and neither `REGION` nor `POINT` has a surface at all. `elements`
says what one value is a value *of*, not how many of them a frame holds.
`source_indexed` is the row axis. The near miss is the one worth stating:
`rescale` and `downsample` already declare `ElementRelation.AGGREGATED`, so the
vocabulary knows the geometry changed and has no way to say by how much — the
factor sits in a tool's params where no fold can read it. A qualitative member
where the consumer needs a quantitative answer.

**A unit is a label the tool declares and the GUI prints, never a set the GUI
enumerates.** `ElementNames` is that move already — the interop vocabulary a CSV
header and a plot axis read *instead of* deriving English from an enum. So the
ground the axis was refused on twice
([a-band-has-no-stereotype-of-its-own.md](../todo/a-band-has-no-stereotype-of-its-own.md),
[composite-kinds-get-their-editors.md](../todo/composite-kinds-get-their-editors.md)) —
that no fixed vocabulary is honest across Hz, an upstream node's own units, and a
dimensionless fraction — was an objection to an *enum*, and never to a
declaration. Only the numbers need the fold, and only one band needs its relation
half: `value_band` is in its input's units, which `detect` cannot name at any
time, exactly as `temporal_baseline` emits blocks over `block_signal` and pixels
over a raw frame and could therefore declare no constant. That tool already
forced the relation into existence one channel over.

**The line is content, not size.** A tool declares what a thing is; the GUI
resolves what it looks like. Colour is the case that fixes the rule: it is a
relation among everything on screen at once and no tool can see the others —
`kind_editors._MARK` is amber *because* the working window is blue. So a
declaration carries a role and never a presentation value, and a hex colour, a
pixel size or a widget class is refused where "these two cuts are the parameter's
edges" is not. In the other direction the GUI grows freely: when a declaration
needs a mechanism it has not got — a picker, a plot with labelled ticks, a
control that toggles k of n — building that mechanism is what a licensed revision
*is*, not an erosion of one. What stays out of `gui/` is content: that this axis
is Hz, that this node is `detect`. Legality is not this vocabulary's problem —
a params-model validator already holds it and every gesture reaches the document
through `SetParam`, so a widget cannot admit a value the model refuses.
Registration refuses both directions, per
[declared-means-verified.md](declared-means-verified.md).

The surface kind and this fold together are the vocabulary a later decision about
what a tool shows on the canvas is answered in, or by a revision of them — never
by a third declaration beside them
([todo/the-in-band-ring-reads-a-mask-no-node-emits.md](../todo/the-in-band-ring-reads-a-mask-no-node-emits.md)
is the first such decision and is unchanged by this).

What this does not settle: whether `freq_band` becomes draggable once its axis
resolves — the fold makes it possible and does not oblige it, and that is
[todo/a-surface-carries-its-values-and-not-the-axis-they-sit-on.md](../todo/a-surface-carries-its-values-and-not-the-axis-they-sit-on.md).
`detect`'s `count_frac` is not this: an unarmed band is a widget the form does not
build, no existing member fails at it, and it buys nothing here. Nor is the
granularity of `STEREOTYPES_WITHOUT_EDITOR` under
[an-unconsumed-member-is-named-in-a-list.md](an-unconsumed-member-is-named-in-a-list.md),
which names a kind with no editor and cannot express a parameter whose editor has
no answer — this fold is where that answer would come from.
