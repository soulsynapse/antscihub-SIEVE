---
title: A row that cannot be decoded is solved by TBD
group: Orchestrator
position: 13
status: unsettled
decided: 2026-08-30
---

A row the decoder cannot produce has to reach the consumer waiting on it as
something other than a value, and nothing here has earned the shape of that
yet.

## Candidates

libavfilter's `ff_inlink_acknowledge_status` — permanent absence rides the
activation path as first-class link state (`AVERROR_EOF` and the error code
carried beside the frame queue), so a consumer is re-entered and told the
input will never arrive. Would have to be measured for what the extra state costs a
landing, and checked against a node that asked for several rows and lost one.

A typed negative entry in the pool — absence is stored under the key like any
other payload, distinguished by type rather than by path, which keeps `has`
the single answer to residency. Would have to be measured for whether it
leaks into the byte ceiling and whether `Request.get` can refuse it without
every node learning about it.

## Rejected

In-band sentinel cautionary tale: `dispatcher.py`'s fetch loop currently parks
`np.zeros((1, 1))` in the pool on a decode failure so `has` says yes, which
makes a hole indistinguishable from data to every node downstream and silences
the failure at the exact point something should have been told about it.
