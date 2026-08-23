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
because this tree built exactly that and did not notice. The reasoning that
got there was not obviously wrong: a tool's field has to be recomputed to be
drawn, the frame it is drawn from was already decoded, and the number that
falls out of that field is the same number a background pass would have
written later at full price. Every clause of that is true. The conclusion
drawn from it — that the drawing may therefore do the recording — inverts
the dependency, and the inversion is invisible from inside the argument
because the argument is about cost and the defect is about provenance.

It survived four cost experiments for that reason. A value filed by the
wrong producer costs exactly what the right one costs, so an instrument that
measures milliseconds cannot see it, and every measurement that succeeded
around it read as confirmation. What eventually found it was a question
about shape rather than about speed: why would anything be driven by the
display.

The disqualifying property is not that a renderer serves the user. It is
that **what a renderer selects depends on what the machine had time to
draw** — on paint cost, on compositor cadence, on window size, on whatever
else holds the processor. A background fill is machine-dependent too, and
that is fine: it varies in *when* rows are produced, not in *which*.
Coverage may lag. Coverage may not be chosen by rendering. The test that
distinguishes them is whether the set of recorded values would differ on a
slower machine.

What the decision buys is that coverage becomes a property of the work
rather than of the session. Rows are covered because their inputs were
admitted, in an order the producer controls, reproducibly; a second run on a
busier machine takes longer and records the same set. It also makes the
byproduct argument sound rather than merely appealing — computing a cheap
step on an input that is already resident really is close to free, and it is
free at the point the input lands, which is a place with a deterministic
cadence.

The accepted costs are real and are felt rather than reasoned about. A step's
output no longer accumulates as a side effect of looking at things, so
arriving somewhere and watching it fills nothing that was not going to be
filled anyway; a step selected after its inputs have already been admitted
has no output until something asks for one. That reads, correctly, as the
application declining to do work nobody requested, and it is the same
property that makes the coverage record trustworthy. Whether it also reads
as the application forgetting something it obviously knows is a question for
the interface, not for this decision: re-deriving over inputs already
resident is cheap and ordered, and offering it is compatible with everything
above so long as the offer is the user's to accept.

The corollary about keys is not decoration. The escape hatch exists because
a user may reasonably choose a cheaper input — a proxy, a downscale, a
coarser form — and accept what it costs them in fidelity. A choice like that
which does not reach the key produces values that are individually honest,
collectively incomparable, and indistinguishable afterwards. Whatever was
actually consumed is named in the key, including the route by which it was
produced where that route can differ.
