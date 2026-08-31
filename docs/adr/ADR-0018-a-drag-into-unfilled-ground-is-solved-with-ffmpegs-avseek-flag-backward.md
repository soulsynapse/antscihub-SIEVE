---
title: A drag into unfilled ground is solved with ffmpeg's AVSEEK_FLAG_BACKWARD
group: Substrate
position: 18
status: settled
decided: 2026-08-31
---

While a drag is moving the picture comes from the nearest keyframe at or before
the target, and the exact frame is decoded when the hand stops.

## Accepted

ffmpeg's `AVSEEK_FLAG_BACKWARD` over avformat's `AVIndexEntry` — PyAV's
`seek(..., backward=True)`; alone among the candidates it builds nothing, the
index being demux-only at open cost
([an uncut seek costs a GOP](../findings/2026.08.21-uncut-seek-costs-a-gop-not-a-frame.md),
[the keyframe index is cheap](../findings/2026.08.21-keyframe-index-is-cheap-and-the-gop-is-fixed.md),
[what froze the felt loop](../findings/2026.08.22-what-froze-the-felt-loop.md)).

## Rejected

`src/sieve/proxy.py` cautionary tale: a full background read of the recording
stands between it and its first serve, which is the wait this problem is about.

A derived proxy or cut file cautionary tale: the same wait by out-of-band
transcode, and fastest of anything once it exists
([best combinations](../../experiments/decode-experiments/2026.08.21-best-combinations.md)).

A stale nearby frame cautionary tale: the wrong instant bounded by nothing,
where a keyframe is the right instant bounded by the GOP; reinvented in
`orchestrator2-experiments/explorer.py` after
[what froze the felt loop](../findings/2026.08.22-what-froze-the-felt-loop.md)
had retired it.
