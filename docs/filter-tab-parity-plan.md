# Filter tab: v1-parity plan

The plan for bringing the rewrite to parity with v1's "Preprocessing
(live)" tab, per the target mockup (`videos-testing/UI mock up copy.png`)
as amended by discussion and then by four clickable interaction mockups
(2026.07.26). Produced in stages — goals, v1/v2 exploration, work items,
then a mockup cycle — and consolidated after the cycle so this document
describes one current design, not its drafts. The mockup folders
(`mockups/insertion`, `mockups/graphs`, `mockups/seeker`, `mockups/tab`)
are the runnable form of the interaction contracts and are deleted as the
real widgets land; everything load-bearing from them is restated here.

---

## 1. Goals and non-goals

### Parity goals (the nine)

1. Set downsampling.
2. Set block size.
3. Normalize (mode selection).
4. Reset button.
5. Morlet wavelet scalogram with draggable band handles.
6. Change energy Jtt signal.
7. LK optical flow signal (v1 "tensor speed").
8. Windowed # blocks in band graph (green detection shading, threshold
   handle).
9. Detection window D slider.

### Non-goals (deliberate)

- No "Process whole video" button, no "Save detections" button.
- No Length control on this tab (it lives with the cross-tab seeker).
- v1's other channels (appearance energy, intensity, shear strain rate,
  divergence, vorticity) do not come over.
- The two signals are the only two; a third is a future registry entry,
  not a widget change.
- Anything else in v1 comes over only if it does not violate the goals of
  the rewrite (structure enforced by tooling, editability).

The milestone's purpose is a side-by-side comparison against v1 — what the
rewrite gained and lost — recorded as a finding (item 9).

---

## 2. The target design

### Layout

- **Left column:** the block-heat video panel — the frame with the block
  grid over it, fill = band power at the playhead, outline = block is in
  the value band, click a block to solo its trace in the signal graph. On
  this tab the picture's job is to say where the signal is. Under it, the
  green **windowed # blocks in band** graph; under that, the **detection
  window D** row (slider, frames + seconds label, centered toggle,
  detections summary).
- **Right column:** the **operation stack** — the live chain as a vertical
  list of step cards under fixed stage headers (SPATIAL PREP → SIGNAL
  EXTRACTION → TEMPORAL FILTER → DETECTION, each header carrying an
  `in → out` type chip). Reset sits above the stack.
- **Bottom:** the cross-tab seeker (§ Seeker below), which owns Length.

### The stack

Every step's parameters live in its card; every graph lives in the card of
the step that produces it:

| step | card body |
|---|---|
| rescale | Downsample spinbox (float scale, v1 semantics) |
| normalize | mode combo (`off` / `zscore`) |
| block signal | Block spinbox (`0 = auto (N)`) + the **quick-switch**: Jtt \| LK as two checkable buttons that swap the step in place, one click, bands kept |
| morlet band | the scalogram and the band-power density graph, embedded |
| windowed count | threshold/D caption; its graph is *promoted* under the video per the target, and the card says so |

Captions restate current parameter values so a collapsed reading of the
stack is complete. Hovering any card shows `swap` and `x` (removal is
always visible). Chain validity is derived by one walk — ok / conflict at
the first type mismatch / unreached after — and **no reachable step, no
graph**: break the chain and the embedded graphs disappear, the count plot
reports "no reachable detection step", the summary says "chain incomplete
— see the stack". Conflicted cards get a red edge, the
expects/receiving message, and inline Swap/Remove (permit-then-repair).
Conflicts can arise from removals or loaded files only — insertion cannot
create them (§ Wizard). Reset is parameters-not-structure: knobs, bands,
and D reset; the chain the user built stays.

