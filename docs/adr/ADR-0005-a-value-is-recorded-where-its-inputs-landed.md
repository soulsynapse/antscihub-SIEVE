---
title: A value is recorded where its inputs landed
group: Substrate
position: 5
status: settled
decided: 2026-08-23
---

A step computes and records a value when its inputs are admitted — a frame
decoded into a form that may be recorded, or an upstream value written — and
never on the cadence of anything that draws. A cheaper input may be used
where the user has chosen it, and that choice is part of the key, so two runs
against different inputs cannot produce values under one name.

What this refuses is the display as a data source, and it is written down
because this tree built exactly that and did not notice. The reasoning was
not obviously wrong: a tool's field has to be recomputed to be drawn, the
frame was already decoded, and the number that falls out is the same number
a background pass would have written at full price. Every clause is true.
The conclusion — that the drawing may therefore do the recording — inverts
the dependency, and the inversion is invisible because the argument is about
cost and the defect is about provenance. It survived four cost experiments:
a value filed by the wrong producer costs exactly what the right one costs,
so an instrument that measures milliseconds cannot see it. What eventually
found it was a question about shape, not speed: why would anything be
driven by the display.

The disqualifying property is not that a renderer serves the user. It is
that what a renderer selects depends on what the machine had time to draw —
paint cost, compositor cadence, window size, whatever else holds the
processor. A background fill is machine-dependent too, and that is fine: it
varies in *when* rows are produced, not in *which*. The test is whether the
set of recorded values would differ on a slower machine.

What the decision buys is that coverage becomes a property of the work
rather than of the session. Rows are covered because their inputs were
admitted, in an order the producer controls; a second run on a busier
machine takes longer and records the same set. It also makes the byproduct
argument sound: computing a cheap step on an input already resident really
is close to free, and it is free at the point the input lands, which has a
deterministic cadence.

The accepted costs are felt rather than reasoned about. A step's output no
longer accumulates as a side effect of looking at things; a step selected
after its inputs have already been admitted has no output until something
asks for one. That reads, correctly, as the application declining to do work
nobody requested — the same property that makes the coverage record
trustworthy. Whether it also reads as the application forgetting something
it obviously knows is a question for the interface, not for this decision:
re-deriving over inputs already resident is cheap and ordered, and offering
it is compatible with everything above so long as the offer is the user's to
accept.

The corollary about keys is not decoration. A user may reasonably choose a
cheaper input — a proxy, a downscale, a coarser form — and accept what it
costs in fidelity. A choice that does not reach the key produces values
individually honest, collectively incomparable, and indistinguishable
afterwards. Whatever was actually consumed is named in the key, including
the route by which it was produced where that route can differ.
