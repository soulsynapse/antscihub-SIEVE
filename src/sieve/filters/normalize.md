# Normalize

Per-frame contrast normalization. `zscore` maps each frame's global
statistics to a fixed mean of 128 and spread of 32; `off` passes the frame
through untouched.

## When to use it

**Use `zscore` when lighting varies and the signal is motion.** A cloud
passing over an arena, an auto-exposing camera, a flickering fixture — all of
these change every pixel at once, and a motion detector downstream reads that
global change as everything moving. Pinning each frame's mean and spread
removes the global component and leaves the local one, which is the one the
animals make.

**Leave it `off` when absolute intensity is the signal** — a brightness
threshold, a marker whose identity is its level — or when the footage is
already evenly and constantly lit and you would rather not spend the pass.

## Parameters

### `mode` (`off` | `zscore`)

`zscore` recomputes the map per frame from that frame's own statistics: mean
and spread come from the frame's grayscale projection (so the numbers the
motion extraction sees downstream are exactly the normalized ones), and the
same affine map is applied to every channel. Output is float32.

A frame with no contrast at all is centered but never divided, so a black
lead-in cannot produce a frame of infinities.

## What it does not do

It does not do `clahe` (local adaptive histogram equalization). v1 shipped it
and it is deliberately dropped: its tile grid interacts with crop edges to
produce large phantom motion at replicate boundaries (v1 measured 861 px/s of
edge speed on footage whose true motion was 48). If local normalization is
ever needed, it returns as a separate filter with that artifact solved, not
as a mode of this one.

It does not normalize across frames. Each frame is mapped from its own
statistics; a slow global drift is removed frame by frame, not modelled. The
background-model filter (`background_ema`) is the tool for structure that
persists across frames.

## Cost

One statistics pass and one fused multiply-add per frame, all SIMD — roughly
1.5 ms per megapixel. `off` costs nothing at all; the frame is handed
through, not copied.
