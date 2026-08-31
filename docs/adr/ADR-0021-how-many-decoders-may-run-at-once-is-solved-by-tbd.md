---
title: How many decoders may run at once is solved by TBD
group: Substrate
position: 21
status: unsettled
decided: 2026-08-31
---

More than one decoder can be open on one recording, and how many may be
*working* at once is not the same question as how many may exist — software
workers take throughput from each other while a hardware one does not, and
nothing here has settled what the shape should be.

## Candidates

The asymmetric pair — one software decoder and one hardware decoder, each
holding its own cursor. Named in the per-activity table at
[experiments/decode-experiments/2026.08.21-best-combinations.md](../../experiments/decode-experiments/2026.08.21-best-combinations.md)
as the shape for a pipeline pass over the uncut source, and pointed at
independently by
[docs/findings/2026.08.30-the-remaining-wall-is-decode-and-a-reader-that-does-not-overlap.md](../findings/2026.08.30-the-remaining-wall-is-decode-and-a-reader-that-does-not-overlap.md),
where software suits the sequential sweep and hardware suits the interactive
cursor for the reasons ADR-0020 keeps apart. Would have to be measured with
the two actually overlapping rather than alternating, which nothing has run.

One reader per urgency band, all software — what
`experiments/orchestrator2-experiments/dispatcher.py` does now, with the bands
partitioned so the sequential reader's cursor is never taken.
[docs/findings/2026.08.30-a-second-cursor-that-overlaps-costs-a-scrub-nothing.md](../findings/2026.08.30-a-second-cursor-that-overlaps-costs-a-scrub-nothing.md)
measures the second reader as free at two, because it is idle unless somebody
is waiting, which is a different regime from the collapse below and is why two
is not yet three. Would have to be measured at three and four before the count
is anything but the two that happened to be tried.

## Rejected

N software decoders sweeping concurrently cautionary tale:
[docs/findings/2026.08.21-software-decoders-collapse-under-contention.md](../findings/2026.08.21-software-decoders-collapse-under-contention.md)
measures aggregate throughput at four wide falling *below* one worker alone,
while a hardware worker holds its rate under every shape. Decoder-per-consumer
is dead on this footage, and the number that matters is how many are decoding
at once rather than how many are open.

Scaling `readers` on the assumption that two helping means four help more
cautionary tale: the free second reader above is free because it is idle
except when a person is waiting; a third and fourth would have to be doing
something to be worth having, and doing something is the case the collapse
finding measured. The default is two and the reason is written here so it is
not read as a knob with a direction.
