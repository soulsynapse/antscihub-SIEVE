---
title: The walked step owns the canvas
adr: 28
position: "05.05"
status: settled
decided: 2026-08-09
---

The walked step owns the canvas — its result over its input, its emissions
drawn by kind; an ancestor's emissions are a view toggle; the pin owns only
the slot below.

Ownership is derived, never declared: standing on a card indexes the
preview to that node, so the canvas is a picture of the same value the
headless path measures and no tool holds a painter. The picture is the
referent's composite — the walked step's result blended over that step's
input, v2's `_composite_target` semantics (`mockup/mockup.py`) — which is
what makes tuning legible: the canvas shows what the step *did*. A source
step has no input, so its composite is its result alone; the output card
has no node to render at
([the-output-card-is-a-picture-of-the-write-list.md](the-output-card-is-a-picture-of-the-write-list.md)),
so the canvas shows the last real step's result.

Emission display generates per kind, never per tool — VISION's overlay
sentence extended from param kinds to emission kinds, same asymmetry, same
deliberate slow path (a new kind) buying the fast one (a new tool writes no
canvas code). The kind vocabulary itself is not ruled here; it waits for
its first consumer. The named violation, for the day a tool's surface gets
built: a painter that imports the tool's module, or any kind that cannot be
described without naming the tool that wanted it.

Showing an ancestor's emissions while standing downstream is user-held view
state — the solo gesture grown up — and never a tool's declaration: a tool
that says when it is shown breaks the claim that any layout emitting every
intent kind is a complete GUI (VISION's reshuffle scenario). What stays
indicative is the referent's canvas *contents* — magnifier, block grid,
solo, heat rings — per
[the-mockup-is-the-gui-end-state.md](superseded/the-mockup-is-the-gui-end-state.md)'s
own carve-out; a param's drawn editor already enters by
[gui-knows-kinds-not-tools.md](gui-knows-kinds-not-tools.md) and appears
when its step holds the canvas.

Why: the canvas was the ownership problem MOCKUP-MAP left open, and the
referent had already answered the half that is answerable — its composite
walks with the selection, so this ADR ratifies a behavior rather than
inventing one, and promotes exactly one thing out of "indicative":
who owns the surface. Ruling ownership as derived is what keeps the two
budget regimes attributable (the canvas asks the preview session, so a
regression is the pipeline's or the paint's, never a mystery between) and
keeps the one-file-one-hour tool claim true at the canvas, where it was
weakest.
