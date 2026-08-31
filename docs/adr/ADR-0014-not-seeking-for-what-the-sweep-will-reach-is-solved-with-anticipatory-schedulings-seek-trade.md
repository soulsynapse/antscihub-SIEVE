---
title: Not seeking for what the sweep will reach is solved with anticipatory scheduling's seek-versus-read trade
group: Orchestrator
position: 14
status: settled
decided: 2026-08-30
---

A deferred need whose rows sit inside a wider declaration yields to it rather
than seeking, because the wider one is a sequential producer already on its
way there, and a seek buys by cursor movement what a read was about to
deliver for nothing.

## Accepted

Anticipatory scheduling's seek-versus-read trade (Iyer & Druschel, SOSP 2001)
— [the pressure dispatcher preempts into seeks](../findings/2026.08.30-the-pressure-dispatcher-preempts-into-seeks.md),
[a second cursor makes preemption free](../findings/2026.08.30-a-second-cursor-makes-preemption-free.md),
[uncut seek costs a gop not a frame](../findings/2026.08.21-uncut-seek-costs-a-gop-not-a-frame.md).
Here the ratio is worse than a disk's — a seek is about thirty sequential
reads, where on a disk it is a few — which is what makes the trade worth
ranking on at all.

**Deceptive idleness is the half that does not transfer, and the title used to
claim it.** Their stronger result is that a scheduler should idle the device
rather than seek away, because the next request from a sequential stream is
probably about to arrive and a gap between requests is not the absence of
them. SIEVE has no such gap to see through: a declaration states a whole
window up front, which is exactly the information a disk scheduler has to
infer. `graph.pressure_queue`'s docstring is where that reasoning lives.

The anti-starvation half this pairs with is ADR-0015, and it was missing here
until it was measured.

## Rejected

Work-conserving elevator cautionary tale: a scheduler that always serves
whatever is queued seeks away from a sequential stream to serve a request that
stream was about to reach, paying a seek for what a read had covered.

Overlapping reader bands cautionary tale, since superseded in part: a single
reader that may take an interactive pick whenever it happens to be free seeks
off the sweep's frontier and pays to rejoin it. What
[a second cursor that overlaps costs a scrub nothing](../findings/2026.08.30-a-second-cursor-that-overlaps-costs-a-scrub-nothing.md)
then showed is that the fix is a cursor per band rather than a partition of
work across one — with its own cursor a reader may overlap freely, and the
seek pair the partition existed to prevent is not paid.
