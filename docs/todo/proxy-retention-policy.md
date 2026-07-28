---
title: What the viewport keeps of a render, and what it drops
status: deferred
opened: 2026-07-27
gated_on: >
  a planning pass — this is a design question with three existing caches to
  reconcile and no obviously right answer, and it should be planned before it is
  coded; docs/todo/render-fed-playback.md can land its first version on a plain
  bounded ring without waiting
reads:
  - src/sieve/gui/proxy_cache.py
  - src/sieve/pipeline/cache.py
  - src/sieve/gui/player.py
  - docs/todo/render-fed-playback.md
---

# What the viewport keeps of a render, and what it drops

**Why not now.** Not because it is unimportant — it is the difference between a
viewport that follows a render and one that can *replay* it — but because it is
a policy question wearing a data-structure costume, and the wrong shape of answer
is one that makes a particular session feel smooth and cannot be reasoned about
afterwards.

The observation that opened it (2026-07-27): the pane is frozen because frames
are **discarded, not unavailable**. `execute` decodes into a local and releases
it; the render's consumer sees every frame once and keeps none. And since the
luma decode, the render produces ~88 fps against playback's 59.94 — so the
producer is ahead, and everything it has produced and dropped is exactly what a
user scrubbing backwards would want.

## The arithmetic that makes it a real question

A 1280-wide gray proxy is 0.9 MB. A 70 s window at 59.94 fps is 4196 frames:

```
whole window, 1280 gray proxies      3.8 GB
whole window, 640 gray proxies       0.9 GB
ProxyFrameCache's current bound       96 MB    ~106 proxies    ~1.8 s
```

So "keep the window" is not on the table at the proxy width the viewport
actually uses, and a smaller proxy is not the escape it looks like: INTER_AREA
gets *more* expensive as the ratio grows (measured — 2.03 ms to 1280, 6.09 ms to
640), so shrinking to fit costs CPU on the render thread to save memory.

## What has to be reconciled, which is why it wants planning

Three caches already exist and none of them is the right home as written:

* `gui/proxy_cache.py` — display proxies by frame index, 96 MB, LRU. Its
  docstring explicitly refuses playback frames, on the grounds that walking the
  timeline evicts everything a scrub warmed. A render walks the timeline too,
  and harder.
* `pipeline/cache.py` — computed frames by cache key. Keyed by *what computed
  them*, which is the right question for a node output and the wrong one for
  "the source frame at index N as the viewport would draw it".
* the player's own in-flight coalescing — one frame, not a store.

The open questions a plan has to answer, none of which a bounded ring answers by
itself: whether retention is keyed on the playhead or on the frontier; whether a
scrubbed-to region outranks a recently-rendered one; whether the policy differs
while a render is filling from when it is over; and whether any of this should
survive a re-render of the same window, which is the point at which it stops
being a viewport concern and starts overlapping materialization
(docs/todo/materialization.md).

**Constraint worth recording before anyone starts:** whatever is kept must not be
mistakable for truth. These are display proxies — downscaled, single-channel, and
under `max_width` semantics that `decode/reader.py` says must never feed anything
but a viewport. A retention layer that made them addressable by anything other
than the viewport would be handing the pipeline a cheaper route to different
pixels, which is the failure `2026.07.25-the-crop-belongs-in-the-graph.md` argues
against in the other direction.
