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
therefore falls to a lower class and degrades in a way somebody chose, rather
than chasing a figure that was set on different hardware.

The classes are cut where behaviour changes rather than where the arithmetic
is tidy: work in the noise beside the fetch that produced its input, which
can ride along with that fetch and needs no pass of its own; work that costs
real time and still fits the interactive budget once drawing is taken out of
it, which can preview live and can never be free; and work that does not
fit, which shows what has been computed and says where nothing has.

This was first written as a field on the step, declared by its author, on
the reasonable-sounding argument that a claim nothing can falsify is not
worth recording. An experiment then falsified the declaring rather than any
particular declaration: every step measured landed in a different class
against the two input regimes the interactive loop runs over, because the
first class is a ratio against a fetch and those fetches differ by more than
an order of magnitude between a small derived file and a large original.
Frame differencing is genuinely free beside one and genuinely is not beside
the other, at the same size, in the same session, seconds apart. A step
carrying a class was a step asserting something it is not in a position to
know. The measurements are in `experiments/tool-experiments/`, beside the
runs that produced them.

Measuring rather than declaring follows the habit this tree already has for
routing decisions that depend on the machine, which are probed at first open
and cached per machine and source shape rather than being written down once
by whoever had the fastest computer. The alternative is shipping one
machine's answer to every other, which is the same defect in a different
subsystem.

What makes the decision load-bearing rather than merely tidy is that the
class *selects behaviour*. It is not a label attached after the fact: it
decides whether a step's output accumulates alongside the fetches that feed
it, whether it may be previewed live, or whether previewing is not offered
at all. So a machine that cannot keep up is told so by measurement and
falls back deliberately — fewer live previews, more work moved to passes the
user asks for — instead of discovering its limits as stutter. Cascading
downward is the intended behaviour on weak hardware and not a failure mode
to be engineered away.

Two accepted costs. The class must be probed, which means a step's first
measurement is taken on a machine doing whatever it happens to be doing, and
a probe taken while the machine is idle describes a machine that is idle; a
class is therefore re-measurable rather than settled once, and the
measurement carries the conditions it was taken under. And the class can
move under load — background work inflates every step by a similar factor,
so what is felt is not a specially fragile step but simply the largest
number — which means a class is a statement about a regime and not a
permanent property, and anything that caches one is caching the regime with
it.
