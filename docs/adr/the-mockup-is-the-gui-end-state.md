---
title: The mockup is the GUI's end state
adr: 22
status: superseded
superseded_by: a-position-is-asked-for-in-the-chain
decided: 2026-08-08
---

`mockup/mockup.py` is the settled v3 surface: layout, hotkeys, and
interactions are final; the fake back end transfers nothing; what it does
not show lands in a popup, never as a new region.

Why: the build re-homes those interactions into the real `gui`/`session`
modules, taking the mockup as the referent for how they look and respond.
VISION's scenarios say what the surface does; they cannot carry a
layout, and every question of the form "where does this go, what does it
look like while it happens" was being re-answered per session. The mockup
settles them by existing — the source tool as the first step, the output as
a step at the foot of the chain whose ticked edges are the write list,
output edges descending past steps that do not consume them, the crop fan,
the walk — each reached by making the interaction actually work, which is
the one test prose cannot run. The freeze is the surface, not the mechanism:
tools still arrive freely under kind-keyed generation
([gui-knows-kinds-not-tools](gui-knows-kinds-not-tools.md)), and a complete
GUI is still one that emits every intent kind (VISION), which is what keeps
a later reshuffle affordable. Until such a reshuffle is decided, this file
is what done looks like, and reshaping it is a revision of this ADR, not a
cleanup. It is a referent, read and never imported: it computes its own
mock data inline, which `gui-computes-nothing` forbids the real surface to
copy, and it stays one file because a referent is read whole — the module
split it must not receive is exactly the one the real `gui` must.
One gap is owed rather than ruled on: the referent has no add-tool
affordance yet, and the popup default does not cover it — VISION's
add-tool box (the new-project scenario) is the binding wording until the
box lands here as a licensed revision.
[MOCKUP-MAP.md](../MOCKUP-MAP.md) is the reading guide: the deltas against
the tree, and the boundary of what the referent does not settle.
