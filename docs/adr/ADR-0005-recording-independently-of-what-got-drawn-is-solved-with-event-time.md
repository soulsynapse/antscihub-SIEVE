---
title: Recording a value independently of what got drawn is solved with the Dataflow model's event time
group: Substrate
position: 5
status: settled
decided: 2026-08-31
---

A value is recorded when its inputs are admitted and never on the cadence of
anything that draws, and the input chosen is part of its key, so two runs over
different inputs cannot produce values under one name.

## Accepted

The Dataflow model's event time against processing time (Akidau et al., VLDB
2015) — a result is defined by when the data says a thing happened, and a pane
fires on its inputs being complete rather than on a clock
([08-cadence](../../experiments/orchestrator2-experiments/08-cadence.py),
[drawing selects the recorded set](../findings/2026.08.31-drawing-selects-the-recorded-set-and-landing-does-not.md)).

Watermarks are not adopted with it: nothing here answers an input admitted after
its row was decided, which is the neighbour of ADR-0016.

## Rejected

The display as a data source cautionary tale: every clause of the argument for
it is true — the field is recomputed to be drawn, the frame is already decoded,
the number is the one a background pass would have written — and the conclusion
still inverts the dependency
([08-cadence](../../experiments/orchestrator2-experiments/08-cadence.py)).

Its invisibility is Tene's coordinated omission, a sampler whose schedule is
coupled to the load of the system it measures: every value stays correct and the
defect is entirely in which rows exist, so four cost experiments could not see
it and a checksum would not either.

Fixed-timestep decoupling (Fiedler, *Fix Your Timestep!*) cautionary tale: fires
on a clock of its own, so a missed step is either fallen behind or skipped, and
skipping reintroduces the selection this refuses.

React's render purity cautionary tale: right refusal, no mechanism — it says
where a value may not be computed and nothing about the cadence it should be
computed on.
