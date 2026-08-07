---
title: The first GUI cut is a capability, and Phase 7 chunks from it
priority: normal
phase: 7
status: done
gated_on: nothing
opened: 2026-08-07
---

# The first GUI cut is a capability, and Phase 7 chunks from it

Ruled 2026-08-07. The first cut is what the GUI can *do*, not which of v2's
surfaces come over: open a project, see the pipeline as VISION describes it,
tune a param with the graphs refilling inside the budget, check off the
outputs to keep, run. The wizard, the replicate tab, the history dialog and
the sweep view wait — each for a reason rather than for room, the sharpest
being that a history dialog makes undo a visible object, which is the
opposite of the two stacks of whole immutable values the v2.5 spike settled
on (`adr/gui-base-is-the-v25-spike.md`).

The cut is drawn at capability because that is where the cost of being wrong
is. A layout can be rearranged for nothing; a capability drags machinery
behind it, and machinery is what Phase 7 would have to unbuild.

The record is in PLAN.md's Phase 7, which is where the items get chunked
from. This file stays as the ruling's home rather than as work to do.
