---
title: A frame is its timestamp
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

Index-as-identity is what this refuses, and the footage already in
`video-tests/` is the refutation: asked "how many frames," the 5.3K source
answers three ways — 11,328 by metadata, 11,328 by packets, 11,308 by decoded
images — because it was cut mid-GOP before SIEVE ever saw it, and its leading
packets decode to nothing. An index is a property of a traversal — where
counting started and what was counted — so two tools that traverse
differently disagree by twenty, silently. v1 shipped this bug class as
clip-local numbering, where two replicates wrote one sidecar and the second
destroyed the first; the survey vault's P003 is the same wound in other
tools. A pts is a property of the frame itself, carried inside it.

What the timestamp pays for is agreement without bookkeeping. The display
proxy and the cuts map to the original frame-for-frame with nothing stored,
because ffmpeg carries timestamps through a transcode; an index mapping would
need an offset nothing verifies. It also closes an arithmetic trap this very
camera sets: at a 90 kHz timebase over 23.976 fps a frame is 3753.75 ticks,
so "frame number times a constant" was never exact even before the missing
twenty.

The accepted costs are front-loaded and small. Every source pays a
demux-only pass at open to build its frame table — seconds for the heaviest
file measured (`docs/findings/2026.08.21-keyframe-index-is-cheap-and-the-gop-is-fixed.md`),
run off the interactive path, cacheable beside it — and tick arithmetic is
confined to the one layer that maps pts to rows, so nothing above it handles
a Fraction. Two corollaries bind the tooling: an encode that produces a
derived file must preserve timestamps (the passthrough class of options, not
the resampling class), and a file whose timestamps have been destroyed is a
*new source* with its own table, never "the same video" — which is the
honest reading, since sameness was exactly what its timestamps carried.
