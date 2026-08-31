---
title: A declaration that never runs is solved with the deadline scheduler's expiry queue
group: Orchestrator
position: 15
status: settled
decided: 2026-08-31
---

Every declaration carries an expiry beside its urgency, and a need past its
expiry is served next whatever its band, so no amount of interactive traffic
can hold a deferred declaration forever.

## Accepted

Linux mq-deadline's `read_expire` / `write_expire` — a FIFO queue beside the
sorted one, drained in a batch after `fifo_batch`, so an expired request is
served next whatever the elevator wanted; a floor under service rather than a
replacement for the ranking
([05-starvation](../../experiments/orchestrator2-experiments/05-starvation.py)).

`Graph.by_age` is the half `pressure_queue` does not supply — that one ranks by
urgency, subsumption and span, none of which knows how long anything has
waited.

## Rejected

Strict priority cautionary tale: ranking by urgency band bounds nothing about
how long a lower band waits, and no counter says so
([05-starvation](../../experiments/orchestrator2-experiments/05-starvation.py)).

Lowest-armed-row ordering cautionary tale: `dispatcher.Mode.ORDERED` runs only
`min(armed)`, so one row never served stalls every later row of that node with
its inputs pinned — which is why ORDERED is the probe in that experiment rather
than its subject.

CFS's `vruntime` cautionary tale: aging urgency itself would fold the guarantee
into the one ranking key, and is out for not having been run rather than on a
measurement — a second mechanism for one guarantee is the field with no
instance this shelf refuses.
