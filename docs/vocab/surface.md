---
title: surface
group: Layer 1
position: 7
gloss: Four live senses, and a fifth the vocabulary says is retired. A rendering path, a pane's occupant, whatever is on screen now, and a filled region a colour applies to.
origin: emergent
status: unsettled
raised: 2026-08-30
---

Four live senses, and a fifth the vocabulary says is retired. The entry for
[view](view.md) records the word being dropped for doing double duty — a thing
a pane houses, and a thing paint lands on — and the tree kept using it for both
anyway, plus two more. Nothing here is wrong on its own; what is wrong is that
"surface" in a docstring does not tell a reader which of them is meant.

## Senses

**A rendering path**, in `src/sieve/surfaces.py` and the experiment it is
ported from: "the live surface and the report surface are different code" is a
claim about painter primitives versus a rasteriser, not about anything a pane
holds.

**A pane's occupant**, the sense [view](view.md) retired, still in
`gui/view/canvas/__init__.py` ("aspect-locked surface with overlays drawn on
top of its content") and `gui/primitives/__init__.py` ("shared surfaces,
controls, and marks that views compose but do not own") — where it is doing the
job "view" was named to do.

**The visible face of whatever is up**, in `gui/view/project_list/card.py` ("a
project on the surface"), `gui/primitives/nav.py` ("one section on the
surface") and the section comment in `gui/view/project_list/view.py`. It means
roughly "on screen right now" and would survive being deleted.

**A filled region a colour applies to**, in `gui/primitives/button.py`: the
design-token sense every widget kit has, and the only one with no synonym
already in this vocabulary.

## Fork

Whether the word survives at all. Retiring it entirely is cheapest to say and
costs one rename of a module the substrate imports. Keeping exactly the fill
sense and taking the other three back to [view](view.md), "paint", and nothing
is the narrower cut, and it is the one the module names argue against, since
`src/sieve/surfaces.py` is the rendering-path sense and is the file most likely
to be read. Not decided here — this entry exists so the next person to write
"surface" in a docstring knows they are picking a side.
