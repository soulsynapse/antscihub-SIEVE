---
title: A cost class belongs to the pairing
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

The classes are cut where behaviour changes: work in the noise beside the
fetch that produced its input, which rides along and needs no pass of its
own; work that costs real time but fits the interactive budget, which can
preview live; and work that does not fit, which shows what has been computed
and says where nothing has.

Declaring was tried and falsified: every step measured landed in a different
class against the two input regimes the loop runs over, because the first
class is a ratio against a fetch and those fetches differ by more than an
order of magnitude between a small derived file and a large original. A step
carrying a class was asserting something it is not in a position to know.
The measurements are in `experiments/tool-experiments/`.

The class selects behaviour — it decides whether a step's output accumulates
alongside fetches, may be previewed live, or is not previewed at all. A
machine that cannot keep up is told so by measurement and falls back
deliberately, rather than discovering its limits as stutter. Cascading
downward is intended on weak hardware, not a failure mode.

Two accepted costs. A probe taken while the machine is idle describes a
machine that is idle, so a class is re-measurable rather than settled once,
and the measurement carries the conditions it was taken under. And
background load can move the class, so anything that caches one is caching
the regime with it.
