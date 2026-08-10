---
title: The epsilon admission is closed, and only a bounded declaration reopens it
adr: 33
position: "04.03.01"
status: settled
decided: 2026-08-09
---

The measured-epsilon admission ADR 17 left open is refused: a residual under a
tool's declared threshold flips a detection. An epsilon warmup is keyed by
becoming bounded, never by measuring small.

Why: [cache-admission-is-bounded-warmup](cache-admission-is-bounded-warmup.md)
refuses `background_ema` and `temporal_baseline` a key and leaves one way back
in, on a question it declined to answer from the armchair.
[findings/2026.08.09-a-sub-epsilon-residual-flips-a-detection.md](../findings/2026.08.09-a-sub-epsilon-residual-flips-a-detection.md)
builds that admission as the store would serve it and carries both foregrounds
into `detect`. The refutation the door was left open for was `inband_count` — a
quantizer, where small differences are supposed to go and die. It does not
happen, because the count is *windowed* before it is thresholded: one block
crossing the floor at one frame of the window moves the mean by a fraction of a
block, and the gate compares against that. The quantizer is followed immediately
by an average that un-quantizes it. The narrowing that looked like a second
rescue — a crop feeding the model in `uint8` — measures worse rather than
safer, because rounding sends a fraction of a level to a whole one wherever two
models straddle a boundary.

The question was never whether the residual is small. A gate is a threshold and
a threshold has no tolerance, so the only admitting answer was zero. What
settles it as a product question rather than an arithmetic one is *where* the
residual moves the count: against the shoulder of the count's range, which is
where a tuned threshold sits, because the tuning gesture is dragging the handle
down until the detection appears and leaving it. The failure mode and the
gesture VISION is built around share an address. This is
[correctness-is-the-default](correctness-is-the-default.md)'s bit-identity bar
meeting the case it was written for, so the bar is not merely conservative.

`temporal_baseline` is refused by the same rule on a mechanism that is shared
and an arithmetic that is not — nothing here measures it, and nothing needs to:
a refusal does not rest on a measurement per tool, an admission would.

What the refusal costs is real and is not this ADR's to relieve. A graph with an
unkeyed model in it re-walks its lead-in arithmetic on every render, though not
its decode wherever something keyed sits above the model
([findings/2026.08.09-the-epsilon-chain-repeats-its-lead-in-arithmetic-not-its-decode.md](../findings/2026.08.09-the-epsilon-chain-repeats-its-lead-in-arithmetic-not-its-decode.md)).
Because the cost is the tools and not the reader, only a materialized product
upstream of the model removes it — `todo/crop-serving-and-checkpoint-read-back-become-source-tools.md`,
whose halves are now done and whose remedy is therefore unblocked. Admission was
the cheap way out of that bill and it is the one that is closed; the ratchet
turns one way, and a later session meeting this paragraph meets a measurement
rather than an invitation.
