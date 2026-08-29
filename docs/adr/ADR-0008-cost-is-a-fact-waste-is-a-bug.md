---
title: Cost is a fact, waste is a bug
group: Substrate
position: 8
status: settled
decided: 2026-08-23
---

Instrumentation exists to find waste — work whose output is discarded or
duplicated, and elapsed time that bought nothing — not to hold cost under a
target. Cost is reported because it decides what a machine can offer; it is
never a list of things to fix. Waste is a defect, is counted, and its target
is zero.

What this refuses is a performance budget. A fixed figure is exceeded by
longer footage, higher resolution, one more step, or a weaker machine, so it
manufactures optimisation work that never ends. It also contradicts ADR-0007:
a cost class belongs to the pairing and is measured where it runs, so a
slower machine falls back deliberately rather than chasing a figure set on
someone else's hardware.

The product constraint — a graph refills faster than the video plays — is
not the budget just refused. The source's frame period is the unit cost
classes are measured in, not a target anything is held to. A step that fits
the period is budgeted; one that does not is a commit step. Falling outside
the period produces a *class*, not a defect report — the deliberate fallback
ADR-0007 buys.

The distinction is between a price and a mistake. Dense optical flow costs
what it costs and the number is information. But a frame decoded twice, a
fetch a declaration predicted (ADR-0006), a value recomputed that was already
stored, a render of a superseded state — those are wrong on any hardware,
finite, and can be driven out.

Unattributed elapsed time is not by itself waste — it may be time that bought
something not yet instrumented. A large remainder reads as *the instrument
is incomplete*, not as a performance problem.

Work discarded on purpose is cost, not waste. A coarse preview thrown away
for a better one later is a choice with a stated reason; counting it as
waste buries the count in noise.

Where it surfaces: a small indicator lives where the work is; the account
belongs in the walked step's own pane, position three on the right
(ADR-0003).

Two accepted costs. The waste count depends on ADR-0006 declarations being
honoured and degrades into a smaller count, not a wrong one, where they are
not. And the instrument deliberately stops answering "is this fast enough" —
that is the cost class's job (ADR-0007), not this instrument's.
