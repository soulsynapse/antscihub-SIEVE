---
title: Knowing what a step costs is solved with FFTW's measure-and-wisdom planner
group: Substrate
position: 7
status: settled
decided: 2026-08-23
---

What cost class a step falls into is a property of that step paired with the
input path feeding it, measured where it runs and cached like any other
machine-dependent probe, never declared by the step itself. A slower machine
therefore falls to a lower class and degrades in a way somebody chose,
rather than chasing a figure set on different hardware.

## Accepted

FFTW's `FFTW_MEASURE` planner and its wisdom file — the plan is chosen by
running the candidates on this machine rather than from a cost model, and the
result is cached with the conditions it was taken under so a later run reuses
it without re-measuring. Both halves are what this decision needed: measure
here, and keep the measurement as a probe rather than as a constant.

Settled by [experiments/tool-experiments/](../../experiments/tool-experiments/) —
every step measured landed in a different class against the two input regimes
the loop runs over.

The classes are cut where behaviour changes: work in the noise beside the
fetch that produced its input, which rides along and needs no pass of its
own; work that costs real time but fits the interactive budget, which can
preview live; and work that does not fit, which shows what has been computed
and says where nothing has. The class selects behaviour rather than
describing it — a machine that cannot keep up is told so by measurement and
falls back deliberately, rather than discovering its limits as stutter, and
cascading downward on weak hardware is intended.

Two accepted costs. A probe taken while the machine is idle describes a
machine that is idle, so a class is re-measurable rather than settled once,
and the measurement carries the conditions it was taken under. And background
load can move the class, so anything that caches one is caching the regime
with it.

## Rejected

A step declaring its own class cautionary tale: tried and falsified in
[experiments/tool-experiments/](../../experiments/tool-experiments/), because
the first class is a *ratio* against a fetch and those fetches differ by more
than an order of magnitude between a small derived file and a large original.
A step carrying a class was asserting something it is not in a position to
know — the same shape ADR-0009 refuses for tools generally.
