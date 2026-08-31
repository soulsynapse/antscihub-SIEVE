---
title: Fetching a frame to look at is solved with libavcodec's AVCodecContext.lowres
group: Substrate
position: 17
status: settled
decided: 2026-08-31
---

A frame fetched to be looked at is reduced to display sampling before it is
copied or held, and source sampling is kept for what will be recorded.

## Accepted

libavcodec's `AVCodecContext.lowres` — decode at 1/2, 1/4 or 1/8 inside the
decoder, as `ffplay -lowres`; unavailable for this codec, so approximated
outside it, and the two samplings of one instant come from one decode
([display sampling](../../experiments/orchestrator2-experiments/09-display-sampling.py),
[what it holds and what it bills](../findings/2026.08.31-a-display-tier-holds-a-window-at-a-sixteenth-and-bills-the-rows-the-step-reached-first.md),
[best combinations](../../experiments/decode-experiments/2026.08.21-best-combinations.md),
[the luma ceiling](../findings/2026.08.21-sequential-luma-ceiling-is-shared.md)).

## Rejected

A pool keyed by the form's string alone cautionary tale: string equality
cannot see that a held frame dominates the one wanted, so two samplings of one
row cost two decodes
([V1's question 7](../../experiments/orchestrator-experiments/07-form-negotiation.py),
[what it bills](../findings/2026.08.31-a-display-tier-holds-a-window-at-a-sixteenth-and-bills-the-rows-the-step-reached-first.md)).

Source sampling for the screen cautionary tale: a budget too small to hold
enough timeline for a playhead to stay inside it, and chosen deliberately to
make eviction load-bearing ([one cursor blacks out playback](../findings/2026.08.30-one-cursor-blacks-out-playback-for-a-whole-window.md)).

Out-of-process transport at full resolution cautionary tale: transport-bound
before it is decode-bound, where the same scale pushed into libavfilter is free
([the luma ceiling](../findings/2026.08.21-sequential-luma-ceiling-is-shared.md)).

Switching bindings for decode speed cautionary tale: cv2 and PyAV sit on one
libav and land on one ceiling, so a binding buys joints and never rate
([the luma ceiling](../findings/2026.08.21-sequential-luma-ceiling-is-shared.md)).
