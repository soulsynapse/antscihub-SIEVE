---
title: Naming a frame across a boundary is solved with ffmpeg's AVStream.time_base and integer pts
group: Substrate
position: 4
status: settled
decided: 2026-08-21
---

The authoritative identity of a frame is its presentation timestamp — integer
ticks in the stream's own timebase, with the timebase recorded once beside
them — everywhere that identity is durable or crosses a boundary: marks,
coverage records, cache keys, sidecars, anything that names a frame to
another file or a later session. An ordinal index exists too, but only as a
per-store coordinate: row *i* of an array, derived from a frame table built
by demuxing the source at open, decode nothing. Arrays stay integer-addressed
inside a store; what a row *means* is the pts in its table entry.

## Accepted

ffmpeg's `AVStream.time_base` with `AVPacket.pts` / `AVFrame.pts` — an
integer tick count in a per-stream rational timebase, the timebase carried
once beside the stream rather than folded into every value. Settled against
the footage in `video-tests/`, which answers "how many frames" three ways —
11,328 by metadata, 11,328 by packets, 11,308 by decoded images — because it
was cut mid-GOP before SIEVE saw it and its leading packets decode to
nothing; and by
[keyframe index is cheap and the gop is fixed](../findings/2026.08.21-keyframe-index-is-cheap-and-the-gop-is-fixed.md)
for what the table costs.

What the timestamp buys is agreement without bookkeeping: the display proxy
and the cuts map to the original frame-for-frame with nothing stored, because
ffmpeg carries timestamps through a transcode, where an index mapping would
need an offset nothing verifies. It also closes an arithmetic trap this
camera sets — at a 90 kHz timebase over 23.976 fps a frame is 3753.75 ticks,
so "frame number times a constant" was never exact even before the missing
twenty.

Two corollaries bind the tooling. An encode producing a derived file must
preserve timestamps — the passthrough class of options, not the resampling
class. And a file whose timestamps have been destroyed is a *new source* with
its own table, never "the same video", which is the honest reading, since
sameness was exactly what its timestamps carried.

The accepted cost is a demux-only pass at every source's open to build the
frame table — seconds for the heaviest file measured, run off the interactive
path and cacheable beside it — and tick arithmetic confined to the one layer
that maps pts to rows, so nothing above it handles a `Fraction`.

## Rejected

Index-as-identity cautionary tale: an index is a property of a traversal —
where counting started and what was counted — so two tools that traverse
differently disagree by twenty, silently. v1 shipped this bug class as
clip-local numbering, where two replicates wrote one sidecar and the second
destroyed the first; the survey vault's P003 is the same wound in other
tools. A pts is a property of the frame itself, carried inside it.