**The chain is a hybrid, and the stack is one presentation over it.** The
spatial-prep and extraction steps are real pipeline nodes (a `Pipeline`
value the tab constructs from the stack and hands to the preview runner).
The temporal-filter and detection steps are tab-side derivation state (the
Morlet CWT needs the whole series and stays outside the per-frame kernel
contract for this milestone). The stack model owns per-step *kinds*
(image → image, image → per-block series, series → series,
series → events) for grading, grouping, and the wizard's guardrails —
these kinds are a chain-model concept, **not** derivable from
`FilterSpec.accepts/emits`: `ArraySpec` cannot distinguish an image frame
from a `(ny, nx)` block-series frame (both GRAY float32 arrays — see
`docs/findings/2026.07.25-the-filter-contract-cannot-type-vision.md`).
Pushing the distinction into the type system becomes necessary only when
the temporal filter becomes a real windowed pipeline node (deferred, § 7).

### The wizard (insert and configure)

Seams between cards are invisible until hovered; a hovered seam grows a
hairline and a plus. Clicking it — or a card's `swap` — opens a
near-full-window inset helper that is the *configuration surface for a
provisional step*, not a picker with a description:

- **Left:** the equivalents for this seam — every operation whose input
  kind matches, grouped by stage with the seam's own stage first, plus
  search. Hover or click swaps the provisional step in place: comparing
  candidates and choosing one are the same gesture.
- **Center:** the current video, live-edited by the provisional chain;
  the band-power graph below it; the green detection graph with its D row
  below that — all fully interactive (handles drag, detections update),
  because a candidate is judged by what it does to the green.
- **Right:** the selected step's own settings — the same widgets its card
  owns — over its guidance, built from the filter's `.md` (`summary` → row
  blurb; "When to use it" / "What it does not do" → the pane).
- The provisional step sits in the actual chain as a dashed card. **Add**
  commits; **Cancel**/Esc restores everything exactly.
- **The wizard cannot break the chain:** kind-breakers and duplicates are
  listed but disabled with the reason ("breaks below" / "in chain").

### Detector semantics (deviations from v1, confirmed by feel)

- **Unset count threshold = disarmed.** Nothing is green and the footer
  says so. (v1's unset-means-unbounded painted a fresh tab as one giant
  detection.) Frequency/value bands still default wide open — they shape a
  signal, they don't claim an event.
- The count threshold is stored as a **fraction of region blocks** and
  rendered in counts — this deletes v1's `rescale_count_band`
  re-denomination machinery (a 13× foot-gun) rather than porting it.
- Every band drag is two-tier: continuous `changed` = cheap re-derive
  (re-sum cached cube, re-count, repaint), `committed` on release = the
  hook for anything expensive. Threshold / D / centered changes are
  instant pure recomputes; only upstream parameter changes re-run
  extraction.
- "Visibility decides what is drawn, never what is computed" (v1's rule,
  kept).

### Plot contracts (QPainter; settled — drop pyqtgraph from the gui extra)

- One drag gesture, two meanings: within 8 px of a handle moves the
  handle; anywhere else scrubs the shared playhead. No modes.
- Handles read out in the right margin (dot + value); dragging past the
  plot edge = unbounded (`inf`), except frequency handles, which clamp to
  the bank's edges.
- **Scalogram:** log-frequency axis, per-column max reduction, COI alpha
  fade (e-folding ≈ 1.369/f s); the title carries the *snapped* bank band
  even when handles sit between rows — the title tells the truth the
  transform uses.
- **Signal graph:** a per-frame value histogram over all blocks (log1p
  value axis), not a mean line — the detector counts blocks, so the user
  tunes against the population the count comes from. Solo (from the block
  heat) answers the opposite question.
- **Count graph:** windowed count line, gate spans floored to 1 px so a
  single-frame detection survives any zoom, one draggable count threshold.
- Green is a status color: detection only, never a data series. One
  sequential ramp per magnitude surface (warm = scalogram, cyan =
  density). Text in text colors, grids recessive.

### Seeker (cross-tab, owns Length)

- Scrub semantics unchanged from the existing `timeline_bar.py`: press =
  seek (commit), move = scrub (guess), release = commit.
- The working window is a bracket manipulated directly — edge handles
  resize, the header band moves it whole, minimum 1 s — and the Length
  spinbox is the same value in lockstep. Window drags are two-tier like
  band drags.
- Detection ticks floored to 1 px; `|<` / `>|` jump to previous/next
  detection.
