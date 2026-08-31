---
title: A declaration that never runs is solved by TBD
group: Orchestrator
position: 15
status: unsettled
decided: 2026-08-30
---

Ranking by urgency band bounds nothing about how long a lower band waits, and
what makes the wait finite has not been decided.

## Candidates

The deadline scheduler's expiry queue (Linux deadline, BFQ) — every
declaration carries an expiry beside its urgency, and a need past its expiry
is served next whatever its band. Would have to be measured for what a served
expiry costs the interactive path, which is the trade the whole pressure
queue exists to make.

Priority aging (RTOS scheduling, and CFS's vruntime as the fair-share form) —
a need's effective urgency rises with the time it has waited, so no band is
absolute and there is no second queue to keep. Would have to be measured for
whether the rise can be tuned without becoming the declared rank ADR-0007
falsified.

## Rejected

Strict priority cautionary tale: `graph.pressure_queue` ranks by urgency band
with nothing to bound how long a lower band waits, so a sustained scrub
starves the sweep behind it and no counter says so.

Lowest-armed-row ordering cautionary tale: `dispatcher.Mode.ORDERED` runs only
`min(armed)`, so one row that is never served stalls every later row of that
node — the ordering promise and the starvation are the same mechanism.
