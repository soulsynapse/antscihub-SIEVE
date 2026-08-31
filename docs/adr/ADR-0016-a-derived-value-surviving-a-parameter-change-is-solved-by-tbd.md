---
title: A derived value surviving a parameter change is solved by TBD
group: Orchestrator
position: 16
status: unsettled
decided: 2026-08-30
---

After a parameter change every held frame is still correct and every value
computed under the old parameters is wrong; ADR-0010 closes that for values
by naming a different series, and what closes it for a held field is open.

## Candidates

Salsa's red-green revalidation with early cutoff — a change marks dependents
*potentially* stale (red) and revalidation compares each dependency's actual
value before recomputing, so a query whose inputs all verify equal is reused
and the propagation stops there. Would
have to be measured for what the comparison costs against a field, which is
the term that decides whether it beats recomputing outright.

Adapton's demanded computation graph (Hammer et al., PLDI 2014) — dependencies
are recorded by execution rather than declared, and the dirtying is
demand-driven. Would have to be measured against a declaration model that
already knows its inputs, where the recording may buy nothing.

Jane Street's Incremental — explicit cutoff functions per node, so equality is
the node author's to define rather than the framework's to guess. Would have
to be checked against ADR-0009: a cutoff a tool defines is a tool deciding
when a value is reused.

## Rejected

Key-only memoization cautionary tale: ADR-0010 makes a parameter change name a
different series, which is always correct and cannot notice that a threshold
nudge left a field bit-identical — so every downstream row re-runs, and on a
slider drag that is the whole interactive loop.

Make cautionary tale: a recipe change invalidates the whole subtree with no
value comparison anywhere, and the workaround culture that fills the gap is a
clean build — forfeiting exactly the accumulated work a tuning loop exists to
reuse.
