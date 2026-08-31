---
title: Fetching a frame to look at is solved with libavcodec's AVCodecContext.lowres
group: Substrate
position: 17
status: settled
decided: 2026-08-31
---

A frame fetched to be looked at is reduced to display sampling before it is
copied or held, and source sampling is kept for what will be recorded, because
the form decides how much of the timeline a memory budget covers and that
dominates every routing choice made downstream of it.

## Accepted

libavcodec's `AVCodecContext.lowres` — the decoder is told to produce the
picture at 1/2, 1/4 or 1/8 scale and reduces inside the decode rather than
after it; `ffplay -lowres` is the visible surface. Settled by the decode
battery: [docs/findings/2026.08.21-decode-stack-best-combinations.md](../findings/2026.08.21-decode-stack-best-combinations.md)
puts file and form choice above route choice on every access pattern SIEVE
has, and [docs/findings/2026.08.21-sequential-luma-ceiling-is-shared.md](../findings/2026.08.21-sequential-luma-ceiling-is-shared.md)
prices display-sized pushdown into libavfilter against full-resolution
transport, which it disqualifies. The per-activity table with the routes and
their costs is
[experiments/decode-experiments/2026.08.21-best-combinations.md](../../experiments/decode-experiments/2026.08.21-best-combinations.md).

**`lowres` does not cover H.264 or HEVC**, which is the footage this tree
reads, so the borrowed idea arrives one step later than libavcodec puts it:
the decoded luma plane is strided before the copy
(`experiments/decode-experiments/explorer.py`'s `luma-ds` route). That keeps
the bytes-held and residency win and gives up the decode-side win, and the gap
is written here so nobody reads the citation as a claim about what we call.

The consequence this exists to protect is residency, not per-frame speed. A
budget holds display-sampled frames by a large multiple over source-sampled
ones, so a miss becomes rare rather than cheap — which is the other half, and
is ADR-0018.

## Rejected

Fetching at source sampling for the screen cautionary tale: what
`experiments/orchestrator2-experiments/fetch.py` does, and
[docs/findings/2026.08.30-one-cursor-blacks-out-playback-for-a-whole-window.md](../findings/2026.08.30-one-cursor-blacks-out-playback-for-a-whole-window.md)
is what it cost — a window that cannot hold enough of the timeline for a
playhead to stay inside it. It was chosen deliberately, to make
declaration-derived eviction load-bearing rather than decorative, and that is
a reason to run an experiment at source sampling and not a reason to serve a
person from one.

Out-of-process decode at full resolution cautionary tale: piping
full-resolution rawvideo is transport-bound before it is decode-bound, per the
luma-ceiling finding. Pushing the scale down into libavfilter is what makes
the same arrangement free, which is the same decision as this one arriving
from the process boundary.

Choosing bindings for speed cautionary tale: cv2 and PyAV sit on one libav and
land on the same sequential ceiling, so a binding buys joints — plane views,
seek control, batch shape — and never decode rate. Recorded because "switch
the decoder" is the reflex this ADR displaces.
