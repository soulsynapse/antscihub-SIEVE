---
title: A drag into unfilled ground is solved with ffmpeg's AVSEEK_FLAG_BACKWARD
group: Substrate
position: 18
status: settled
decided: 2026-08-31
---

While a drag is moving, the picture comes from the nearest keyframe at or
before the target rather than from the target itself, and the exact frame is
decoded when the hand stops — so the cost of landing somewhere nothing holds
is one frame's decode instead of a replay of the group of pictures leading to
it.

## Accepted

ffmpeg's `AVSEEK_FLAG_BACKWARD` on `av_seek_frame`, which lands on the nearest
keyframe at or before a timestamp; it is PyAV's `container.seek(...,
backward=True)` default, and the table it seeks over is avformat's
`AVIndexEntry`. Settled by
[docs/findings/2026.08.21-uncut-seek-costs-a-gop-not-a-frame.md](../findings/2026.08.21-uncut-seek-costs-a-gop-not-a-frame.md),
which establishes that the cost of an uncut seek *is* the replay from the
landing keyframe, and by
[docs/findings/2026.08.22-what-froze-the-felt-loop.md](../findings/2026.08.22-what-froze-the-felt-loop.md),
where a drag into unfilled ground was the felt freeze and the placeholder route
is what removed it. The route sits in the per-activity table at
[experiments/decode-experiments/2026.08.21-best-combinations.md](../../experiments/decode-experiments/2026.08.21-best-combinations.md)
as "kf-snap while dragging, exact on release".

**What makes this the answer and not merely an answer is that it builds
nothing.** The index is demux-only and costs what opening the file costs —
[docs/findings/2026.08.21-keyframe-index-is-cheap-and-the-gop-is-fixed.md](../findings/2026.08.21-keyframe-index-is-cheap-and-the-gop-is-fixed.md)
prices it and finds the GOP fixed on this footage, so the snap distance is
bounded and knowable per file rather than assumed. Every alternative below
buys a lower steady-state cost by making somebody wait first.

This makes a miss *cheap*. ADR-0017 makes a miss *rare*. They are different
halves and neither substitutes for the other: striding to display sampling
does nothing for a jump to ground nothing holds, and snapping to a keyframe
does nothing for how much of the timeline stays resident.

## Rejected

A built proxy cautionary tale: `src/sieve/proxy.py` serves a scrub outside the
window from a whole-recording tier at a coarse form, and the tier has to exist
before it serves anything — a full read of the recording, in the background,
while the person who wanted to look at frame 9000 waits. The pixels are right
and the shape is right; what is wrong is that its first use is behind its build.
Kept as a candidate for sustained cheap access once something has already paid
that cost, which is a different problem from this one.

A derived intra file cautionary tale: same objection, more expensive — the
proxy and cut files in the decode battery were made by an out-of-band ffmpeg
transcode of the whole source. Fastest once they exist; nothing before.

A stale nearby frame cautionary tale: `orchestrator2-experiments/explorer.py`
served the closest held row within a radius while dragging, which shows the
wrong instant at the right form and reads as the picture sticking rather than
as the picture being coarse. A keyframe is the right instant at the wrong
*time*, bounded by the GOP; a neighbour is the wrong instant, bounded by
nothing. Written down because it was reinvented in this tree after the finding
above had already retired it.
