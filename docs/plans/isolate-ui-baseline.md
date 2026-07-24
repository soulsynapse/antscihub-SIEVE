# Isolate UI Chunk 0 baseline

Captured offscreen on `2026-07-23` from:

- oracle: `antscihub-optical-flow-detector`;
- current rewrite: `antscihub-SIEVE`;
- media fixture: `test_videos/benchmark-numbered-ffv1.mkv`.

## BLUF

The oracle is a compact top strip over a 3:2 video/instrument workspace with a
480-pixel-minimum independently scrolling instrument pane and a bottom
whole-clip navigator. Current SIEVE is a 4:1 video/channel splitter followed by
two control rows, transport, and its whole-asset timeline. SIEVE has one
progressive Change-energy density plot; the oracle has a selected-channel
trace, permanent scalogram, selected density, and detection-count plot expanded
by default, with the remaining instruments collapsed.

The oracle computed surface has an actual minimum width larger than the
requested comparison canvases: the 1600-pixel capture requested a 1600-pixel
surface, but Qt resolved the widget to 1885 pixels. The PNG is deliberately
cropped to exactly 1600 pixels and the inventory records the actual geometry.
This overflow is baseline evidence, not a capture error.

The oracle computed screenshots use deterministic synthetic channel arrays to
populate the presentation surface without running or persisting oracle
scientific work. Current SIEVE computed screenshots use its real immutable
Change-energy request/result path over 64 fixture frames.

## Screenshot matrix

| Surface | State | 1600 x 980 | 1200 x 800 |
|---|---|---|---|
| Oracle | Empty | `isolate-ui-baseline/oracle-empty-1600x980.png` | `isolate-ui-baseline/oracle-empty-1200x800.png` |
| Oracle | Computed | `isolate-ui-baseline/oracle-computed-1600x980.png` | `isolate-ui-baseline/oracle-computed-1200x800.png` |
| SIEVE | Empty | `isolate-ui-baseline/sieve-empty-1600x980.png` | `isolate-ui-baseline/sieve-empty-1200x800.png` |
| SIEVE | Computed | `isolate-ui-baseline/sieve-computed-1600x980.png` | `isolate-ui-baseline/sieve-computed-1200x800.png` |

Machine-readable widget inventories accompany the 1600 x 980 captures:

- `oracle-empty-1600x980.json`
- `oracle-computed-1600x980.json`
- `sieve-empty-1600x980.json`
- `sieve-computed-1600x980.json`

## Hierarchy and geometry inventory

### Oracle

1. Compact horizontal tuning/action strip.
2. Main horizontal workspace at approximately 3:2:
   - left video, transport, replicate/readout controls, instructions, and
     scientific status;
   - right 480-pixel-minimum independently scrolling instrument column.
3. Whole-clip detection navigator and legend.

Observed computed geometry:

- video minimum: `720 x 480`;
- instrument scroll minimum width: `480`;
- video width: `1103`;
- instrument viewport width: `736`;
- expanded plot minimum height: `132`;
- collapsed plot height: `18`.

The computed surface resolved to `1885 x 980` even when asked for
`1600 x 980`. The empty surface, which has no explorer instrument stack,
remained exactly `1600 x 980`.

### Current SIEVE

1. Horizontal video/channel splitter.
2. Working-grid row and geometry readout.
3. Selected-channel compute row and resource/status readout.
4. Playback plus window start/length controls.
5. Whole-asset timeline.
6. General status line.

Observed splitter at 1600 x 980: `1249 : 325`, consistent with the configured
4:1 stretch and a 220-pixel channel minimum. There is no independent scroll
area. Both empty and computed surfaces remained exactly the requested size.

## Labels, defaults, and visible state

### Oracle top strip

- Window start `0` / `0.00 s`
- Length `5.00 s`
- Downsample `1.000`
- Block `auto (64)`
- All channels unchecked
- Use ROI clips unchecked and disabled for this fixture
- Normalize `zscore`
- Reset
- Play
- Process whole video
- Process settings

Empty status: press Play or Space to run from the window start; the navigator
states that nothing has been examined.

Computed status includes readiness, retained cube/channel memory, cube shape,
current frame/rate state, replicate identity, detection-window length, cache
identity, examined coverage, and detected duration/count.

