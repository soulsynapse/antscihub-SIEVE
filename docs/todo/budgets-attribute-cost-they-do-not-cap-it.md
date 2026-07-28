---
title: A budget must attribute a cost, never cap the user's parameter
status: open
serves: [A1, A2]
opened: 2026-07-28
gated_on: >
  nothing — the decision is made (Kendrick, 2026-07-28) and it invalidates a
  shipped control. What is left is the order: the off-thread rebuild has to
  land before the cap comes off, or removing the cap trades a refusal for a
  frozen window, which is the worse half of rule 6
reads:
  - src/sieve/gui/density_plot.py
  - src/sieve/gui/block_spin.py
  - src/sieve/bench/budgets.py
  - src/sieve/gui/graph_hud.py
  - docs/findings/2026.07.28-the-density-rebuild-buys-one-octave-below-auto.md
---

# A budget must attribute a cost, never cap the user's parameter

`gui/density_plot.MAX_BLOCKS` is 16,384 because that is where the 100 ms
`density_rebuild` ceiling lands *on this workstation*, and `gui/block_spin.py`
refuses every block size implying more. That is a machine parameter wearing a
product parameter's clothes, and it is wrong in the direction that matters:
block count is a scientific choice about the grain of the analysis, the HPC
target does not have this machine's timing, and a user who wants a 256x256
grid is not making a mistake the application should prevent.

**The decision (Kendrick, 2026-07-28): there is pretty much no cap.** The
obligation the budget creates is on the app, not on the user. Slow is
acceptable. Laggy or frozen is not. And the bench instrumentation must say
*what* is costing the time, in a persistent field, rather than the application
either seizing up or saying no.

So the budget stops being a refusal threshold and becomes an attribution
threshold: the number is what decides whether the HUD names this work as the
thing making the session slow, not what decides whether the work is allowed.

## Why this is not a one-line deletion

Removing the cap today buys a frozen window at large B. `set_series` runs on
the GUI thread and is linear in `T x B` at ~6 us per thousand pairs (today's
reading; the finding measured 5.1), so a 600-frame window at B = 65,536 is
~400 ms a rebuild and the 210,672-block grid
`docs/findings/2026.07.27-the-density-histogram-was-a-scatter.md` measured is
seconds a tick. Rule 6's mirror clause is explicit that a control which looks
live and is not is the same lie as a result that looks better-founded than it
is. So the order is fixed:

1. **The rebuild leaves the GUI thread.** `gui/detector_worker.py` is the
   shape and the precedent — a third thread, one in flight and one pending,
   latest wins, no cadence — and its docstring already argues why neither
   existing thread can host work like this. A rebuild that is superseded
   before it lands is dropped by revision, exactly as a detector pass is.
2. **The cap comes off.** `MAX_BLOCKS` stops being a refusal and
   `BlockSpinBox` stops declining. What is left of the number, if anything, is
   the point past which the HUD starts attributing.
3. **The HUD attributes.** A persistent field naming the current dominant
   cost — "density surface, B = 65,536: 340 ms/rebuild" — not a transient
   warning and not a modal. `gui/graph_hud.py` already publishes timings from
   `bench/metrics.py`; what is missing is the *ranking* and a field that says
   which consumer owns the biggest span.

## What this invalidates, and must be corrected rather than left

- **`MAX_BLOCKS` as a bound.** The comment on it calls the refusal "rule 6's
  preference"; that reading is wrong and the constant's own docstring has to
  say so once the cap is gone.
- **`docs/findings/2026.07.28-the-density-rebuild-buys-one-octave-below-auto.md`.**
  Its measurements stand — the rate and the linearity are facts. Its framing
  does not: "what that bound buys is one halving below auto" is an answer to a
  question that should not have been asked. A finding is superseded by a later
  finding, never edited, so this is a `supersedes:` on whatever measures the
  off-thread rebuild.
- **`density_rebuild`'s entry in `bench/budgets.py`.** It is currently a
  producer for a widget's refusal threshold. It becomes the attribution
  threshold for one span, and its `WITHOUT_PRODUCER` status does not change.

## The measurement that provoked this, kept because it is the argument

Fresh processes, 2026-07-28, same machine as the finding: 89.3, 92.8, 93.3,
99.7 ms at B = 16,384 against a 100 ms ceiling, where the finding measured 84.1
that morning. Inside a full pytest collection the same work reads 100-118 ms.
Scaling is linear and confirmed: 23.6 / 47.0 / 97.6 ms at B = 4,096 / 8,192 /
16,384.

The margin is under the machine's own variation, which is why
`docs/todo/budget-checks-under-ambient-load.md` could not settle it with a
statistic or a retry — no adjudication policy rescues a budget whose headroom
is smaller than the noise. That item's audit result stands on its own and is
finished (`tests/bench/gate.py`); what it could not do was decide this, and
this is the decision it was waiting for.

`density_rebuild` is declared in `IN_DEBT` against this item in the meantime,
so the gate stays green and the miss stays visible — which is what debt is
for, and it is the honest state while a shipped control is known wrong.
