# Isolate UI port plan

Reviewed against the oracle UI and the current SIEVE checkout:
`2026-07-23 22:10:47 -07:00`.

## BLUF

Port the pre-rewrite Isolate/Preprocessing surface as the interaction and
visual contract, but do not port its ownership mistakes. SIEVE keeps its
current active-asset controller, `IsolateSession`, media service, immutable
scientific requests/results, resource admission, and single selected-channel
worker. The port supplies the compact tuning strip, video/transport surface,
scrollable right-side instrument stack, collapsible plot chrome, and bottom
navigator.

The port is divided into acceptance-sized chunks below. Each chunk must leave
the GUI runnable and the complete test suite passing. Later scientific stages
are represented honestly as unavailable instruments until their headless
application contracts exist.

This file is the durable handoff for context resets. Update the status table,
the most recent checkpoint, and the next action after every accepted chunk.

## Current working-tree warning

Chunk 0 removed the preliminary `isolate_instruments.py` shell and restored
the last accepted `_build_ui` layout while preserving the interleaved,
previously accepted progressive Change-energy work. The shell is not a
completed instrument chunk and must not be revived as an implementation
shortcut.

## Reference surface

Oracle files used as behavior and presentation evidence:

- `gui/explorers/live_scalogram_surface.py`: compact tuning/action strip and
  live-surface ownership.
- `gui/explorers/scalogram_explorer.py`: video/transport layout, scrollable
  instrument column, plot selection, and detection-sweep arrangement.
- `gui/explorers/plots.py`: plot palette, collapse semantics, cursor/seek
  behavior, render caching, density rendering, and coverage presentation.
- `gui/explorers/detection_timeline.py`: whole-clip navigation language.
- `FINDINGS.md` sections 17, 18, and 24: measured performance and correctness
  traps behind the UI.

Current SIEVE seams that remain authoritative:

- `gui/isolate_tab.py`: composition and GUI request snapshot owner.
- `gui/isolate_session.py`: Isolate-local playhead, window, display decoder,
  request coalescing, and stale-frame rejection.
- `gui/isolate_player.py`: Qt image ownership plus grid/channel presentation.
- `gui/intensity_panel.py`: current progressive time-by-value density
  presentation.
- `gui/intensity_worker.py`: one current worker, newest pending request, and
  coalesced progressive publication.
- `application/intensity.py`, `application/change_energy.py`, and
  `application/channel_progress.py`: headless scientific contracts and
  immutable progressive frame views.
- `gui/isolate_timeline.py`: current whole-asset navigation contract.

## Target layout

```text
+ compact tuning and action strip -----------------------------------------+
| start | length | scale | block | channel | normalize | run/stop | status |
+-------------------------------------+------------------------------------+
|                                     | Selected channel                   |
| video                               |   trace                            |
|                                     |   scalogram                        |
|                                     | Per-block band power               |
|                                     |   selected channel density         |
| transport / playhead / achieved fps |   other channel instruments        |
| active-asset readout                | Detection sweep                    |
| overlay and display toggles         |   count / clump instruments        |
| activity and memory status          |                  [scrollable]       |
+-------------------------------------+------------------------------------+
| whole-asset navigator with selected window and absolute playhead         |
+--------------------------------------------------------------------------+
```

The starting split is 3:2, with a minimum 480-pixel instrument pane. The
splitter remains user-adjustable. The instrument column scrolls independently;
adding plots must not continually squeeze the video.

## Current-control mapping

| Oracle control/surface | SIEVE mapping | Port decision |
|---|---|---|
| Window start and length | `start_spin`, `length_spin` | Port to top strip |
| Downsample | `downsample_spin` | Port unchanged |
| Block Auto/explicit | `block_intent_combo`, `block_size_spin` | Port unchanged |
| Selected channel | `channel_combo` | Port unchanged |
| Normalize | `normalization_combo` | Port unchanged |
| Play/stop pass | current compute/cancel plus playback state | Preserve current semantics; do not create a second pass owner |
| Video transport | `IsolateSession` and `play_button` | Port placement, retain controller |
| Grid visibility | `show_grid_check` | Keep near video presentation controls |
| Channel overlay | `show_channel_overlay_check` | Keep near video presentation controls |
| Whole-clip navigator | `IsolateTimeline` | Port visual language incrementally; retain absolute-frame contract |
| Inherit | no equivalent | Omit; SIEVE owns its Isolate-local playhead |
| Use ROI clips | active child asset is already the isolate | Omit; do not revive region translation |
| Replicate selector | active asset controller | Omit; selection occurs in Replicates |
| All channels | no multi-channel scheduler yet | Disabled presentation only, or omit until useful |
| Process whole video | no accepted whole-clip scientific runner yet | Disabled and explicitly unavailable; no fake action |
| Detection tuning | no accepted Morlet/detection nodes yet | Visible plot shells only; controls disabled |

