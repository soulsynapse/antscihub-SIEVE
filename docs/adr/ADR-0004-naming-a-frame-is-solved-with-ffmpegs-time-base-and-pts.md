---
title: Naming a frame across a boundary is solved with ffmpeg's AVStream.time_base and integer pts
group: Substrate
position: 4
status: settled
decided: 2026-08-21
---

A frame's durable identity is its presentation timestamp — integer ticks in the
stream's own timebase, recorded once beside them — everywhere identity crosses a
boundary, and an ordinal is admitted only as a coordinate inside one store,
whose table says what a row means.

## Accepted

ffmpeg's `AVStream.time_base` with `AVPacket.pts` / `AVFrame.pts` — a tick count
in a per-stream rational carried once beside the stream, preserved through a
transcode so derived files map to the original with nothing stored
([the keyframe index is cheap](../findings/2026.08.21-keyframe-index-is-cheap-and-the-gop-is-fixed.md)
for the table's cost; the footage in `video-tests/` answers "how many frames"
three ways).

Binds the tooling twice: a derived file is encoded with the passthrough class of
timestamp options, never the resampling class, and a file whose timestamps were
destroyed is a new source with its own table rather than the same video.

## Rejected

Index-as-identity cautionary tale: an index is a property of a traversal, so two
tools that traverse differently disagree silently — v1 shipped it as clip-local
numbering where two replicates wrote one sidecar and the second destroyed the
first.

Frame number times a constant cautionary tale: at 90 kHz over 23.976 fps a frame
is 3753.75 ticks, so the arithmetic was never exact even before the twenty
packets that decode to nothing.
