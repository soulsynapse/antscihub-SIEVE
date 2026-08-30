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

Settled by [experiments/orchestrator2-experiments/01-reentry.py](../../experiments/orchestrator2-experiments/01-reentry.py),
[the pressure dispatcher preempts into seeks](../findings/2026.08.30-the-pressure-dispatcher-preempts-into-seeks.md),
and [a second cursor makes preemption free](../findings/2026.08.30-a-second-cursor-makes-preemption-free.md) —
each ranks by facts a declaration carried.

Taxonomy: Mokhov, Mitchell & Peyton Jones, *Build Systems a la Carte*, ICFP
2018 — scheduler as topological, restarting, or suspending.

Suspending scheduler cautionary tale: a coroutine reveals its dependencies
lazily, one await at a time, so nothing can rank a fetch queue or compute
subsumption before the work begins — the ordering the wall depends on is the
one it cannot see.

Topological scheduler cautionary tale: it needs the dependency graph up front
and whole, which a scrub does not have.
