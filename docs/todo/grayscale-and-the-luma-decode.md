---
title: Decode the luma plane, because nothing reads chroma
status: open
opened: 2026-07-27
gated_on: >
  nothing structurally — no filter in the shelf accepts chroma, so the derived
  format is unambiguous today and the mechanism exists for the day it is not
reads:
  - src/sieve/decode/reader.py
  - src/sieve/decode/identity.py
  - src/sieve/pipeline/cache_key.py
  - src/sieve/filters/block_signal.py
---

# Decode the luma plane, because nothing reads chroma

Measured 2026-07-27 on `videos-testing/stab_GX010050c2_02_18_26.MP4`
(5312x2988, 59.94 fps), medians of 60 reads:

```
BGR  decode (CAP_PROP_CONVERT_RGB=1)     19.39 ms      47.6 MB allocated
luma decode (CAP_PROP_CONVERT_RGB=0)      7.96 ms      15.9 MB allocated
  + resize to 1280                        2.03 ms
  + GRAY2BGR on the proxy                 0.56 ms
```

The YUV→BGR convert and the 47.6 MB buffer that carries it are **11.4 ms of the
19.4**, and this chain throws the result away: `block_signal._gray`
(`src/sieve/filters/block_signal.py:223`) calls `cv2.COLOR_BGR2GRAY` at the
extraction step. Colour is decoded, downsampled, normalized, and then discarded
by the node that produces the series the detector reads.

## The difference it makes to the answer, measured

The luma plane is not the same array as today's extracted gray. They are related
by the limited→full range expansion, `ref ≈ 1.1643·luma − 19.99`, but only
approximately: this footage is BT.709 and `cvtColor(BGR2GRAY)` applies BT.601
weights, so the composition is not a scalar affine of Y. Residual after the fit
is mean 0.35/255, p99 1.30/255, max 10.7/255.

On the series the detector actually consumes — z-scored block-32 means, three
frames 9000 apart — the difference is **mean 0.004 sd, max 0.026 sd,
r = 0.99999**.

Four parts in a thousand of a standard deviation is far below what any detection
threshold resolves. That is the whole justification for doing this unconditionally
rather than offering it: there is no tradeoff to put in front of a user, because
there is no chain in the shelf whose answer changes in a way anything downstream
can see.

## Why it is derived from the graph and not simply always on

Hard-coding gray would make a colour filter unwritable — the frame would already
be luma before any node saw it, and `ArraySpec.channels` could never be
satisfied. So the format is a property of the graph: **decode luma unless some
node declares it accepts chroma.** Today no filter does, so today it is always
luma; the day a hue-reading filter lands it flips back without anyone
remembering that it had to.

This keeps the decision where the contract already is (`accepts` on the filter
spec) rather than adding a second place a chain says what it needs.

## Identity

Two things move and they are different in kind.

**How this package decodes** changed, which is `DECODE_POLICY_VERSION` in
`src/sieve/decode/identity.py:19` — its docstring already names exactly this case
("bumped by hand when this package changes how it decodes"). 1 → 2 invalidates
every cache entry once, which is correct and is the cheapest honest thing.

**Which format a given run used** is per-graph, so it also enters `source_key`
(`src/sieve/pipeline/cache_key.py:123`) beside `decoder_identity()` — the place
root pixel provenance already enters and reaches every node through the ancestry.
Without it, a future colour graph and a luma graph over the same footage would
collide. Rule 7 is satisfied without a new concept: the format changes what a
frame *is*, so it is hashed.

## Shape

**`decode/reader.py`** — `VideoReader(path, luma=True)` sets
`CAP_PROP_CONVERT_RGB=0` at open and returns `Frame(channels=ChannelSpec.GRAY)`.
Verified on this build: the FFmpeg backend logs `Unknown/unsupported picture
format: yuv420p, will be treated as 8UC1` and hands back the Y plane alone at
`(h, w)` uint8 — chroma is dropped, not delivered, so there is no colour proxy
available by this route and none should be attempted. A build that returns
something else must **raise, not reinterpret**: check the returned shape against
`(h, w)` and fail, because silently treating a packed frame as a luma plane is a
wrong answer that renders.

**`decode/prefetch.py`** — pass the flag to every reader it opens. The 47.6 →
15.9 MB drop matters twice here: the memory-bandwidth wall that
`docs/findings/2026.07.26-threading-the-reads-buys-1.6x-and-stops.md` located at
four workers is a property of the 47.6 MB buffer, so the worker optimum should be
re-measured on the luma path rather than assumed to stay at four.

**The viewport follows the pipeline.** `gui/decode_worker.py:76` reads at
`max_width=1280` for display; it takes the same format the graph resolved, so the
pane is gray whenever the chain is. This is what makes
docs/todo/render-fed-playback.md possible at all — if the pane wanted colour and
the render decoded luma, they would be two decodes again and there would be
nothing to share. A preference restores colour for anyone who wants it and
accepts the second decode.

## What to not get wrong

With the flag off, `CAP_PROP_CONVERT_RGB` is untouched and every pixel is what it
always was, so the colour path stays byte-identical and remains the fallback.

All three version constants move, and they are not redundant even though they
invalidate the same entries once: `DECODE_POLICY_VERSION` 1→2 says this build
decodes differently, `HASH_VERSION` 2→3 says `source_key`'s derivation gained a
field (which that constant's own docstring names as its case), and the field
itself says which format *this run* used. The first two are about builds, the
third about runs.

**The viewport is colour by default** (decided 2026-07-27) — the gray proxy is a
preference, stated with its measured 2x, because a grayscale video pane is a
surprise to everyone who did not choose it. The consequence is that the pane and
the pipeline are usually two formats and therefore two decodes, which bounds what
docs/todo/render-fed-playback.md can deliver: frame sharing pays off only for
someone who has opted into the gray pane. The luma decode still helps the colour
case, by making the render finish sooner and contend for less bandwidth while it
does — that is worth re-measuring once this lands, since the 1.85x contention
figure was taken with a colour render.
