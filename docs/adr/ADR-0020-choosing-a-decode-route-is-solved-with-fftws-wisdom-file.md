---
title: Choosing a decode route is solved with FFTW's wisdom file
group: Substrate
position: 20
status: settled
decided: 2026-08-31
---

Which decoder opens a source, hardware or software and at what thread count, is
probed on this machine against this shape of file at first open and cached
under both.

## Accepted

FFTW's `FFTW_MEASURE` and the wisdom file it writes — ADR-0007's technique on a
different problem, cached in
`experiments/decode-experiments/explorer-logs/probe-cache.json`, whose verdicts
can be near-ties
([an uncut seek costs a GOP](../findings/2026.08.21-uncut-seek-costs-a-gop-not-a-frame.md),
[the luma ceiling](../findings/2026.08.21-sequential-luma-ceiling-is-shared.md)).

## Rejected

Assuming hardware decode is faster cautionary tale: ahead by about half on a
seek and behind on a sustained read, so one verdict for it is wrong in one
direction or the other
([an uncut seek](../findings/2026.08.21-uncut-seek-costs-a-gop-not-a-frame.md),
[the luma ceiling](../findings/2026.08.21-sequential-luma-ceiling-is-shared.md)).

A checked-in route table cautionary tale: one machine's verdicts made permanent
and invisible, which the battery names as its own first weakness
([best combinations](../../experiments/decode-experiments/2026.08.21-best-combinations.md)).
