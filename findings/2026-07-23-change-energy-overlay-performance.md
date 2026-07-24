# Change-energy selected-channel overlay performance

## BLUF

The milestone-7 overlay is display-bounded and did not produce a measurable
steady-paint penalty in the controlled four-way offscreen matrix: median paint
was `0.782 ms` for video only and `0.754 ms` for video plus the selected-channel
overlay. Preparing a new 960x540 overlay raster cost `6.077 ms`. The accepted
grid remained the dominant presentation cost (`5.299 ms` alone and `5.155 ms`
with the channel overlay).

The separate direct before/after video-only samples moved from `1.151 ms` to
`1.748 ms` median steady paint. These are short, noisy runs with different
within-process phases, so no speedup or regression mechanism is claimed.
All measured configurations remained below the representative 59.94 fps
asset's `16.68 ms` frame budget offscreen. Native-window playback still requires
manual acceptance.

## Detailed benchmark setup

- Windows `10.0.26200`, Intel Family 6 Model 183 Stepping 1.
- Python `3.11.9`, repository `.venv`, PyQt offscreen platform.
- Representative source:
  `test_videos/stab_GX010050c2_02_18_26.MP4`.
- Source: MPEG-4/yuv420p, 5312x2988, `2997/50` fps.
- Display decode: 1280x720.
- Player: 960x540, device pixel ratio 1.
- Eight sequential frames and eight synchronous repaint samples per matrix
  configuration.
- Scientific overlay geometry used the default resolved source grid
  (`47` rows by `83` columns at 64 working pixels, including a partial bottom
  edge) and a
  deterministic immutable float32 field spanning `[0,1]`.
- Overlay preparation includes display-pixel to working-cell projection, value
  mapping, QImage construction, and Qt-owned copy. It excludes video decode and
  scientific computation.
- Operating-system filesystem caches were not flushed.

Commands:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe -m antscihub_sieve.gui.benchmark_viewer `
  test_videos\stab_GX010050c2_02_18_26.MP4 `
  --frames 8 --width 960 --height 540 `
  --json-out findings\data\before-change-energy-overlay-offscreen.json

.\.venv\Scripts\python.exe -m antscihub_sieve.gui.benchmark_viewer `
  test_videos\stab_GX010050c2_02_18_26.MP4 `
  --frames 8 --width 960 --height 540 --channel-overlays `
  --json-out findings\data\after-change-energy-overlay-offscreen.json
```

## Measurements

### Direct before/after video-only path

| Measurement | Before | After | Difference |
|---|---:|---:|---:|
| Steady paint median | 1.151 ms | 1.748 ms | +0.598 ms |
| Steady paint p95 | 1.636 ms | 2.910 ms | +1.274 ms |
| Steady decode-to-paint median | 4.980 ms | 5.590 ms | +0.611 ms |
| Steady decode-to-paint p95 | 7.513 ms | 7.845 ms | +0.333 ms |

### Same-process four-way presentation matrix

| Configuration | Preparation | Paint median | Paint p95 |
|---|---:|---:|---:|
| Video only | 0 ms | 0.782 ms | 1.792 ms |
| Video + grid | 0 ms | 5.299 ms | 7.353 ms |
| Video + channel overlay | 6.077 ms | 0.754 ms | 0.946 ms |
| Video + channel overlay + grid | 6.003 ms | 5.155 ms | 5.458 ms |

The overlay preparation cost occurs once for a new retained frame/mapping/
display-size cache key. Ordinary repaint reuses the cached bounded image.
Grid lines are drawn individually when the accepted density suppression rule
permits them, which explains their larger steady cost in this geometry.

Automated validation after the measurement reported `170 passed in 30.33s`
with `QT_QPA_PLATFORM=offscreen`.

## Comparison

The same-process matrix is the strongest comparison for layer cost because it
uses one decoded frame, player, process, and run phase. Within this short sample,
adding the cached channel layer changed median paint by `-0.028 ms`, which is
noise rather than evidence of a speedup. Adding the grid cost approximately
`4.5 ms`; combining the channel raster with it did not add another visible
steady penalty.

The separate pre/post runs include decode and different process/run phases.
Their approximately `0.6 ms` median increase is reported because the repository
requires before/after evidence, but the matrix does not reproduce it as a
channel-layer cost. The correct conclusion is bounded overhead with no claimed
speedup, not that painting became faster.

## Interpretation

Retain the display-bounded raster and cache. It avoids full-source-resolution
overlay traffic and makes ordinary playback paint reuse cheap. The measured
`6 ms` preparation is relevant when every accepted displayed frame changes;
it should be inspected during native-window manual playback rather than hidden
inside the steady cached-paint number.

Do not optimize the grid or overlay speculatively from these eight offscreen
samples. The combined path remains under the representative frame budget, and
the matrix points to grid drawing—not cached channel compositing—as the larger
presentation cost.

## Potential ways this finding could be invalid now or later

- Offscreen Qt painting can differ materially from a native Windows window,
  GPU/compositor path, high-DPI display, or obscured/minimized behavior.
- Eight samples are too few for stable tail latency, thermal behavior, or
  dropped-frame estimates.
- The overlay values were deterministic synthetic presentation data. Different
  mappings have similar array traffic but could differ in arithmetic cost.
- The matrix reuses one decoded frame and measures synchronous repaint; actual
  playback also includes queued delivery, per-frame overlay selection, and
  decoder scheduling.
- Preparation was called directly before repaint so its boundary is explicit.
  Normal GUI delivery spreads selection, preparation, update scheduling, and
  paint across callbacks.
- The default grid on this source is representative but not worst-case. Tiny
  blocks, different downsample, window size, or device pixel ratio can change
  both raster projection and line-drawing cost.
- Operating-system and Qt caches were warm and uncontrolled.
- Future zoom, opacity controls, alternate color maps, or additional player
  chrome may invalidate the cache key or change composition cost.

## Raw benchmark data

- `data/before-change-energy-overlay-offscreen.json`
- `data/after-change-energy-overlay-offscreen.json`
