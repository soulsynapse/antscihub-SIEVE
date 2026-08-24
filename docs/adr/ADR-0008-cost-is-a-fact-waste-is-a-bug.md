---
title: Cost is a fact, waste is a bug
group: Substrate
position: 8
status: settled
decided: 2026-08-23
---

Instrumentation exists to find waste — work whose output is discarded or
duplicated, and elapsed time that bought nothing — and not to hold cost under
a target. Cost is reported because it decides what a machine can offer, and
it is never a list of things to fix. Waste is a defect, is counted, and its
target is zero.

What this refuses is a performance budget, and it is written down because a
budget has been the tree's latent position since v2 without anyone deciding
it. A fixed figure is exceeded by long enough footage, high enough
resolution, one more step in the chain, or a weaker machine, so it
manufactures optimisation work that never ends and never began for a reason.
It also contradicts what has already been settled: a cost class belongs to
the pairing and is measured where it runs, so a slower machine falls back
deliberately rather than chasing a figure set on someone else's hardware
(ADR-0007). A budget asks the machine to conform. This tree asks it to
report, and then decides.

One figure in this tree looks like the budget just refused and is not. The
product constraint is that a graph refills faster than the video plays,
which names the source's own frame period — and a period is the unit the
cost classes are measured in rather than a target anything is held to. A
step whose field fits the period once its fetch and its drawing are taken
out is budgeted; one that does not is a commit step, which shows what
exists and says where none does. Falling outside the period produces a
*class*, and a class is a behaviour somebody chose: the same deliberate
fallback ADR-0007 buys by measuring where it runs. It produces no work
item, and that is the property that separates the two. A budget exceeded is
a defect report addressed to whoever is nearest. A class assigned is the
application saying what it can offer here.

The distinction survives the four things that break a fixed figure. Higher
resolution, one more step in the chain and a weaker machine each move the
class, which is what a class is for. Longer footage does not reach it at
all, because a refill is over a window and a window does not grow with the
file — the one respect in which this constraint was never a figure to begin
with.

The distinction is between a price and a mistake. Dense optical flow costs
what it costs; there is no version of it that is free, and the number is
information about what may be offered here rather than a problem to be
solved. But a frame decoded twice because two consumers wanted forms one of
them could have served, a fetch that a declaration said was coming
(ADR-0006), a computed value discarded where recording it was permitted, a
value recomputed that was already stored under its key, a render of a state
that was superseded before anyone saw it — those are wrong on fast hardware
and slow hardware alike, they are finite, and they can actually be driven
out. That is what makes waste worth an instrument and cost worth only a
readout.

Elapsed time attributed to nothing is counted with them, with one
qualification that matters. Unattributed time is not by itself waste: it may
be time that bought something nobody has instrumented yet. The action it
calls for is therefore a clock rather than an optimisation, and confusing
the two costs a great deal — a driven session of the tool explorer was
diagnosed three times against the instruments that existed before the
remainder revealed that the largest term had no clock on it at all. So the
account is closed against the interval that actually elapsed, never against
a target, and a large remainder reads as *the instrument is incomplete*.

Work discarded on purpose is a cost and not waste. An approximate preview
computes something it will throw away, and does so because a placeholder now
beats the truth later; a coarse field drawn under load is thrown away for the
same reason. Those are choices with a stated reason, and counting them as
waste would bury the count in noise and teach everyone to ignore it. Waste is
work discarded that nobody chose to discard.

Where it surfaces follows from what each part is for. A small indicator
lives where the work is, because a count nobody passes is a count nobody
reads; the account itself belongs in the walked step's own pane, the third
position on the right (ADR-0003), because that is where somebody is standing
when they want to know what a step is throwing away.

Two accepted costs. The waste count is only as good as the declarations it
is measured against — a fetch is avoidable only relative to something that
said it was coming — so this decision depends on ADR-0006 being honoured and
degrades quietly into a smaller count rather than a wrong one where it is
not. And the instrument deliberately stops answering "is this fast enough."
That question has no machine-independent answer, and every attempt this tree
has made to answer it has produced work that outlived its reason. What
answers it instead is the cost class, in the only terms that survive a
change of machine — not a verdict but a statement of what may be offered
here, which is ADR-0007's to give and not this instrument's.
