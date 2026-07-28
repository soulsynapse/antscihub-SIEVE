---
title: What the viewport keeps of a render, and what it drops
status: deferred
opened: 2026-07-27
gated_on: >
  a planning pass — three existing caches to reconcile, a memory-budget resolver
  that does not exist yet, and HPC consequences; plan before coding.
  docs/todo/render-fed-playback.md can land its first version on a plain bounded
  ring without waiting
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

## The arithmetic, and the machine it depends on

A 1280-wide gray proxy is 0.9 MB. A 70 s window at 59.94 fps is 4196 frames:

```
whole window, 1280 gray proxies      3.8 GB
whole window, 640 gray proxies       0.9 GB
ProxyFrameCache's current bound       96 MB    ~106 proxies    ~1.8 s
```

**3.8 GB is not obviously too much, and an earlier draft of this file said it
was — wrongly.** On the reference workstation it is comfortable; on a laptop
with 16 GB shared with a browser it is not; on an HPC node it is nothing. The
number that decides is not in this file, because it is a fact about the machine.

That makes the policy **resource-derived, not constant**, and there is already a
model for exactly this in the repo: `decode/prefetch.py`'s `available_cpus()`
deliberately reports the process's affinity or cgroup allocation rather than the
machine's core count, because inside a container or a job step those differ and
the allocation is the honest answer. Retention wants the memory equivalent —
cgroup limit, `--mem` from the scheduler, or the physical figure when neither
applies — and it does not exist yet. Writing it is probably the first step of
this item rather than part of the policy.

A smaller proxy is not the escape it looks like: INTER_AREA gets *more* expensive
as the ratio grows (measured — 2.03 ms to 1280, 6.09 ms to 640), so shrinking to
fit spends render-thread CPU to save memory. Dropping the width is a real knob
and it is not a free one.

## Why this reaches further than the viewport

Two consequences worth stating before the plan starts, because they change who
the item is for:

**It is a per-user decision, not a per-application one.** The same policy that
is reckless on a laptop is timid on a workstation, and the difference between
them is a factor of thirty in what can be held. A retention rule that is one
number in the source will be wrong for most people running it; one that reads
the allocation is right for all of them and needs no setting. This is the same
argument `gui/concurrency.py` makes about cores, and it lands on the same
conclusion for a different resource.

**It bears directly on HPC** (docs/todo/hpc-handoff-and-review-mode.md). A
cluster node's memory allocation is both large and *declared* — a job step says
`--mem` and gets exactly that — which is the friendliest possible case for a
policy that reads its budget rather than guessing it, and the least forgiving for
one that does not, because exceeding a cgroup limit is an OOM kill rather than a
slow session. If retention is written against a constant now, the HPC path
inherits a number chosen for somebody's desktop.

There is also a third axis hiding here. Non-negotiable #5 says no consumer
starves another, and `gui/concurrency.py` enforces it by counting threads; the
bandwidth finding already showed that arithmetic misses the resource that
actually binds. Memory is a further one. Whatever this item concludes should
probably land *in* that module rather than beside it, so the session's claim on
the machine adds up in one place instead of three.

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
