---
title: Recording a value independently of what got drawn is solved by TBD
group: Substrate
position: 5
status: unsettled
decided: 2026-08-23
---

A value must be recorded on a cadence the machine's drawing cannot select,
because what a renderer paints depends on paint cost, compositor cadence,
window size and whatever else holds the processor — so a recorded set gated by
it differs between two machines running the same work. What produces that
cadence has candidates and no measurement.

What the tree does now: a step computes and records a value when its inputs are
admitted — a frame decoded into a form that may be recorded, or an upstream
value written — and never when something draws. A cheaper input may be used
where the user chose it, and that choice is part of the key, so two runs against
different inputs cannot produce values under one name.

The test is not whether a renderer serves the user; a background fill is
machine-dependent too, and that is fine, because it varies in *when* rows are
produced and not in *which*. The test is whether the set of recorded values
would differ on a slower machine.

What this buys is coverage as a property of the work rather than of the
session: rows are covered because their inputs were admitted, in an order the
producer controls, and a second run on a busier machine takes longer and
records the same set. The accepted cost is felt rather than reasoned about — a
step selected after its inputs were already admitted has no output until
something asks for one, which reads correctly as the application declining to
do work nobody requested, and is the same property that makes the coverage
record trustworthy.

## Candidates

The Dataflow model's event time and watermarks (Akidau et al., VLDB 2015;
*Streaming Systems*) — a result is defined by when the data says a thing
happened, never by processing time, which depends on machine speed and arrival
order; a window fires when the system can assert its inputs have landed.
Closest structurally, because it is about recorded values rather than about
simulation state, and it carries vocabulary for the case this tree has not hit:
an input that arrives after the window decided it would not.

Fixed-timestep simulation decoupling (Fiedler, *Fix Your Timestep!*; Bettner &
Terrano, *1500 Archers on a 28.8*, GDC 2001) — the simulation advances on a
step independent of frame rate and rendering interpolates from it, because
deterministic lockstep makes "would a slower machine compute something else"
an absolute requirement rather than a preference. The acceptance test above is
theirs.

React's render purity — persistent state is never derived during render,
because a render can be discarded, re-run, or interrupted. Same conclusion from
a different reason, and it is the one that connects to ADR-0008's *render of a
superseded state*.

All three wait on the same measurement, which this file already specifies: run
one walk under artificial load and compare the recorded set against the
unloaded run. Differing sets say the display was the data source; identical
sets say the current arrangement is clean.

## Rejected

The display as a data source cautionary tale: this tree built exactly that and
did not notice, and the reasoning was not obviously wrong — a tool's field has
to be recomputed to be drawn, the frame was already decoded, and the number
that falls out is the number a background pass would have written at full
price. Every clause is true; the conclusion inverts the dependency, and the
inversion is invisible because the argument is about cost and the defect is
about provenance. It survived four cost experiments, because a value filed by
the wrong producer costs exactly what the right one costs.

That invisibility has a name — Tene's coordinated omission, where a sampler
whose schedule is coupled to the load of the system it measures systematically
misses the moments that system was busy, while every individual measurement
stays correct. Named as the diagnosis rather than the lineage: Tene is
describing latency measurement, and the mechanism is what transfers.

A choice of input that does not reach the key cautionary tale: a user may
reasonably accept a proxy, a downscale or a coarser form, and values produced
under one that is unnamed are individually honest, collectively incomparable,
and indistinguishable afterwards.
