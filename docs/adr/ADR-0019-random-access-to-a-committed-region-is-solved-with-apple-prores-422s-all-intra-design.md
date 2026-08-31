---
title: Random access to a committed region is solved with Apple ProRes 422's all-intra design
group: Substrate
position: 19
status: settled
decided: 2026-08-31
---

A region SIEVE has committed to is written back as a file in which every frame
is independently decodable, so random access into it costs one frame rather
than a replay, and the lossy-or-lossless choice is a size trade made after
that and never instead of it.

## Accepted

Apple ProRes 422 — an intra-only codec whose whole reason for existing is that
an editor jumps around inside footage, so every frame is a seek point by
design. Settled by
[docs/findings/2026.08.21-lossy-intra-beats-lossless-for-the-cut.md](../findings/2026.08.21-lossy-intra-beats-lossless-for-the-cut.md),
which cut one region five ways and found intra structure — not the codec and
not the bitrate — is what collapses random access against decoding the
original with a crop. `src/sieve/chunks.py` implements it with x264 at
`-g 1`, which is the same structural choice at a size this tree measured
against the alternatives.

**Intra is the decision; the codec is a trade underneath it.** The same finding
has a lossless entry posting the fastest random access of anything measured,
at roughly eight times the size, so "lossless loses" survives only as losing
the size-for-speed trade and not the latency race. That is a live choice per
use — a committed region somebody will re-read exactly wants different bytes
from one being kept to look at — and it is a choice this ADR deliberately does
not make.

## Rejected

An inter-coded cut cautionary tale: cutting the region while keeping a group
of pictures preserves the replay this exists to remove, and the finding
measures it losing to the intra cut of the same codec at the same quality on
random access while winning only on size.

CineForm cautionary tale: rejected on two measurements — larger than the
lossless entry it was competing with, and drags an order slower — recorded in
the per-activity table at
[experiments/decode-experiments/2026.08.21-best-combinations.md](../../experiments/decode-experiments/2026.08.21-best-combinations.md).
Measured through ffmpeg's `cfhd` decoder, which may not represent GoPro's own,
so the door is not nailed shut.

Transcoding a whole recording up front cautionary tale: the derived files in
that battery were made out of band over the entire source, which is the build
cost ADR-0018 refuses for the interactive case. This ADR is about a region
somebody has already committed to, where the encode is bounded by the
commitment and the person is not waiting on it to look at something.
