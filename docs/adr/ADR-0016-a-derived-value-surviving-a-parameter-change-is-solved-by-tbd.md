---
title: A derived value surviving a parameter change is solved by TBD
group: Orchestrator
position: 16
status: unsettled
decided: 2026-08-30
---

After a parameter change every held frame is still correct and every value
computed under the old parameters is wrong; ADR-0010 closes that for values by
naming a different series, and what closes it for a held field is open.

## Candidates

Salsa's red-green revalidation with early cutoff — a change marks dependents
potentially stale and revalidation compares each dependency's value before
recomputing, so propagation stops where inputs verify equal. Would have to be
measured for what the comparison costs against a field, which is the term that
decides whether it beats recomputing.

Adapton's demanded computation graph (Hammer et al., PLDI 2014) — dependencies
recorded by execution rather than declared, dirtying demand-driven. Would have
to be measured against a declaration model that already knows its inputs, where
the recording may buy nothing.

Jane Street's Incremental — explicit per-node cutoff functions, so equality is
the node author's to define. Would have to be checked against ADR-0009: a cutoff
a tool defines is a tool deciding when a value is reused.

## Rejected

Key-only memoization cautionary tale: ADR-0010 makes a parameter change name a
different series, which is always correct and cannot notice a threshold nudge
leaving a field bit-identical, so on a slider drag every downstream row re-runs.

Make cautionary tale: a recipe change invalidates the whole subtree with no
value comparison anywhere, and the clean build that fills the gap forfeits the
accumulated work a tuning loop exists to reuse.
