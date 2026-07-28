---
title: Render-fed playback, and the frontier it loops at
status: open
opened: 2026-07-27
gated_on: >
  nothing structurally — but take docs/todo/grayscale-viewport-toggle.md FIRST;
  this is the second of the two, and the pane being able to go gray is what lets
  the render's frames feed it at all
reads:
  - src/sieve/gui/player.py
  - src/sieve/gui/preview_runner.py
  - src/sieve/pipeline/executor.py
  - src/sieve/gui/preferences.py
---

# Render-fed playback, and the frontier it loops at

Priority **2 of 2**, after docs/todo/grayscale-viewport-toggle.md. The
dependency is real and not just sequencing: the pipeline decodes luma, so frames
the render could hand the player are single-channel. A colour viewport and a
luma render are two formats and therefore two decodes, which is the thing this
item exists to stop — so the pane must be able to go gray before its frames can
come from anywhere but its own reader.

While a window render is filling, the same frames are decoded twice: the
preview's `PrefetchFrameSource` decodes the window at full resolution to compute
the graphs, and the player's decode thread decodes the very same source frames
again to show them. They are two readers over one file, and they contend on the
resource that is actually scarce.

Measured 2026-07-27, reference footage, player read path exactly as
`DecodeWorker.request_frame` performs it:

```
player alone              22.7 ms/frame   44.1 fps
player + preview(2)       41.9 ms/frame   23.9 fps      1.85x slower
  preview throughput      22.4 ms/frame
```

Against a 59.94 fps source the player is at 0.74x real time before anything else
runs, and 0.40x while a render fills. That is the freeze.

**Why a shorter window does not help, which is the observation that opened
this.** Render wall-time is `N x 22.4 ms` and watching the same window is
`N x 16.7 ms`. Both are linear in the frame count, so the ratio is invariant:
whatever window is chosen, the render takes about as long as one pass of
watching it. Shortening the window shortens the freeze and the thing being
watched by the same factor.

## A frozen pane is the deception, and that is the actual defect

Sharpened 2026-07-27, and it changes what this item is for. The complaint is not
that playback is slow. It is that a pane which stops updating **reads as a
crashed application** — the user's conclusion is "the software is on the fritz",
not "the render is busy". Choppy playback is strictly better than frozen
footage, because choppy is legible: it says work is happening and this is what it
costs.

That is rule 6 from its second direction. The rule's mirror clause says a control
must never look more live than it is; a viewport that freezes solid during a
render breaks the same rule the other way round, by looking *dead* when the
system is working perfectly. Neither state is honest, and the fix for both is the
same: show what is actually going on.

Which suggests the simplest possible version of this item, and probably the one
to build first: **while a render is filling, show the frame the render is
currently processing.** Not a cache, not a ring, not a frontier — the consumer
already receives every frame in order, so the pane can simply follow it. It is
honest by construction (that frame *is* what the system is doing), it costs one
downscale, and it removes the second decode. Playback ceases to be wall-clock
during a render, which the section below rejects for the transport in general —
but this is not the transport pretending to run at speed, it is a different and
truthful mode: "following the render".

The measured case for it, from
`docs/findings/2026.07.27-decode-is-a-bandwidth-wall-shared-by-two-consumers.md`:
speeding the render up does not help the player at all (a 1.88x faster render
made playback 23.8 -> 19.6 fps, because the two contend for bandwidth and a
faster consumer draws harder). Removing a consumer is the only thing that works.

## The shape, and the one that was rejected

The obvious fix is to let the player display the render's frames — the render has
already decoded them — and pace playback at the render's rate. **Rejected as the
transport's behaviour**, though not as a labelled mode (see the section above):
playback that *silently* runs at 0.75x is a transport lying about time, and the
speed the user is watching at is not a thing to trade for throughput without
saying so.

So, for the transport proper: the player keeps its wall clock and full speed, and takes frames from the
render when the render has them. Because the player is faster than the render,
it reaches the **frontier** — the last frame the render has produced — and
instead of stalling there it loops back to the window start and replays the
prefix that exists. The window fills behind it while it loops over what is
filled. There is always something moving to watch, it moves at the right speed,
and no frame is decoded twice.

This mirrors the frontier the graphs already carry (`DetectorResult.settled`,
`gui/detector_worker.py`), and it should read as the same idea to a user: the
picture and the graphs are both honest about how much of the window exists yet.

## Shape

