---
title: Recording a value independently of what got drawn is solved with the Dataflow model's event time
group: Substrate
position: 5
status: settled
decided: 2026-08-31
---

A value is recorded when its inputs are admitted — a frame decoded into a form
that may be recorded, or an upstream value written — and never on the cadence
of anything that draws, because what a renderer paints depends on paint cost,
compositor cadence, window size and whatever else holds the processor. A
cheaper input may be used where the user chose it, and that choice is part of
the key, so two runs against different inputs cannot produce values under one
name.

## Accepted

The Dataflow model's event time against processing time (Akidau et al., VLDB
2015; *Streaming Systems*) — a result is defined by when the data says a thing
happened, never by when a machine got round to it, and a pane fires when its
inputs are complete rather than on a clock. Settled by
[experiments/orchestrator2-experiments/08-cadence.py](../../experiments/orchestrator2-experiments/08-cadence.py)
and [drawing selects the recorded set and landing does not](../findings/2026.08.31-drawing-selects-the-recorded-set-and-landing-does-not.md):
recording on the landing cadence produced the identical set of rows in every
repeat under both loads, and recording on a display cadence produced a
different set every time.

What is adopted is the event-time rule and firing on per-row input
completeness. Watermarks proper — a global assertion that event time has
advanced past a point, with a stated policy for what arrives after — are *not*
implemented here, and that is exactly where the unfinished business is: this
tree has no answer for an input admitted after its row was decided. ADR-0016
is the neighbouring case for a parameter rather than a late input.

The test is not whether a renderer serves the user; a background fill is
machine-dependent too, and that is fine, because it varies in *when* rows are
produced and not in *which*. The test is whether the set of recorded values
would differ on a slower machine, and 08-cadence is that test made runnable.

What it buys is coverage as a property of the work rather than of the session.
The accepted cost is felt rather than reasoned about: a step selected after its
inputs were already admitted has no output until something asks for one, which
reads correctly as the application declining to do work nobody requested, and
is the same property that makes the coverage record trustworthy.

## Rejected

The display as a data source cautionary tale: this tree built exactly that and
did not notice, and the reasoning was not obviously wrong — a tool's field has
to be recomputed to be drawn, the frame was already decoded, and the number
that falls out is the number a background pass would have written at full
price. Every clause is true; the conclusion inverts the dependency. Measured in
08-cadence at 25 to 31 rows present in a quiet run and absent from a loaded
one, and 43 to 53 the other way, with every shared value in exact agreement —
the defect is entirely in which rows exist afterwards and never in what one
says, which is why a checksum over the values would not find it either.

That invisibility has a name — Tene's coordinated omission, where a sampler
whose schedule is coupled to the load of the system it measures systematically
misses the moments that system was busy while every individual measurement
stays correct. Named as the diagnosis rather than the lineage: Tene is
describing latency measurement, and it is the mechanism that transfers. It is
why the defect survived four cost experiments — a value filed by the wrong
producer costs exactly what the right one costs.

Fixed-timestep simulation decoupling (Fiedler, *Fix Your Timestep!*; Bettner &
Terrano, *1500 Archers on a 28.8*, GDC 2001) cautionary tale: it fires on a
clock of its own rather than on inputs being complete, so a machine that misses
a step must choose between falling behind and skipping it — and skipping
reintroduces exactly the selection this refuses. Its acceptance test is the one
adopted above; its mechanism is not.

React's render purity cautionary tale: it forbids deriving persistent state
during render, because a render can be discarded, re-run, or interrupted. Right
refusal, and not a mechanism — it says where a value may not be computed and
nothing about the cadence on which it should be, so it cannot settle this on
its own.

A choice of input that does not reach the key cautionary tale: a user may
reasonably accept a proxy, a downscale or a coarser form, and values produced
under one that is unnamed are individually honest, collectively incomparable,
and indistinguishable afterwards.
