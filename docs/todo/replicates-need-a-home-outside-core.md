---
title: Replicates need a home, and ADR-6 does not offer one
priority: high
phase: 3
status: open
gated_on: nothing
opened: 2026-08-07
---

# Replicates need a home, and ADR-6 does not offer one

`adr/core-membership-is-closed.md` enumerates core's children — `types.py`,
`tool_base.py`, `tool_registry.py`, `pipeline_model.py`, `ops` — and
`doc_index.py` refuses anything else. v2's `core/replicates.py` is not on
that list, and `Replicate` is a parameter of every v2 command that runs
anything.

It is not a module that can be dropped and noticed later: VISION's project
pane is replicates, the schema question in Phase 3 is partly "what does a
`Project` hold", and six replicates per project is the case the GUI is being
designed around. So this is a collision between a settled ADR and the
product, and it resolves one of three ways: the ADR is revised (its own text
says a new direct child is a revision, refused at the gate until made),
replicates become a field of schema v1 with no module of their own, or they
live outside `core/` in a package that has to be argued for.

Whichever way it goes, it is a decision before 03.1, not during it — a
schema written without a verdict on replicates will get one by accident.