## What is in scope

1. Match the oracle's layout hierarchy, spacing, plot ordering, compactness,
   colors, typography, and scroll behavior closely.
2. Preserve the current live behavior: playback begins during computation,
   density coverage fills progressively, and the exact displayed frame receives
   the matching overlay.
3. Port reusable GUI-only plot primitives without importing oracle `core.*`
   modules or cache-era state.
4. Display unavailable later plots as unmistakably uncomputed/unavailable.
5. Retain absolute-frame cursor, click-to-seek, resize, splitter, and collapse
   interactions.
6. Add structural, interaction, rendering, and performance regression tests.
7. Capture offscreen screenshots at agreed window sizes after every visual
   chunk and perform a final native-Windows review.

## What is not in scope

- Morlet/scalogram calculation.
- Frequency-band, value-band, count-band, or clump math.
- Static filtering, detection, behavior classification, or detected badges.
- A whole-video processor, process schedules, track persistence, or exports.
- A multi-channel scheduler, plugin/registry system, or generic computation
  graph.
- New scientific channels such as speed, coherence, divergence, or vorticity.
- Reintroducing the retired flow cache, pooled-region model, or ROI-clip toggle.
- Moving Qt objects, widget dimensions, or GUI generations into scientific
  identity.
- A general theme/visual redesign. This pass copies the proven instrument UI;
  modernization is separate.
- Changing scientific formulas, units, normalization, temporal alignment,
  resource admission, or retained-result ownership.

## UI-entangled machinery that should be ported

These mechanisms are presentation work even though they contain algorithms.
They are part of why the oracle surface remained responsive and legible.

### Port during the UI work

1. **Two independent collapse states.** User-collapsed and auto-collapsed-empty
   are different state. Data arrival must not reopen something the user closed,
   and an empty plot must not advertise a working `[+]` action. Preserve the
   oracle's `[+]`, `[-]`, and `[.]` language and 18-pixel collapsed header.
2. **Real collapsed fast path.** A collapsed plot returns before expensive
   painting, does not queue `update()` for cursor/data changes, and releases
   only reconstructible render images. It does not discard authoritative
   scientific arrays.
3. **Versioned render memoization.** Cache data range, decimated envelope,
   painter polygon, and raster image by explicit data version, dimensions, and
   presentation settings. Cursor movement must not rebuild data-derived
   geometry.
4. **Burst-preserving line decimation.** Use maximum-in-column envelopes, not
   means, so short behavior bursts survive long-series display compression.
   Signed plots may require a min/max envelope when they arrive.
5. **Screen-resolution density rasterization.** Bin directly to the rendered
   `width × height` image rather than constructing a frame-by-block GUI image.
   Keep SIEVE's owned-area weighting and scientific value-axis mapping.
6. **Exact axis registration.** Every plot carries absolute processed start and
   span. Cursor, seek, data, and coverage map through that identity. Progressive
   coverage hatching is derived from the covered span, using a ceiling at its
   right pixel edge; it is not inferred from which pixel columns happened to
   receive samples.
7. **Sticky but resettable value ranges.** Repeated live windows may widen the
   display range, but ordinary refresh must not make thresholds or colors drift.
   Reset only when the measured quantity or scientific presentation changes.
8. **Frozen overlay scale.** The expensive percentile scale is prepared outside
   the per-frame paint path and remains stable for the accepted run. Current
   SIEVE already implements this boundary; retain it.
9. **Latest-only display publication.** Retain worker progress coalescing and
   stale-token rejection. Do not queue every intermediate plot refresh.
10. **Qt-owned image lifetime.** Any NumPy-backed `QImage` used beyond the paint
    call owns/copies its bytes explicitly.