**The source frame has to escape the executor.** `execute` decodes into a local
`source` (`src/sieve/pipeline/executor.py:170`) and drops it. `FrameResult` gains
it — `source: Frame | None`, `None` when every root was served from the store and
no decode happened, which is exactly the warm re-render where there is nothing to
share and nothing to want. Carrying it costs nothing: the docstring's own
argument for holding every node's output ("the cost of carrying them is one frame
per node held for as long as the caller holds this") extends unchanged.

**The proxy is made on the render thread**, in the consumer, where the pixels
already are: a resize to the proxy width, ~2.0 ms. Doing it on the GUI thread
would put a full-resolution resize in front of every repaint.

**The player gains a source of frames that is not its decode thread**, and a
frontier. `VideoPlayer._request` should consult the render's ring before issuing
a decode, and `timerEvent`'s `playback_step` should fold at the frontier rather
than at the window end while a render is filling. `gui/timeline_model.py`'s
`playback_step` is where the fold already lives.

**A preference toggles it** (`gui/preferences.py`, beside `adaptive_scrub`,
which is the same kind of switch: an automatic behaviour the user may not want).
Off means today's behaviour — the player decodes independently and stutters,
which is the right choice for someone who needs true wall-clock coverage of the
whole window more than they need smooth motion.

## The frames are discarded, not unavailable — and the render now outruns playback

Noted 2026-07-27, and it moves this item's centre of gravity.

The pane is frozen because the render's frames are *thrown away* after the
consumer has looked at them, not because they do not exist. `execute` decodes
into a local and drops it (`pipeline/executor.py:170`); the consumer sees each
frame once, on the render thread, and nothing keeps it. Every pixel the viewport
wants has already been decoded and then deliberately released.

And since the luma decode landed, the producer is **faster than real time**:

```
render, luma, 2 workers      11.2-11.4 ms/frame     ~88 fps
playback at source rate      16.7 ms/frame          59.94 fps
```

That inverts the premise the section above was written on. When this item was
scoped the render was 22.4 ms a frame and the player would outrun it, which is
what the loop-at-the-frontier mechanism exists to handle. At 11.2 ms the
frontier outruns the *playhead* instead, and it pulls further ahead the moment
the player stops decoding and stops competing for bandwidth. So in the steady
state there is no frontier to fold at — only at the very start, before the
render has any lead, and after a seek backwards into a region already passed.

The loop is still worth building as the honest behaviour at the edge, but it
stops being the main path. The main path is: keep what the render produced, and
play it.

**Which makes retention the real question, and it is a planning job rather than
a coding one.** A window of 1280-wide gray proxies is 0.9 MB a frame — 3.8 GB for
70 s at 59.94 fps. Whether that is affordable is a fact about the machine, not
about this repo: comfortable on the reference workstation, reckless on a laptop,
trivial on an HPC node. So the policy has to read its budget rather than carry
one, which is docs/todo/proxy-retention-policy.md — deferred to a planning pass
rather than decided inline, because a retention rule chosen to make one demo
smooth is how a cache becomes something nobody can reason about.

This item does not wait on it. A plain bounded ring is enough for the first
version, and the ring's size is exactly the knob that item exists to replace.

**The v1 ring's bound, fixed 2026-07-27 so it does not get invented at the
keyboard:** 256 MB — ~280 proxies, ~4.7 s at 59.94 fps — declared as a named
constant beside `ProxyFrameCache`'s bound with a comment saying the resource
ledger (docs/todo/resource-ledger.md) owns the real answer. Enough that the
playhead following a few seconds behind the frontier never misses, small
enough to be safe on a 16 GB machine even with the browser open. It is a
placeholder with a stated successor, which is the honest kind.

## What to not get wrong

The ring is bounded and small. A full window of 1280-wide proxies is 4200 x 2.8
MB = 11.8 GB, so this is a ring over the render's recent output, not a cache of
the window — and the loop-at-frontier behaviour is what makes a small ring
sufficient, because the player is never far from the frontier by construction.

`ProxyFrameCache` is deliberately not the place to put these
(`gui/proxy_cache.py` says why: playback would evict everything a scrub warmed).
This is a separate, render-owned buffer with a different lifetime.

The frontier must not be confused with the settled frontier. The render's
frontier is "the last frame that exists"; `DetectorResult.settled` is "the last
frame whose value will not change". They move differently and mean different
things, and a player folding at the wrong one would replay frames that are about
to be superseded.
