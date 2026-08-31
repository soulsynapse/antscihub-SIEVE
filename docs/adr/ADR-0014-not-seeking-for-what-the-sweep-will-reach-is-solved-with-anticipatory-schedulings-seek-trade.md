---
title: Not seeking for what the sweep will reach is solved with anticipatory scheduling's seek-versus-read trade
group: Orchestrator
position: 14
status: settled
decided: 2026-08-30
---

A deferred need whose rows sit inside a wider declaration yields to it rather
than seeking, because the wider one is a sequential producer already on its way
there.

## Accepted

Anticipatory scheduling's seek-versus-read trade (Iyer & Druschel, SOSP 2001),
where the ratio here is worse than a disk's and so worth ranking on
([the pressure dispatcher preempts into seeks](../findings/2026.08.30-the-pressure-dispatcher-preempts-into-seeks.md),
[a second cursor makes preemption free](../findings/2026.08.30-a-second-cursor-makes-preemption-free.md),
[an uncut seek costs a GOP](../findings/2026.08.21-uncut-seek-costs-a-gop-not-a-frame.md)).

Deceptive idleness does not transfer and the title used to claim it: their
stronger result is to idle the device rather than seek away, which needs a gap
between requests that a declaration stating a whole window up front does not
leave. The anti-starvation half this pairs with is ADR-0015.

## Rejected

Work-conserving elevator cautionary tale: always serving whatever is queued
seeks away from a sequential stream to reach a request that stream was about to
cover.

Overlapping reader bands cautionary tale, superseded in part: one reader that
may take an interactive pick whenever free seeks off the frontier and pays to
rejoin, and the fix turned out to be a cursor per band rather than a partition
of work across one
([a second cursor that overlaps](../findings/2026.08.30-a-second-cursor-that-overlaps-costs-a-scrub-nothing.md)).