Oracle evidence measured all-expanded plotting at about 3.2–3.3 times the
cursor-scrub cost of all-collapsed plotting for the tested surface. Treat
collapse as a performance feature, not decorative accordion behavior. Re-run a
SIEVE-native benchmark rather than claiming the oracle ratio transfers.

### Preserve as design constraints for later scientific chunks

These were entangled with widgets in the oracle, but must become headless
application/scientific operations before SIEVE connects them:

1. Pooled channel mean and pooled Morlet can feed cheap selected-channel views,
   but Morlet is scientific math and must not live in a Qt widget.
2. Per-block Morlet cubes and frequency-band sums remain lazy, bounded, and
   backpressured. Their visibility may control optional presentation
   preparation, never authoritative detection computation.
3. Detection gate and clump series are application results. A widget may paint
   them but must never be their only owner.
4. A selected detector channel must continue to compute even when its plot is
   collapsed. The oracle nearly shipped a silent false negative by coupling
   visibility to calculation.
5. Single-frame detections receive at least one display pixel, and edge-touching
   runs must survive span extraction, when detection presentation eventually
   arrives.
6. If a slow scalogram and fast traces cover different spans, pad them onto the
   same absolute axis and hatch the unexamined portion. A “stale” badge does not
   repair geometric x-axis misregistration.

## Implementation chunks and acceptance gates

### Chunk 0 — Baseline and contract inventory

Status: completed; awaiting user acceptance.

- Review and resolve the preliminary unvalidated shell diff.
- Capture oracle and current-SIEVE screenshots at the same 1600×980 and
  1200×800 sizes, empty and with a computed Change-energy window.
- Record widget hierarchy, labels, default expanded/collapsed states, minimum
  sizes, splitter proportions, keyboard/mouse gestures, and visible status
  lines.
- Add a current-SIEVE behavior test covering compute-while-playing, progressive
  density, overlay/frame identity, seek, and cancel.
- Benchmark current cursor/playback painting with the current visible panel.

Acceptance: no intended behavior change; baseline artifacts and tests exist.

### Chunk 1 — SIEVE-native instrument primitives

Status: planned.

- Add GUI-only palette, section label, collapsible plot base, and empty
  instrument body.
- Implement separate user/auto collapse, cached-render release, and no-update
  collapsed paths.
- Port line envelope and pixel-bar primitives without oracle scientific imports.
- Unit-test collapse state transitions, empty state, cache invalidation, cursor
  repaint behavior, and seek mapping.
- Benchmark collapsed versus expanded cursor movement.

Acceptance: primitives run in a standalone offscreen harness; `IsolateTab`
layout is not changed yet.

### Chunk 2 — Layout shell

Status: planned.

- Move existing controls into the compact top strip.
- Build left video/transport/status column.
- Build the independently scrollable 480-pixel-minimum instrument column.
- Place selected-channel, per-block, and detection-sweep sections in oracle
  order.
- Keep unsupported controls disabled with direct tooltips.
- Keep `IsolateTimeline` as the bottom navigator.

Acceptance: all existing Isolate behavior tests pass, unavailable controls
launch no workers, and screenshot review confirms geometry before data wiring.

### Chunk 3 — Current selected-channel presentation

Status: planned.

- Adapt the current progressive density raster to the shared instrument chrome.
- Add the selected-channel trace from the already-authoritative result/progress
  frames as presentation-only aggregation; do not retain a second scientific
  tensor.
- Preserve absolute-frame cursor, click-to-seek, covered/uncomputed hatching,
  units, current-value readout, and Off/z-score mappings.
- Preserve current live overlay and frozen run scale.

Acceptance: Intensity and Change energy both play during computation, fill the
graphs progressively, keep overlay/frame identity exact, and invalidate cleanly
on request changes.

### Chunk 4 — Navigator and interaction parity

Status: planned.

- Port the oracle navigator colors and coverage vocabulary only where current
  SIEVE state can support them honestly.
- Retain current window selection and whole-asset scrubbing.
- Port applicable hotkeys and raw-frame peek only after inventory confirms they
  do not conflict with current main-window shortcuts.
- Add achieved-rate readout from measured presentation cadence if it can be
  derived without changing playback timing.

Acceptance: mouse and keyboard interaction matrix passes; hidden Isolate and
collapsed plots do not repaint unnecessarily.

### Chunk 5 — Future-stage shells

Status: planned.

