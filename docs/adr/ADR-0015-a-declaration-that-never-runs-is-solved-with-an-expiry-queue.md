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

Linux mq-deadline's `read_expire` / `write_expire` — a second queue in FIFO
arrival order beside the sorted one, drained in a batch after `fifo_batch`, so
a request past its expiry is served next whatever the elevator wanted. Settled
by [experiments/orchestrator2-experiments/05-starvation.py](../../experiments/orchestrator2-experiments/05-starvation.py):
against a person scrubbing without pause, an ORDERED node computed 1 of 60
armed rows with no deadline and 60 of 60 with one, while the expiry queue took
0.056 of all picks doing it. A floor under service, not a replacement for the
ranking.

`Graph.by_age` is the half `pressure_queue` deliberately does not supply — that
one ranks by urgency, subsumption and span, none of which knows how long
anything has waited.

## Rejected

Strict priority cautionary tale: ranking by urgency band bounds nothing about
how long a lower band waits, and 05-starvation is that measured — one row in
sixty, with no counter saying so.

Lowest-armed-row ordering cautionary tale: `dispatcher.Mode.ORDERED` runs only
`min(armed)`, so one row that is never served stalls every later row of that
node with their inputs pinned. The ordering promise and the starvation are the
same mechanism, which is why ORDERED is the probe in 05-starvation rather than
its subject — under PARALLEL the same starvation is a node quietly falling
behind and nothing makes it visible.

CFS's `vruntime` cautionary tale: a need's urgency could age instead, folding
the guarantee into the one ranking key rather than a second queue. Not run
against the expiry queue, and out for that reason rather than on a
measurement — the queue was measured and works, and a second mechanism for one
guarantee is the field with no instance this shelf refuses. It returns as a
candidate if a workload ever shows the batch drain costing the interactive path.
