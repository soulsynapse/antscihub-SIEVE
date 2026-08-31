---
title: Knowing what a step costs is solved with FFTW's measure-and-wisdom planner
group: Substrate
position: 7
status: settled
decided: 2026-08-23
---

What cost class a step falls into belongs to that step paired with the input
path feeding it, measured where it runs and cached like any other
machine-dependent probe, never declared by the step.

## Accepted

FFTW's `FFTW_MEASURE` planner and its wisdom file — candidates run on this
machine rather than scored from a cost model, and the verdict kept with the
conditions it was taken under
([tool-experiments](../../experiments/tool-experiments/)).

Three classes, cut where behaviour changes: work in the noise beside the fetch
that produced its input, work that costs real time and fits the interactive
budget, and work that does not fit. The class selects behaviour, so a slow
machine cascades downward deliberately instead of discovering its limits as
stutter.

Accepted cost: a probe taken while idle describes an idle machine, so a class
is re-measurable and carries its regime with it.

## Rejected

A step declaring its own class cautionary tale: the first class is a ratio
against a fetch, and those differ by more than an order of magnitude between a
small derived file and a large original, so every step measured landed in a
different class against the two regimes the loop runs over
([tool-experiments](../../experiments/tool-experiments/)).
