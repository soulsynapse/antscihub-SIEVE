---
title: The mockup is the GUI's end state, and a position is asked for in the chain
adr: 30
position: "05.03"
status: settled
decided: 2026-08-09
---

`mockup/mockup.py` is the settled v3 surface: layout, hotkeys and interactions
are final. What it does not show lands in a popup — unless the question is
*which position*, which is asked in the chain.

Why: the fake back end transfers nothing. The build re-homes those
interactions into the real `gui`/`session`
modules, taking the mockup as the referent for how they look and respond.
VISION's scenarios say what the surface does; they cannot carry a layout, and
every question of the form "where does this go, what does it look like while it
happens" was being re-answered per session. The mockup settles them by existing
— the source tool as the first step, the output as a step at the foot of the
chain whose ticked edges are the write list, output edges descending past steps
that do not consume them, the crop fan, the walk — each reached by making the
interaction actually work, which is the one test prose cannot run. The freeze
is the surface, not the mechanism: tools still arrive freely under kind-keyed
generation ([gui-knows-kinds-not-tools](gui-knows-kinds-not-tools.md)), and a
complete GUI is still one that emits every intent kind (VISION), which is what
keeps a later reshuffle affordable. Until such a reshuffle is decided, this
file is what done looks like, and reshaping the referent is a revision of this
ADR, not a cleanup. It is a referent, read and never imported: it computes its
own mock data inline, which `gui-computes-nothing` forbids the real surface to
copy, and it stays one file because a referent is read whole — the module split
it must not receive is exactly the one the real `gui` must.

The exception is what this ADR adds, and it is the gap
[the-mockup-is-the-gui-end-state](the-mockup-is-the-gui-end-state.md) left
owed. A popup is the right default because most of what the referent does not
draw is a *choice* — one list, one answer, no geometry — and giving each of
those a region would grow the surface per feature. Adding a step is not that
shape. Its first question is which gap, and the gaps are what the stack is
already drawing: a panel in the chrome asking it would have to name in words
the position the picture is holding, and then the user would be reading a
sentence against a diagram to check they agreed. So the affordance stands in
the chain — a card in the stack, numbered as though it were already the step,
dashed on the two edges it would be spliced onto — and the popup default binds
everything whose question is not a place. That is the general rule; the box is
its first case and `MOCKUP-MAP.md` row "Adding a step" is what it settled.

Two of those settlements go past VISION's wording rather than implementing it,
which is why they are recorded here and not only in the map. VISION puts the
add-tool box "below the last step" because that is where its new-project
scenario stands, with one step in the chain; what a position *is* does not
change further up, and the offering is derived from what flows into the gap, so
the same derivation answers at every gap and the foot is the default rather
than the rule. And the gap under the output step is not a position at all —
nothing reads past the foot of the chain — which is a refusal the surface
carries the way the source card carries its un-removability, not a rule the
document holds.

What is still owed is narrower than what was: the referent cannot draw an offer
that is empty, because its sample shelf always has entries, and the tree's
first case is the other one
([findings/2026.08.09-the-shelf-declares-too-little-for-eight-of-ten-positions-to-offer-anything.md](../findings/2026.08.09-the-shelf-declares-too-little-for-eight-of-ten-positions-to-offer-anything.md)).
`MOCKUP-MAP.md` holds that and the rest of the boundary; this file does not
restate it.
