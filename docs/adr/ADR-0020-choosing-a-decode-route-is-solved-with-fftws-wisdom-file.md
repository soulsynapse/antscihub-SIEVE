---
title: Choosing a decode route is solved with FFTW's wisdom file
group: Substrate
position: 20
status: settled
decided: 2026-08-31
---

Which decoder opens a source — hardware or software, and at what thread count
— is probed on this machine against this shape of file at first open and
cached under both, never assumed from a table somebody measured elsewhere.

## Accepted

FFTW's `FFTW_MEASURE` planner and the wisdom file it writes: run the
candidates once on the machine that will run them, keep the verdict, and let a
later run on different hardware re-derive rather than inherit. Settled by the
decode battery's routing results, which are what made the probe necessary —
[docs/findings/2026.08.21-uncut-seek-costs-a-gop-not-a-frame.md](../findings/2026.08.21-uncut-seek-costs-a-gop-not-a-frame.md)
has hardware decode winning on seek latency while
[docs/findings/2026.08.21-sequential-luma-ceiling-is-shared.md](../findings/2026.08.21-sequential-luma-ceiling-is-shared.md)
has it losing sequentially, so neither route is better in general and only the
pairing decides. `experiments/decode-experiments/explorer-logs/probe-cache.json`
is the cache; deleting it re-probes.

This is ADR-0007's technique applied to a different problem, and the repeat is
deliberate rather than an oversight: that one is what a *step* costs against
the input path feeding it, this one is which decoder to open, and they would
be settled by different experiments and could move independently. The shared
citation is the point — a tree that measures machine-dependent facts where
they run should look like it does that in more than one place.

**The accepted cost is that a probe's verdict can be a near-tie.** The
per-activity table at
[experiments/decode-experiments/2026.08.21-best-combinations.md](../../experiments/decode-experiments/2026.08.21-best-combinations.md)
records the probe keeping hardware on a file where sustained use slightly
favours software, which is the probe measuring a burst and the use being a
sweep. A tie broken wrongly costs a little; a table baked in from another
machine costs whatever that machine differed by.

## Rejected

Assuming hardware decode is faster cautionary tale: it is not, sequentially,
on this footage — the luma-ceiling finding puts hardware decode-with-download
behind software on a sustained read while the seek finding has it ahead by
about half on a jump. A single verdict for "NVDEC" is wrong in one direction
or the other whichever way it is written.

A checked-in route table cautionary tale: the whole battery is one machine,
which its own synthesis names as its first weakness. A table in the repository
is that weakness made permanent and invisible, since nothing goes red when it
stops being true on somebody else's hardware.
