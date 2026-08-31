---
title: How many decoders may run at once is solved by TBD
group: Substrate
position: 21
status: unsettled
decided: 2026-08-31
---

How many decoders may be working at once is not how many may be open, and
nothing here has settled the shape.

## Candidates

The asymmetric pair — one software decoder and one hardware, each with its own
cursor, software suiting the sweep and hardware the interactive jump. Run now
and ahead on every axis measured, including the sweep's own wall, which leaves
the count rather than the shape open
([a hardware interactive reader in place](../findings/2026.08.31-a-hardware-interactive-reader-is-worth-four-times-more-in-place-than-alone.md),
[best combinations](../../experiments/decode-experiments/2026.08.21-best-combinations.md),
[the remaining wall](../findings/2026.08.30-the-remaining-wall-is-decode-and-a-reader-that-does-not-overlap.md)).

One reader per urgency band, all software — what
`orchestrator2-experiments/dispatcher.py` does, free at two because the second
is idle unless somebody is waiting. Would have to be measured at three and four
before the count is anything but the one that was tried
([a second cursor that overlaps](../findings/2026.08.30-a-second-cursor-that-overlaps-costs-a-scrub-nothing.md)).

## Rejected

N software decoders sweeping at once cautionary tale: aggregate throughput at
four wide falls below one worker alone, while a hardware worker holds its rate
under every shape
([software decoders collapse](../findings/2026.08.21-software-decoders-collapse-under-contention.md)).
