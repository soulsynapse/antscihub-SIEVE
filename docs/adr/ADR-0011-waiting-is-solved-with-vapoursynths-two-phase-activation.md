---
title: Waiting on an input is solved with VapourSynth's two-phase activation
group: Orchestrator
position: 11
status: settled
decided: 2026-08-30
---

A consumer is called twice — once to declare what it needs and return, once
to compute with those inputs resident — and never blocks or polls, because it
is never running at a moment when it would have to wait.

Settled by [experiments/orchestrator2-experiments/01-reentry.py](../../experiments/orchestrator2-experiments/01-reentry.py)
and [re-entry removes the poll interval and not the wall](../findings/2026.08.30-re-entry-removes-the-poll-interval-and-not-the-wall.md).

Corroborated independently: libavfilter's `AVFilter.activate` arrived at the
same shape under the same constraint (`ff_inlink_request_frame`, return
`FFERROR_NOT_READY`, re-enter on link change).

libavfilter's original `filter_frame`/`request_frame` pair cautionary tale:
push and pull mixed in one API recursed arbitrarily deep through the graph,
every filter had to be written as though it could block, and the rewrite to
`activate` was the fix.

Polling cautionary tale: this tree's own V1 ran three intervals — 5 ms per
tool thread against a ten-second deadline, 4 ms in the dispatcher, 2 ms in
the Qt thread — asking one question the decoder already knew the answer to.
