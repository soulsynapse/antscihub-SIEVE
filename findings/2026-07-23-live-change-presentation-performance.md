# Live Change-energy presentation performance

## BLUF

The corrected pre-rewrite-style TURBO overlay remains inside the representative
59.94 fps frame budget offscreen. Preparing a new 960x540 overlay raster took
`4.953 ms`, versus `6.219 ms` for the pre-correction selected-channel mapping;
cached steady paint was effectively unchanged (`0.806 ms` versus `0.790 ms`
median). Mapping the small `R x C` block field to TURBO before expanding it to
display pixels avoided a rejected intermediate implementation that performed
the polynomial color transform over the full display raster.

This benchmark covers the player overlay, not native-window playback or
progressive density-graph rebuild cost. The graph/playback concurrency contract
is covered separately by a deliberately stalled worker GUI test.

## Detailed benchmark setup

- Windows `10.0.26200`, Intel Family 6 Model 183 Stepping 1.
- Python `3.11.9`, repository `.venv`, PyQt offscreen platform.
- Representative 5312x2988 MPEG-4 source at `2997/50` fps:
  `test_videos/stab_GX010050c2_02_18_26.MP4`.
- Display decode: 1280x720.
- Player: 960x540, device pixel ratio 1.
- Eight decoded frames and eight synchronous repaint samples per matrix
  configuration.
- Deterministic default-grid field spanning `[0,1]`.
- Before: the milestone-7 selected-channel presentation path.
- After: Change-energy TURBO lookup table with a 99th-percentile display scale,
  applied to the small block field before display-pixel expansion.
- Operating-system and decoder caches were not flushed.

Commands:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
$env:QT_QPA_FONTDIR = "C:/Windows/Fonts"

.\.venv\Scripts\python.exe -m antscihub_sieve.gui.benchmark_viewer `
  test_videos\stab_GX010050c2_02_18_26.MP4 `
  --frames 8 --width 960 --height 540 --channel-overlays `
  --json-out findings\data\before-live-channel-graphs-offscreen.json

.\.venv\Scripts\python.exe -m antscihub_sieve.gui.benchmark_viewer `
  test_videos\stab_GX010050c2_02_18_26.MP4 `
  --frames 8 --width 960 --height 540 --channel-overlays --change-overlay `
  --json-out findings\data\after-live-channel-graphs-offscreen.json
```

## Measurements

| Measurement | Before | After | Difference |
|---|---:|---:|---:|
| New overlay preparation | 6.219 ms | 4.953 ms | -1.266 ms |
| Video + cached overlay paint median | 0.790 ms | 0.806 ms | +0.016 ms |
| Video-only paint median | 0.924 ms | 0.892 ms | -0.032 ms |
| Video + grid paint median | 5.960 ms | 5.065 ms | -0.895 ms |
| Video + overlay + grid paint median | 5.145 ms | 5.898 ms | +0.753 ms |

The after run's steady decode-to-paint median was `4.890 ms`. Overlay
preparation plus that steady median is approximately `9.843 ms`, below the
representative frame budget of approximately `16.68 ms`, although those stages
were measured separately and must not be treated as a dropped-frame guarantee.

## Comparison

The important result is that restoring the requested TURBO behavior did not
require a full-display polynomial color transform. The final path maps the
small scientific block field once through a 256-entry immutable lookup table,
then performs nearest-neighbor block-to-display indexing. That is both faster
and closer to the old OpenCV `applyColorMap` behavior.

Cached paint remains inexpensive because `IsolatePlayer` still caches by
publication token, absolute frame, mapping, display scale, and display extent.
The grid remains a larger steady presentation cost than the cached channel
layer in this controlled sample.

## Interpretation

Keep the block-first TURBO lookup path and the display-bounded cached image.
Do not restore per-display-pixel color arithmetic. Progressive graph updates
should remain coalesced: the first eight-frame preview makes the UI responsive,
then updates are limited to at most 10 Hz so graph rebuilding cannot create a
Qt event backlog.

## Potential ways this finding could be invalid now or later

- Offscreen Qt can differ from the Windows compositor and native high-DPI
  rendering.
- Eight samples do not characterize tail latency, thermal effects, or dropped
  frames.
- The deterministic field is not a distribution of real Change-energy values;
  percentile calculation itself occurs before this player benchmark.
- The before and after mappings differ intentionally, so the comparison tests
  the complete corrected presentation path rather than one isolated operation.
- Progressive graph rebuild time is not included. Dense grids, long windows,
  or many valid blocks could make that GUI-side histogram cost visible.
- Different widget sizes, device pixel ratios, grid geometry, or future zoom
  can alter expansion and paint costs.
- Actual playback overlaps decode, scientific work, queued preview delivery,
  graph rebuilding, overlay preparation, and paint. Native manual validation
  remains required.

## Raw benchmark data

- `data/before-live-channel-graphs-offscreen.json`
- `data/after-live-channel-graphs-offscreen.json`
