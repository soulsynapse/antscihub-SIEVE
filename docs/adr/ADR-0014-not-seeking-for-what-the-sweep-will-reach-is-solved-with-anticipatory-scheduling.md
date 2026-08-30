---
title: Not seeking for what the sweep will reach is solved with anticipatory scheduling's deceptive idleness
group: Orchestrator
position: 14
status: settled
decided: 2026-08-30
---

A deferred need whose rows sit inside a wider declaration yields to it rather
than seeking, because the wider one is a sequential producer already on its
way there, and a seek buys by cursor movement what a read was about to
deliver for nothing.

Settled by [the pressure dispatcher preempts into seeks](../findings/2026.08.30-the-pressure-dispatcher-preempts-into-seeks.md),
[a second cursor makes preemption free](../findings/2026.08.30-a-second-cursor-makes-preemption-free.md),
and [uncut seek costs a gop not a frame](../findings/2026.08.21-uncut-seek-costs-a-gop-not-a-frame.md).

Prior art: Iyer & Druschel, *Anticipatory scheduling: a disk scheduling
framework to overcome deceptive idleness in synchronous I/O*, SOSP 2001.

Work-conserving elevator cautionary tale: a scheduler that always serves
whatever is queued seeks away during the gap between a sequential stream's
synchronous requests, destroying the locality it was about to exploit — the
idle queue is deceptive, not empty.

Overlapping reader bands cautionary tale: a reader that may take an
interactive pick whenever it happens to be free is a reader that seeks off
the sweep's frontier and pays to rejoin it, which is the cost the partition
exists to remove.