- **Coverage is a first-class encoding:** signal bars tinted
  examined-current-settings / examined-other-settings / never-examined,
  restated in words in the hover bubble. (v1's navigator honesty.)
- Graphs cover the working window; the seeker covers the asset; one
  playhead mapped through the window connects them.
- Two variants remain user's choice: `lanes` (one strip, compact) vs
  `split` (separate status lane) — `mockups/seeker`.

---

## 3. What v1 actually does (semantics to preserve)

v1 = `antscihub-optical-flow-detector` (PyQt6). The tab is
`gui/tab_live_preprocess.py` → `LiveScalogramSurface` (~2 700 lines) →
`ScalogramExplorer` (~2 500 lines); math in `core/wavelet.py`,
`core/detection.py`, `core/tensor_channels.py`, `core/structure_tensor.py`.

### Spatial controls

- **Downsample** is a spatial linear scale factor (0.05–1.0, step 0.05,
  default 1.0): `width/height = round(src × scale)`, `cv2.resize`
  INTER_AREA, no-op at ≥ 1.0. Never touches frame rate. 0.250 = 25 %
  linear, 6.25 % pixels.
- **Block** is working pixels per reduction cell, `0 = auto` meaning
  `max(1, round(64 source px × scale))` — the grid is held fixed in
  *source* pixels so downsample changes compute cost, not localization.
  Spinner shows `auto (N)`. Block size sets the `(ny, nx)` grid, cube
  memory, and the count-threshold denominator.
- **Normalize**: `off | zscore | clahe`. zscore is a fused affine to
  mean ≈ 128, sd ≈ 32 from global per-frame stats. clahe has a known
  replicate-edge artifact and is dropped (optional later).
- v1's Reset restored a pre-sidecar snapshot plus cleared all three bands
  and D; without sidecar persistence in scope, ours is simply
  tab-defaults (see § 2 detector semantics).

### Per-block signals

- Both signals come from structure-tensor products of consecutive
  preprocessed frames: `it = g − gp`, `iy, ix = np.gradient(g)`, products
  Gaussian-blurred with **σ = 2.0** (the blur *is* the tensor window),
  then block-mean reduced. Output `(T, ny, nx)`, flattened `(T, B)` per
  scope.
- **Change energy Jtt** = blurred `⟨I_t²⟩` — one product, one blur, the
  cheapest channel (v1 always streams it).
- **LK optical flow ("tensor speed")** = per-pixel 2×2 Lucas–Kanade solve
  `[[Jxx,Jxy],[Jxy,Jyy]] v = −[Jxt,Jyt]`, `|det| ≤ 1e-6 ⇒ v = 0`
  (aperture-degenerate blocks honestly zero), speed `hypot(u,v) × fps`
  in px/s, *then* block-reduced — the solve precedes reduction so the
  aperture problem is not coupled to block size. Needs all 6 products
  (~4× Jtt's cost).

### The temporal filter

- Torrence–Compo Morlet, `W0 = 6.0`, FFT-based, complex64; scales
  `(W0 + √(2+W0²))/(4π f)`; zero-pad to `next_fast_len` past the COI;
  power `|w|²` float32.
- Frequency bank: `geomspace(0.5, min(25, 0.45·fps), 24)` — log-spaced,
  capped below Nyquist.
- Two uses, both needed: pooled replicate-mean series → `(F, T)` scalogram
  for display (~8 ms at T = 30k — near-live); per-block `(F, T, B)` cube
  whose band sum feeds the signal graph and detection (expensive; built
  off-thread, on demand, LRU-cached — v1 budgeted 6 GiB).
- COI handling matters twice: display fades outside the cone; any chunked
  evaluation must widen by COI (v1 used 2.5 × 2 × COI) or seams ring.
- `band_indices` snaps an empty span to the nearest single scale.
- Morlet is the first of a *class* of temporal filters: the seam is
  series `(T, B)` + params → filtered magnitude; the band UI is generic,
  the scalogram display is Morlet-specific.

### The detection chain

Pure functions, shared verbatim between v1's live and whole-video paths (a
property to keep):

```
band power (T,B) → inband_count(m, v_lo, v_hi) → count (T,)
  → windowed_mean(count, D, centered) → detect_gate(windowed, c_lo, c_hi)
  → gate (T,) ∈ {0,1}
```

- "# blocks in band" = blocks whose *band-power value* lies inside the
  value band; the frequency band is applied upstream by summation. Two
  distinct bands, easy to conflate.
- `windowed_mean` is a prefix-sum mean over D frames, centered or
  trailing, truncated honestly at clip edges (divide by true window
  length). **D is in frames**, default ≈ 1 s, label shows frames and
  seconds.

### v1 coupling that must NOT come over

1. God objects (two ~2 500-line widget classes owning workers, caches,
   cost models, persistence, and math orchestration).
2. Detection state living in plot-widget paint state, read back via
   `detection_params()`, with a `None`/±∞/float three-valued encoding
   every consumer re-handles. Here the detector is a value; plots render
   it.
3. Rebuild-the-widget-as-state-migration (order-dependent view-state
   serialization on widgets).
4. Nine hand-tuned QTimer debounces with cross-cancellation;
   token/generation counters as a substitute for cancellable requests.
   v2 has `gui/coalescer.py` and revision-stamped renders for this.
5. Six hand-rolled QThread subclasses.
6. Parameter resolution re-derived at 3+ call sites (one home only).
7. Whole-atlas extraction paid when scoped to one region (~13× waste) —
   v2's per-replicate ROI at the executor root removes this by
   construction.

---

## 4. v2 constraints that shape the work

- **Layering (`.importlinter`):** gui → bench → pipeline → filters →
  decode|backend → core. cv2 is legal only in `filters/` and
  `decode/reader.py`, so Jtt/LK extraction must be pipeline filters.
  numpy/scipy math is legal in `core/` — the home for the ported
  wavelet/detection pure functions.
- **The kernel contract** (per-frame, one-in/one-out, index-preserving;
  WINDOWED/multi-input refused by the executor) fits extraction — a
  stateful STREAMING kernel with the previous frame as state,
  `warmup_frames = 1`, emitting `(ny, nx)` GRAY float32 frames — but not
  the Morlet CWT, which stays tab-side this milestone (§ 2, hybrid chain).
  Stateful ⇒ uncacheable (the `background_ema` caveat); acceptable because
  extraction at working resolution is ~realtime.
- **Downsample mismatch:** v2's `downsample` filter takes integer factor
  (2–64); parity needs v1's float linear scale. New `rescale` filter or a
  params-v2 — decide in item 2.
- **Knob state lives in the tab.** The stack constructs a `Pipeline` value
  from its cards and hands it to `PreviewRunner.request_render` — no
  document writes, no undo stack, no parameter-panel machinery
  (deliberately deferred, § 7). Content-derived `node_key`s give cache
  reuse across knob wiggles for free.
- **Render plumbing exists:** `PreviewRunner` (revision-stamped,
  latest-wins, tested, currently drawn by nothing) needs per-frame node
  outputs exposed to a collector; `PreviewSession.render_frame` (the
  100 ms single-frame path) exists unused and becomes the wizard's video
  preview.
- **House conventions:** filter = module + `.md`, self-registered,
  discovered namelessly (test-enforced); tests pin the load-bearing claim,
  2–3 per item; TODO items < 150k context; completion is atomic into
  `docs/completed-todo/`; measurements to `docs/findings/`; latency-budget
  misses are defects.

### Carry / adapt / drop (v1 → v2)

| v1 thing | verdict | reason |
|---|---|---|
| Downsample = float linear scale, INTER_AREA | carry | the parity semantic |
| Block = working px, 0 = auto from 64 source px | carry | grid fixed in source px is the right invariant |
| Normalize zscore (fused affine, mean 128 sd 32) + off | carry | parity |
| Normalize clahe | drop (optional later) | known edge artifact; not in the nine |
| Morlet W0=6, geomspace bank, COI fade + widen | carry | the transform is the feature |
| Pooled scalogram for display + per-block cube for detection | carry | two uses, both needed |
| Jtt/LK extraction semantics incl. aperture honesty | carry | parity |
| Detection chain as shared pure functions | carry | the best part of v1 |
| Count band in raw counts + re-denomination | adapt | store as fraction of region blocks |
| Unset detector bands = unbounded | adapt | unset count threshold = disarmed |
| Density-heatmap signal rendering | adapt | keep the histogram idea; population view |
| Per-(region, channel) band memory | open | see § 8, band memory across signal swap |
| Drag = cheap, commit = expensive | carry | as coalescer-mediated tiers |
| "Visibility decides drawing, never computing" | carry | stated rule |
| Collapsible 7-channel plot stack | drop | two signals, stack-hosted graphs |
| God objects, widget-state truth, debounce zoo, thread zoo, atlas waste | drop | the reasons the rewrite exists |
| Sidecar persistence, whole-video track, process/save, ROI clips, window-start, all-channels | drop | out of scope |

---

## 5. What the mockup cycle taught (necessary, and easy to miss)

1. **A non-throwing chain grade is required.** `Dag.build` raises on the
   first bad edge; the stack needs per-step ok/conflict/unreached for
   chains that removal or a loaded file broke. It operates on the chain
   model's *kinds*, not on `Dag` — because of the hybrid chain and because
   `ArraySpec` cannot express the image-vs-block-series distinction
   (§ 2). GUI-side (chain model), pure, tested directly.
2. **Do not add stage metadata to `FilterSpec` for this milestone.** The
   chain model annotates its own steps with kinds; the pipeline prefix is
   short and fully known to the tab. The type-system version of this
   question comes due when the temporal filter becomes a real windowed
   node (§ 7) — that is when `ArraySpec` (or a successor) must learn the
   difference between image space and block space, per the
   cannot-type-vision finding.
3. **Provisional preview is nearly free by construction.** The wizard
   renders a *different* `Pipeline` value without touching anything —
   `request_render(pipeline, …)` already takes the pipeline as an
   argument, and content-derived keys share every cache entry upstream of
   the seam. The strongest architectural validation the mockups produced;
   lean on it, never copy state. The tab-side suffix (Morlet + detection)
   re-derives cheaply from the cached cube.
4. **Hover-preview must ride the coalescer tier.** The mockup recomputes
   synchronously against precomputed cubes; the real thing schedules a
   latest-wins provisional render per hover and an expensive tier on
   selection/commit — same two-tier discipline as band drags.
5. **Coverage must be recorded as render events, not derived from store
   contents.** "Examined under settings S" keyed by S's node keys, logged
   at render time — store presence conflates examination history with
   cache retention, and eviction would silently un-examine footage. This
   log is also the trigger the `docs/LATER.md` detection-lanes entry has
   been waiting on.
6. **Do not reparent shared Qt widgets between hosts.** The mockups moved
   single widget instances (density plot into the wizard, D row out of
   the left column) and hit PySide parent-death semantics repeatedly — a
   parentless widget dies with its Python reference and takes its
   children with it. The real tab builds thin views over shared state
   (the house pattern anyway); the wizard gets its *own* plot instances
   bound to the same detector/chain state.
7. **Guidance `.md`s are user-facing UI content.** The wizard pane and
   candidate blurbs are built from `summary`, "When to use it", and "What
   it does not do". Write items 2–3's docs knowing they will be read in
   the wizard, not only in the repo; the wizard item needs a small
   section parser.
8. **Duplicate blocking needs a per-filter rule.** The mockup disables
   any op already in the chain — right for the parity set, wrong in
   general (a second smoothing pass can be legitimate). Effectively a
   `repeatable` judgment; default to blocking until a real chain needs
   repetition.

---

## 6. Work items

Ordered bottom-up along the layer stack; each sized to TODO.md rule 3 and
written to be liftable into `docs/TODO.md`. Tests pin the load-bearing
claim (rule 7).

### Item 1 — Wavelet and detection math (`core/`)

`src/sieve/core/wavelet.py`, `src/sieve/core/detection.py` + unit/property
tests. Port the v1 semantics of § 3 as Qt-free, cv2-free pure functions:
`morlet_scales`, `morlet_power` (`(T,)→(F,T)` and `(T,B)→(F,T,B)`),
`default_freqs`, `coi_efolding_s` / `coi_edge_samples`, `band_indices`
(empty span snaps to one scale), `inband_count`, `windowed_mean`
(prefix-sum, centered/trailing, honest edges), `detect_gate`. Count
threshold API takes a fraction of B. Adds scipy to core deps — confirm
import-linter stays green.

Claims: a pure tone concentrates power in the nearest scale row;
`windowed_mean` at clip edges divides by true window length; `band_indices`
on an empty span returns exactly one scale.

### Item 2 — Preprocessing filters (`filters/`)

`rescale.py` + `.md` (or params-v2 of `downsample` — one-paragraph
decision in the module docstring), `normalize.py` + `.md`, tests.
`rescale`: float scale ∈ [0.05, 1.0], INTER_AREA, no-op at 1.0,
`frame_bytes_ratio = scale²`. `normalize`: `off | zscore` (fused affine to
mean ≈ 128, sd ≈ 32; clahe named in "what it does not do"). Write the
`.md`s for the wizard's eyes (learning 7).

Claims: rescale at 0.25 yields `round(w·0.25)` preserving dtype; zscore of
a nonconstant frame hits mean ≈ 128 / sd ≈ 32; a constant frame does not
divide by zero.

### Item 3 — Block-signal extraction filter (`filters/`)

`block_signal.py` + `.md`, tests. One filter, `signal ∈ {change_energy,
flow_speed}`, `block: int` with `0 = auto` (`max(1, round(64 · scale))`;
scale and fps enter as explicit params so the kernel stays pure and
resolution lives in exactly one exported function). `@stateful_kernel`,
state = previous frame, `warmup_frames = 1`, emits GRAY float32 `(ny, nx)`
frames, index-preserving. Math per § 3 (σ = 2.0 blur, per-pixel LK solve
with `|det| ≤ 1e-6 → 0` before reduction).

Claims: a static input yields exactly zero for both signals from frame 1;
a uniform translation of textured input yields flow_speed ≈ speed·fps and
change_energy > 0; an aperture-degenerate input yields flow_speed exactly
0, not noise.

### Item 4 — Per-frame delivery and the single-frame path (`pipeline/` + `gui/`)

Expose the existing `Consumer` hook through `request_render` so a caller
receives per-frame node outputs on the render thread; add a Qt-free
`SeriesCollector` assembling `(T, ny, nx)` float32 for the current
revision, discarding superseded revisions; surface
`PreviewSession.render_frame` through the runner for single-frame renders
(the wizard's video preview — learning 4's cheap tier).

Claims: a superseded render never contributes rows to the served series;
the collected frame axis aligns with `plan.span` (lead-in excluded);
per-frame delivery does not regress `slider_to_preview`.

### Item 5 — Plot widgets (`gui/`)

Shared QPainter base (series/heatmap painting, log/log1p axes, two band
handles with the § 2 gesture rules, drag/commit signals, gate-span
underpaint floored to 1 px); scalogram plot (log-f, per-column max, COI
fade, snapped-band title); density plot (per-frame block histogram, solo
trace); count plot; **block-heat panel** (grid fill/outline/solo/hover
readout). Widgets own no detector state: setters in, drags out
(`TimelineStrip` is the template). This item also removes pyqtgraph and
napari from the gui extra if still unused.

Claims: dragging past the plot edge emits an unbounded band (frequency
clamps instead); a 1-frame gate run paints ≥ 1 px at any width; a drag
starting 9 px from a handle scrubs instead of grabbing; solo state lives
in the state model, not the widget.

### Item 6 — Chain model and the stack UI (`gui/`)

The Qt-free chain/detector model: ordered steps where the prefix maps to
`Pipeline` nodes and the temporal/detection suffix maps to detector state
(bands, D, centered, solo, signal choice); per-step kinds; the
non-throwing `grade()` (learning 1); one pure recompute gluing item 1's
functions; captions. The stack widgets: step cards with embedded parameter
rows and graphs, stage headers with type chips, hover `swap`/`x`, conflict
cards with inline repair, seam affordances (no-op until item 7). Wire to
the document/player/runner per the house pattern.

Claims: `grade()` statuses for a valid chain, a mid-chain removal, and a
loaded-broken chain; removing the temporal step hides its graphs and the
count plot reports why; a knob change while a render is in flight yields
exactly one final recompute with the last value; Reset restores documented
defaults, clears bands, disarms, and does not touch chain structure.

### Item 7 — The wizard (`gui/`)

Per § 2: provisional insertion as a second `Pipeline` value through the
existing runner (learning 3), candidates from the chain model's kinds with
disable rules (breaks-below, duplicates — learning 8's default), suggested
stage first, live video via item 4's single-frame path, **its own** plot
instances bound to shared state (learning 6), settings hosting, `.md`
section parsing for the guidance pane (learning 7), Add/Cancel/Esc.
Hover-preview through the coalescer tier (learning 4).

Claims: Cancel restores the exact prior state (chain, detector, view); a
provisional render reuses every cache entry upstream of the seam (assert
on store hits); disabled candidates cannot be committed by any input path.

### Item 8 — Seeker upgrades (`gui/` + wherever the coverage log lands)

Coverage as a render-event log keyed by settings identity (learning 5),
coverage tint + hover wording, detection ticks + prev/next jumps, window
bracket + Length lockstep, playhead mapping through the window,
lanes-vs-split decision.

Claims: a frame rendered under settings A then revisited under B reads
"other settings"; evicting cache entries does not change coverage; a
1-frame detection paints at any width; bracket and spinbox can never
disagree.

### Item 9 — Parity comparison finding (`docs/findings/`)

Run v1 and v2 on `videos-testing/stab_GX010050c2_02_18_26.MP4` with
matched settings (scale 0.25, block auto, zscore, same band, same D):
numeric agreement of count/gate series where comparable, interaction
latencies against the budget table, throughput, and a gained/lost list.
Anything lost that matters becomes a LATER.md entry with its trigger.

### Order and gating

1 → (2, 3 in either order) → 4 → 5 ∥ 6 → 7 → 8 → 9. Items 1–3 are
pure/headless. Item 6 does not require item 5 (cards can hold placeholder
bodies); item 7 requires both. Item 8 is independent of 5–7 except for
detection spans to display.

---

## 7. Explicitly deferred (with triggers, per LATER.md discipline)

- Persisting tab params into the project artifact + undoable param edits —
  trigger: the parameter-panel item (`docs/LATER.md:366-399`) or the first
  complaint that tuning is lost across sessions.
- Windowed/multi-input kernel protocol (Morlet as a real pipeline node) —
  trigger in `docs/LATER.md:96-135`. **When it fires, the image-vs-blocks
  kind distinction must move into the type system** (cannot-type-vision
  finding); the chain model's kinds are the interim.
- clahe normalize; the five dropped channels; whole-video processing;
  saved detections; detection lanes on the cross-tab timeline
  (`docs/LATER.md:158` — unblocked by item 8's coverage log).
- The color-gate channel (click-to-include/exclude on a paused frame,
  `mockups/graphs --variant color`) — a stretch goal whose integration
  contract is pinned (one more per-block channel: fraction of the block's
  pixels in gate); trigger: the first experiment that needs color-marked
  animals separated.

---

## 8. Open decisions (settled at item time, none blocking)

- **Item 2:** new `rescale` filter vs params-v2 of `downsample`.
- **Item 5:** colormap stops — v1's ramps vs restyle (the mockup palettes
  were explicitly not the decision).
- **Item 6:** `detector_state.py` vs the SCAFFOLD-reserved `gui/state.py`;
  whether knob-settle and band-drag interactions get ARCHITECTURE.md
  budget rows (recommended: yes, here).
- **Item 7:** band memory across the signal quick-switch — the mockups
  keep bands and `mockups/tab --shot lk` shows the consequence (a
  Jtt-tuned threshold silently reinterpreted in LK units); v1 remembered
  value bands per (region, channel). Per-signal memory is probably right.
  Also: the `repeatable` rule (learning 8), and whether the wizard hosts
  the scalogram too (currently video + band power + count).
- **Item 8:** `lanes` vs `split`; seeker scrub outside the working
  window — clamp (mocked) vs move-the-window.
- Whether the superseded `mockups/filter_tab.py` (the operations-list
  concept) is deleted now or when item 6 lands.
