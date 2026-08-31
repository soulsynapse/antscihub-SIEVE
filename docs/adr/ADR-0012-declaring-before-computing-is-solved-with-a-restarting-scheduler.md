---
title: Declaring before computing is solved with Build Systems a la Carte's restarting scheduler
group: Orchestrator
position: 12
status: settled
decided: 2026-08-30
---

The declaration phase exists to hand the scheduler a complete row set to rank
before any work starts, not to avoid blocking; that is what makes this a
restarting scheduler rather than a suspending one, and it is why the phase
cannot be collapsed away.

## Accepted

*Build Systems a la Carte*'s restarting scheduler (Mokhov, Mitchell & Peyton
Jones, ICFP 2018) — [experiments/orchestrator2-experiments/01-reentry.py](../../experiments/orchestrator2-experiments/01-reentry.py),
[the pressure dispatcher preempts into seeks](../findings/2026.08.30-the-pressure-dispatcher-preempts-into-seeks.md),
[a second cursor makes preemption free](../findings/2026.08.30-a-second-cursor-makes-preemption-free.md).
Each ranks by facts a declaration carried before the work it ranks began.

## Rejected

Suspending scheduler cautionary tale: a coroutine reveals its dependencies
lazily, one await at a time, so nothing can rank a fetch queue or compute
subsumption before the work begins — the ordering the wall depends on is the
one it cannot see.

Topological scheduler cautionary tale: it needs the dependency graph up front
and whole, which a scrub does not have.
