---
title: A declaration that never runs is solved with the deadline scheduler's expiry queue
group: Orchestrator
position: 15
status: needs experiment
decided: 2026-08-30
---

Every declaration carries an expiry beside its urgency, and a need past its
expiry is served next whatever its band, so no amount of interactive traffic
can hold a deferred declaration forever.

Settled by *(experiment not yet in this tree)*.

Prior art: Linux's deadline and BFQ I/O schedulers pair a locality heuristic
with a per-request expiry; priority aging in RTOS scheduling is the same fix
under another name.

Strict priority cautionary tale: `graph.pressure_queue` ranks by urgency band
with nothing to bound how long a lower band waits, so a sustained scrub
starves the sweep behind it and no counter says so.

Lowest-armed-row ordering cautionary tale: `dispatcher.Mode.ORDERED` runs only
`min(armed)`, so one row that is never served stalls every later row of that
node — the ordering promise and the starvation are the same mechanism.
