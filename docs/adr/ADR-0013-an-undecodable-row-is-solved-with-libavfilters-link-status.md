---
title: A row that cannot be decoded is solved with libavfilter's link status
group: Orchestrator
position: 13
status: needs experiment
decided: 2026-08-30
---

Permanent absence is a state carried on the activation path — the consumer is
re-entered and told the input will never arrive — and never a value placed
where a value goes.

Settled by *(experiment not yet in this tree)*.

Prior art: libavfilter carries EOF and error as first-class link state through
the same `activate` protocol that carries frames.

In-band sentinel cautionary tale: `dispatcher.py`'s fetch loop currently parks
`np.zeros((1, 1))` in the pool on a decode failure so `has` says yes, which
makes a hole indistinguishable from data to every node downstream and silences
the failure at the exact point something should have been told about it.