### Oracle computed instrument defaults

- Selected-channel replicate mean: collapsed.
- Scalogram: expanded and permanent.
- Selected Change-energy block density: expanded.
- Appearance, tensor speed, intensity, shear strain rate, divergence, and
  vorticity densities: collapsed.
- Windowed blocks in band: expanded.
- Blocks in band and largest connected clump: collapsed.

Collapsed instruments use 18-pixel headers. The source distinguishes explicit
user collapse from automatic empty collapse, rendering `[+]`, `[-]`, or `[.]`
as appropriate.

### Current SIEVE defaults

- Grid hidden.
- Channel overlay shown.
- Channel `Intensity`.
- Normalize `Off`.
- Downsample `1.000`.
- Block `Auto`.
- Empty resource readout: CPU result budget 16 GiB; GPU result budget 6 GiB.
- Empty channel state: `No channels added yet.`

After Change-energy completes, the right pane contains the selected channel
context, one time-by-value density raster, and its legend. The scientific
status reports 64 completed frames. No future-stage instruments are present.

## Interaction inventory

Shared or equivalent:

- Play/pause button and Space at the owning main-window level.
- Whole-asset/whole-clip click and drag seeking.
- Window start and length editing.
- Resize and horizontal allocation changes.

Oracle:

- Drag frequency and value-band boundaries.
- Click the video to select a replicate; back/clear returns to selection.
- Click `[+]`/`[-]` plot markers to collapse or expand.
- Hold Shift to peek at the raw frame without overlays.
- Highlight-block and centered-detection-window toggles.
- Detection-window slider.

Current SIEVE:

- Left/Right steps one frame; Shift+Left/Right steps one second; Home/End seeks
  to window bounds.
- Timeline press/move scrubs without decoding every pointer position; release
  settles the decode.
- Left-clicking a density cell seeks to its absolute frame; moving over a cell
  shows its frame/value-bin tooltip.
- Grid and channel-overlay visibility are independent.
- Compute and Cancel share the one selected-channel worker.

## Current-panel performance baseline

Raw data: `isolate-ui-baseline/sieve-current-panel-performance.json`.

Setup:

- offscreen Qt, device-pixel ratio 1;
- 1200 x 800 current SIEVE `IsolateTab`;
- 64-frame real Change-energy result;
- 12 samples per path;
- full-widget `grab()` after the relevant decode/publication settles.

| Path | Median | Minimum | Maximum |
|---|---:|---:|---:|
| Unchanged full-panel paint | 2.353 ms | 2.117 ms | 19.083 ms |
| Timeline seek, decode through full-panel paint | 106.579 ms | 101.547 ms | 113.046 ms |
| Playback tick, decode through full-panel paint | 12.417 ms | 11.938 ms | 13.403 ms |

These are baseline measurements, not a speedup claim. Timeline seeking includes
random-access media decode, while playback ticks follow the sequential path.
Offscreen results do not establish native Windows compositor behavior.

## Behavior contract pinned by test

`test_change_graph_overlay_and_playback_publish_while_worker_is_running`
deliberately stalls the Change-energy worker after eight frames and verifies:

1. computation remains active while playback runs;
2. progressive density coverage is visible with an uncomputed hatched tail;
3. the overlay identity equals the authoritative displayed frame;
4. seeking during the stalled computation preserves that identity; and
5. Cancel ends the worker and clears preview density, result, and overlay state.

## Reproduction

Use the repository venv for SIEVE captures and the oracle repository venv for
oracle captures:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
$env:QT_QPA_FONTDIR = "C:/Windows/Fonts"

.\.venv\Scripts\python.exe scripts\capture_isolate_ui_baseline.py `
  sieve computed --width 1600 --height 980 `
  --video test_videos\benchmark-numbered-ffv1.mkv `
  --output docs\plans\isolate-ui-baseline\sieve-computed-1600x980.png

.\.venv\Scripts\python.exe scripts\benchmark_isolate_ui_baseline.py `
  test_videos\benchmark-numbered-ffv1.mkv --samples 12 `
  --width 1200 --height 800 `
  --json-out docs\plans\isolate-ui-baseline\sieve-current-panel-performance.json
```
