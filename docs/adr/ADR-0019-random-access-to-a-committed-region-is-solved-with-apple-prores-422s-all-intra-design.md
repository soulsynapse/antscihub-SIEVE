---
title: Random access to a committed region is solved with Apple ProRes 422's all-intra design
group: Substrate
position: 19
status: settled
decided: 2026-08-31
---

A region SIEVE has committed to is written back all-intra so random access into
it costs one frame, and the lossy-or-lossless choice is a size trade made under
that rather than instead of it.

## Accepted

Apple ProRes 422's all-intra design — every frame a seek point because an
editor jumps; `src/sieve/chunks.py` writes the same structure with x264 `-g 1`
([lossy intra beats lossless for the cut](../findings/2026.08.21-lossy-intra-beats-lossless-for-the-cut.md)).

## Rejected

An inter-coded cut cautionary tale: keeps the replay this exists to remove,
losing random access to the intra cut of the same codec at the same quality and
winning only size
([lossy intra](../findings/2026.08.21-lossy-intra-beats-lossless-for-the-cut.md)).

CineForm cautionary tale: larger than the lossless entry and drags an order
slower, through ffmpeg's `cfhd` rather than GoPro's own
([best combinations](../../experiments/decode-experiments/2026.08.21-best-combinations.md)).