- Add the remaining oracle plot names and controls as presentation shells.
- Use one consistent unavailable state, not fake zero-valued data.
- Do not allocate scientific arrays, start workers, or include unavailable
  settings in request/cache identity.

Acceptance: the intended finished workflow is spatially legible, while every
unimplemented stage is unmistakable and inert.

### Chunk 6 — Integrated validation and cleanup

Status: planned.

- Run focused GUI tests, full offscreen suite, import/compile checks, and the
  same before/after rendering benchmark.
- Capture final offscreen screenshots and perform native-Windows manual review.
- Inspect paint profiles for expanded/collapsed plots and live overlay.
- Update the milestone handoff, divergence log, `docs/next_steps.md`, findings,
  and indexes with measured results and remaining scientific work.
- Remove compatibility aliases only if no tests or callers require them.

Acceptance: user approves visual/interaction parity and no performance or
scientific regression is observed.

## Test matrix carried across every chunk

- Empty app, parent asset, and child isolate asset.
- One-frame, short-window, frame-zero Change energy, and mid-asset windows.
- Intensity and Change energy, Off and per-frame z-score.
- Compute, replacement compute, cancel, asset/grid/window/channel change, close.
- Play, pause, seek, scrub, rapid seek, resize, splitter move, tab hide/show.
- Grid and channel overlay independently visible/hidden.
- Progressive preview, final publication, invalid temporal frame, exact zero,
  and uncomputed tail.
- All plots collapsed, selected plots expanded, every plot expanded.
- 1200×800 and 1600×980 offscreen; native Windows at ordinary DPI and one
  non-default scaling setting if available.

## Architecture invariants

1. Visibility decides what is drawn, never what is scientifically computed.
2. Widgets do not own the only copy of scientific or detection state.
3. GUI lifecycle tokens never enter headless scientific identity.
4. Display-sized decoded frames are not scientific evidence.
5. There remains one Isolate media/playback owner and one selected-channel
   worker/newest-pending envelope.
6. A plot can retain presentation caches, not a duplicate full scientific
   result.
7. Unsupported UI is inert and visibly unavailable, never plausible fake data.
8. Preview and final publication use the same formulas and result allocation.

## Context-reset checkpoint template

After each work chunk, append:

```text
Checkpoint YYYY-MM-DD HH:MM TZ
Completed chunk:
Accepted by user:
Files changed:
Tests/benchmarks:
Screenshots:
Known deviations:
Unfinished work:
Next exact action:
Do not start:
```

## Status table

| Chunk | State | User accepted | Last evidence |
|---|---|---|---|
| 0 Baseline | Complete | No | Matched screenshots, inventories, integrated test, and current-panel benchmark |
| 1 Instruments | Planned | No | — |
| 2 Layout | Planned | No | — |
| 3 Current channel | Planned | No | — |
| 4 Navigator/interactions | Planned | No | — |
| 5 Future shells | Planned | No | — |
| 6 Integrated validation | Planned | No | — |

## Next exact action

Ask the user to review and accept the Chunk 0 baseline in
`docs/plans/isolate-ui-baseline.md`. Only after explicit acceptance, begin
Chunk 1 with standalone SIEVE-native instrument primitives. Do not change the
`IsolateTab` layout during Chunk 1.

Checkpoint 2026-07-23 22:23 -07:00
Completed chunk: Chunk 0 — Baseline and contract inventory.
Accepted by user: No; awaiting review.
Files changed: preliminary shell removed; integrated behavior test extended; capture and benchmark harnesses added; matched screenshot, inventory, benchmark, and baseline documentation artifacts added; plan and next-steps checkpoint updated.
Tests/benchmarks: focused integrated GUI test passed; full offscreen suite passed (174 tests in 37.65 s); 12-sample current-panel benchmark recorded.
Screenshots: oracle and SIEVE, empty and computed, at exact 1600×980 and 1200×800 canvases. Oracle computed canvases record/crop its larger minimum-resolved surface.
Known deviations: oracle computed presentation uses deterministic synthetic channel arrays; SIEVE uses a real 64-frame Change-energy result. Oracle cannot naturally fit its computed surface inside 1600 px because its minimum resolves to 1885 px.
Unfinished work: user review/acceptance; native Windows visual validation remains a later integrated gate.
Next exact action: review Chunk 0 artifacts and, only if accepted, begin standalone Chunk 1 primitives.
Do not start: Chunk 1 or any scientific stage before explicit user acceptance.
