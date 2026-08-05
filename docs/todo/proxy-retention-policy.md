---
title: What the viewport keeps of a render, and what it drops
status: deferred
priority: unassessed
after: [slow-path-surfacing]
opened: 2026-07-27T21:48:22-07:00
gated_on: >
  a recorded session that scrubs, which is docs/todo/slow-path-surfacing.md's
  gesture mix to make visible. The capacity half landed 2026-07-28 in 14ce201:
  RENDER_RING_SHARE took fraction=0.01 against a 4 GB reserve — ~644 MB and so
  ~700 gray 1280-wide proxies on the finding's 68.4 GB machine, sized to reach
  a large machine's own knee rather than to hardcode the ~720 where that
  session saturated — and below ~26 GB total the 256 MB floor resolves instead,
  so a small machine pays nothing. What is left is the scrub half, and it has
  no sample: 16 scrub events, 0.00% hit under every policy. Reopening the
  eviction rule is a stall-length argument, not a throughput one, so it needs a
  recorded session that actually scrubs.
reads:
  - src/sieve/gui/transport/render_ring.py
  - src/sieve/gui/concurrency.py
  - src/sieve/bench/retention_trace.py
  - docs/findings/2026.07.28-capacity-beats-policy-in-the-render-ring.md
---

# What the viewport keeps of a render, and what it drops

The observation that opened this item (2026-07-27): the pane is frozen because
frames are **discarded, not unavailable**. `execute` decodes into a local and
releases it; the render's consumer sees every frame once and keeps none. Since
the luma decode the render produces ~88 fps against playback's 59.94, so the
producer is ahead, and everything it has produced and dropped is exactly what a
user scrubbing backwards would want.

`gui/transport/render_ring.py` answered the retention half. What is left is the *size* of
what it retains, and one question the trace could not answer.

## The change that is left

`RENDER_RING_SHARE` is `floor_bytes=256 MB` with **fraction zero**, and the
comment in `gui/concurrency.py` says why: how much of a bigger machine the ring
deserves was this item's question, and growing it there would have decided the
policy by side effect. The measurement is now in, so the fraction is this
item's to set.

Give it one. At the operating capacity of ~280 proxies, distance-from-playhead
buys 0.69 pp of hit rate over the plain ring; raising capacity from 280 to 720
buys 42 pp on the plain ring alone — capacity is worth ~60x policy, and the
portable result is that the ring deserves to grow with the allocation, not that
720 is a number to hardcode.

**What the finding does not settle, and the fraction must not pretend to:**
what a machine too small to reach its own saturation point should do. A
fraction tuned so the reference workstation lands past the knee leaves a small
machine below it, and a floor raised to compensate is the reserve competing
with the consumers it is reserved against.

Two levers, and the second is not free: the fraction, and the proxy width.
INTER_AREA gets *more* expensive as the ratio grows — measured, 2.03 ms to
1280 against 6.09 ms to 640 — so shrinking proxies to fit more of them spends
render-thread CPU to save memory.

## Do not rebuild the eviction rule

Settled by measurement, not by argument, so the rejected sides are recorded
here rather than re-derived:

- **Distance-from-playhead with the frontier pinned** — this item's own
  proposal, and the reasoning for it still reads well: eviction drops the
  retained frame farthest from the playhead, scrubbing *moves* the playhead so
  a scrubbed-to region is preferred by construction, no pin list and no decay
  constant. It buys 0.69 pp. It also costs a second eviction rule to explain
  and a playhead crossing a thread boundary to feed it.
- **LRU by access, and the plain ring** — indistinguishable from each other and
  from the proposal everywhere in the sweep.

## The scrub half, which is still open

16 scrub events in the recorded session, 0.00% hit under every policy, and this
item's own framing puts felt latency first. The trace cannot say whether that
is the policy's fault or the session's — 16 events against 12671 playback gets
is not a sample.

Stall *length* is the one metric the rejected proposal genuinely improves:
worst miss run falls 14% at the operating capacity and 23% at 1080. **If the
eviction rule is ever reopened it is reopened on stall, not on throughput**,
and the reopening needs a session that scrubs — which is a gesture-mix
question, and therefore
docs/todo/slow-path-surfacing.md's to make visible while it is still running.

## The constraint that outlives both halves

Whatever is kept must not be mistakable for truth. These are display proxies —
downscaled, single-channel, and under `max_width` semantics that
`decode/reader.py` says must never feed anything but a viewport. A retention
layer addressable by anything other than the viewport would be handing the
pipeline a cheaper route to different pixels, which is the failure
`docs/findings/2026.07.25-the-crop-belongs-in-the-graph.md` argues against in
the other direction. Nothing survives a re-render either: retention is
session-transient display state, and the moment "keep it for next time" is
worth paying for, the answer is materialization, which is truth-grade and on
disk.
