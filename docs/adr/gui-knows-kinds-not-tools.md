---
title: The GUI knows kinds, never tools
adr: 12
position: "05.01"
status: settled
decided: 2026-08-06
---

`gui` reads spec data — param kinds, presentation stereotypes, window shape —
and never branches on `tool_id`; widgets and overlays are generated per kind.

A drawn overlay is an editor bound to a param field, entering through the
same command path as a typed value.

Why: the asymmetry is the design — tools grow fast and for free because kinds
grow slowly and deliberately, and the first `if tool_id == "crop"` in a
renderer ends the property for every tool after
(`docs/archive/DESIGN-SESSION.md`, Exchanges 1 and 2; v2's `filter_tab.py` is
what its absence costs). The named erosion point: when a bespoke
visualization is a two-hour job and a new kind is a two-day one, the two-hour
job gets taken — the answer is that the kind vocabulary is where that work
lands, so the third tool wanting it pays nothing. Binding overlays to param
fields is the same property on the left pane: drawing a box and typing
coordinates are one mutation at one path, so undo, validation, and
serialization need no per-tool code.
