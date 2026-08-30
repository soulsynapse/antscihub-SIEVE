---
title: A derived value surviving a parameter change is solved with Salsa's early cutoff
group: Orchestrator
position: 16
status: needs experiment
decided: 2026-08-30
---

A parameter change marks what depends on it *potentially* stale rather than
stale, and revalidation compares each dependency's actual value before
recomputing, so a change that leaves an intermediate identical stops
propagating at that intermediate instead of re-running everything under it.

Settled by *(experiment not yet in this tree)*.

Prior art: Salsa's red-green revalidation with early cutoff (rust-analyzer's
engine); Hammer et al., *Adapton: composable demand-driven incremental
computation*, PLDI 2014; Jane Street's Incremental.

Key-only memoization cautionary tale: ADR-0010 makes a parameter change name a
different series, which is always correct and cannot notice that a threshold
nudge left a field bit-identical — so every downstream row re-runs, and on a
slider drag that is the whole interactive loop. It closes the gap for values
and leaves it open for a held field, which is the case this decision is about.

Make cautionary tale: a recipe change invalidates the whole subtree with no
value comparison anywhere, and the workaround culture that fills the gap is a
clean build — forfeiting exactly the accumulated work a tuning loop exists to
reuse.
