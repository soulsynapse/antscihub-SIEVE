# Filter tab: v1-parity plan

Target: the modified-v1 mockup at `videos-testing/UI mock up copy.png`, amended
by discussion (2026.07.26). This document is built in three stages and the
earlier stages are left standing so the reasoning is auditable:

1. **Checklist + goal chunks** — what the plan has to cover, before reading code.
2. **Running considerations** — what the v1 source and the current v2 state
   actually say, per chunk.
3. **Formal plan** — ordered work items, sized to TODO.md rule 3.

---

## Stage 1a — checklist for writing this plan

- [x] State the target layout in words, with the amendments that override the
      flattened PNG (green blocks-in-detection graph under the video; detection
      window slider below it; Length lives with the cross-tab player, not here).
- [x] Enumerate the nine parity goals and the explicit non-goals.
- [x] Chunk the goals so each chunk is one coherent piece of design.
- [x] Read the v1 preprocessing tab source (`antscihub-optical-flow-detector`)
      and record, per chunk: exact semantics (units, ranges, defaults, what
      recomputes on what), and what in the v1 implementation must *not* be
      carried over.
- [x] Read the current v2 state (`gui/`, `pipeline/`, `core/`, `filters/`) and
      record, per chunk: what already exists, which conventions constrain the
      design (filter contract, cache key, coalescer, import-linter layering,
      guardrails), and where each new piece belongs.
- [x] Reconcile: for every consideration, decide carry / adapt / drop, with a
      one-line reason.
- [x] Formalize into ordered work items, each with file targets, the
      load-bearing claim its tests pin (TODO.md rule 7), and a scope under one
      context window (rule 3).
- [x] Sanity-check the plan against the mockup image one final time.

## Stage 1b — target, goals, non-goals

### Target layout (authoritative wording)

- **Left column:** video view. Directly under it, the green **windowed # blocks
  in band** graph ("blocks in detection", green fill = positive detection, red
  draggable threshold line). Under that, the **detection window D** slider.
- **Right column, top:** one control row — **Downsample**, **Block**,
  **Normalize** (mode dropdown, zscore first), and a **Reset** button.
  **Length is not here**; it belongs with the cross-tab player at the bottom.
- **Right column, below the controls:** exactly two graphs.
  1. **The temporal-filter view: Morlet scalogram** with a draggable frequency
     band (two handles). Morlet is the first member of a *class* of temporal
     filters — the UI slot is "the temporal filter", not "the Morlet widget".
  2. **The filter-output signal**: the per-block signal that feeds the temporal
     filter, selectable between exactly two options — **change energy (Jtt)**
     (default) and **LK optical flow** (labelled "tensor speed" in the v1
     screenshot). No other channels.
- **Bottom:** the existing cross-tab player/timeline strip (already in v2).

### Parity goals (the nine)

1. Set downsampling.
2. Set block size.
3. Normalize (mode selection).
4. Reset button.
5. Morlet wavelet scalogram with draggable band handles.
6. Change energy Jtt signal.
7. LK optical flow signal (v1 "tensor speed").
8. Windowed # blocks in band graph (green detection shading, threshold handle).
9. Detection window D slider.

### Non-goals (deliberate)

- No "Process whole video" button, no "Save detections" button.
- No Length control on this tab.
- v1's other channels (appearance energy, intensity, shear strain rate,
  divergence, vorticity) do not come over.
- The pipeline graph stays invisible to the user on this tab for now. The
  point of this milestone is a side-by-side comparison against v1 — what the
  rewrite gained and lost — not the graph-editing UI.
- Anything else in v1 comes over only if it does not violate the goals of the
  rewrite (structure enforced by tooling, editability).

## Stage 1c — goals chunked

- **Chunk A — spatial preprocessing controls** (goals 1, 2, 3, 4): downsample,
  block size, normalize, reset. These parameterize how frames become per-block
  signals; they are pipeline parameters, not view state.
- **Chunk B — per-block signal extraction** (goals 6, 7): Jtt change energy and
  LK optical flow, computed per block over time. These produce the 1-D-per-block
  time series everything downstream consumes.
- **Chunk C — the temporal filter** (goal 5): Morlet CWT over the selected
  signal, scalogram rendering, draggable frequency-band handles. Designed as
  the first of a class of temporal filters.
- **Chunk D — detection layer** (goals 8, 9): per-block in-band test →
  windowed count over D → threshold → detection intervals; the green graph and
  the D slider.
- **Chunk E — layout & interaction** : the tab itself — placement per the
  target layout, live recomputation behavior, what invalidates what, and how
  this coexists with the existing replicate tab and cross-tab player.

---

## Stage 2 — running considerations (from v1 source and v2 state)

v1 = `antscihub-optical-flow-detector` (PyQt6). File references below are into
that repo. The tab is `gui/tab_live_preprocess.py` →
`gui/explorers/live_scalogram_surface.py` (`LiveScalogramSurface`, ~2 700
lines) → `gui/explorers/scalogram_explorer.py` (`ScalogramExplorer`, ~2 500
lines); math in `core/wavelet.py`, `core/detection.py`,
`core/tensor_channels.py`, `core/structure_tensor.py`.

### Chunk A — spatial preprocessing controls (v1 semantics to preserve)

- **Downsample** is a *spatial linear scale factor* (0.05–1.0, step 0.05,
  default 1.0). `width/height = round(src * scale)`, `cv2.resize INTER_AREA`,
  no-op at ≥ 1.0. It never touches frame rate. 0.250 = 25 % linear, 6.25 %
  pixels.
- **Block** is *working pixels per reduction cell*, with `0 = auto` meaning
  `max(1, round(64 source px × scale))` — the grid is held fixed in **source**
  pixels so downsample changes compute cost, not localization. The spinner
  shows `auto (N)`. Block size sets the `(ny, nx)` grid, cube memory, and the
  denominator of the block-count threshold.
- **Normalize**: `off | zscore | clahe`, per-frame pixel op. zscore is a fused
  affine to mean ≈ 128, sd ≈ 32 from global per-frame stats. clahe
  (clipLimit 2.0, 8×8 tiles) has a known replicate-edge artifact in v1.
  Carrying zscore (and off) suffices for parity; clahe is optional.
- **Reset** in v1 restores a snapshot of the strip taken *before* the
  remembered sidecar was applied, and additionally clears all three detection
  bands (frequency / value / count) to unset, resets D to ~1 s, keeps the
  selected channel and replicate. Decision: our Reset restores tab defaults
  (downsample, block, normalize, bands, D) — there is no sidecar persistence
  in scope, so the subtlety disappears.
- v1 debounces knob changes (500 ms downsample, 250 ms block) before
  replanning a full pass. v2 already owns this problem in `gui/coalescer.py` —
  do not reintroduce ad-hoc QTimers.

### Chunk B — per-block signals (v1 semantics to preserve)

- Both signals come from structure-tensor products of consecutive preprocessed
  frames: `it = g − gp`, `iy, ix = np.gradient(g)`, products Gaussian-blurred
  with **σ = 2.0** (the blur *is* the tensor window), then block-mean reduced.
- **Change energy Jtt** = blurred `⟨I_t²⟩` — one product, one blur; the
  cheapest channel, and the one v1 always streams.
- **LK optical flow ("tensor speed")** = per-pixel 2×2 Lucas–Kanade solve
  `[[Jxx,Jxy],[Jxy,Jyy]] v = −[Jxt,Jyt]`, `|det| ≤ 1e-6 ⇒ v = 0`, speed
  `hypot(u,v) × fps` (px/s), *then* block-reduced. The solve is per-pixel
  before reduction, deliberately, so the aperture problem is not coupled to
  block size. Requires all 6 products (~4× the cost of Jtt).
- Output shape per channel: `(T, ny, nx)`, flattened to `(T, B)` per scope.
- v1 renders these as a time × value *density heatmap* (per-column value
  histogram over blocks, log1p value axis, hatching for unexamined spans, red
  value-band handles). Note for the plan: in the target UI this graph slot is
  "the signal that comes out of the temporal filter" — i.e. what v1 shows here
  is *band power after the Morlet transform* (`cube[i:j].sum(axis=0)`), not
  the raw signal. Parity means: signal → Morlet → per-block band power → this
  graph, with the value-band handles that feed detection.

### Chunk C — Morlet temporal filter (v1 semantics to preserve)

- `core/wavelet.py`: Torrence–Compo Morlet, `W0 = 6.0`, FFT-based, complex64;
  scales `(W0 + √(2+W0²))/(4π f)`; zero-padding to `next_fast_len` past the
  COI e-folding; returns power `|w|²` float32.
- Frequency bank: `geomspace(0.5, min(25, 0.45·fps), 24)` — log-spaced, capped
  below Nyquist.
- Two uses, both needed: (a) pooled replicate-mean series → `(F, T)` scalogram
  for display (~8 ms at T = 30k — cheap enough to be near-live); (b) per-block
  `(F, T, B)` cube whose band sum feeds the density graph and detection
  (expensive; v1 builds it off-thread, on demand, LRU-cached under a 6 GiB
  budget).
- COI handling matters: display fades outside the cone
  (e-folding ≈ 1.369/f s); v1 also widens detect windows by 2.5 × 2 × COI so
  seams land inside valid regions. Any chunked evaluation in v2 must widen by
  COI or the seams will ring.
- Scalogram rendering: log-frequency y-axis, per-column max reduction,
  log-scaled warm colormap, band title readout.
- Draggable band handles: two handles, drag past top/bottom = unbounded,
  ±∞ ↔ clamped to bank endpoints, drag-continuous (cheap re-sum) vs
  commit (expensive recompute) as separate signals. This two-tier
  drag/commit split is worth keeping as a *concept* even if v2's coalescer
  implements it differently.
- "Morlet is the first of a class of temporal filters": the seam to design is
  *series (T,B) + params → per-block filtered magnitude (F,T,B) or (T,B)*.
  The frequency-band UI is generic to any filter with a tunable band; the
  scalogram display is Morlet-specific.

### Chunk D — detection layer (v1 semantics to preserve)

- Pure-function chain in `core/detection.py`, shared verbatim between live
  and whole-video paths (a property to keep):
  `band power (T,B)` → `inband_count(m, vlo, vhi)` → `count (T,)` →
  `windowed_mean(count, D, centered)` → `detect_gate(windowed, clo, chi)` →
  `gate (T,) ∈ {0,1}`.
- "# blocks in band" = blocks whose *band-power value* lies inside the value
  band — the frequency band is applied upstream by summation. Two distinct
  bands, easy to conflate.
- `windowed_mean` is a prefix-sum mean over D frames, centered or trailing,
  truncated honestly at clip edges. **D is in frames**, range 1..T−1, default
  ≈ 1 s; label shows both frames and seconds.
- The red draggable line on the green graph is the *count band* (min/max in
  raw block counts, upper usually pulled to +∞). Count-band values are
  denominated in blocks, so a block-size change silently rescales meaning —
  v1 re-denominates by the actual block-count ratio (`rescale_count_band`)
  with a visible note (13× error otherwise). v2 must preserve either the
  re-denomination or store the threshold as a *fraction* of region blocks
  (cleaner; decide in stage 3).
- Green shading = gate runs, floored to 1 px so single-frame detections stay
  visible. Gate is computed regardless of widget visibility ("visibility
  decides what is drawn, never what is computed") — keep that rule.
- Threshold / D / centered changes are instant (no re-transform); frequency
  or value band drags re-sum the cached cube; only upstream parameter changes
  (downsample/block/normalize/signal) re-run extraction.

### Chunk E — v1 coupling that must NOT come over

1. God objects: two ~2 500-line widget classes owning workers, caches, cost
   models, persistence, and math orchestration.
2. Detection state living in plot-widget paint state (`band_lo/band_hi` on
   three widgets, read back out via `detection_params()`), with a three-valued
   `None`/±∞/float encoding every consumer re-handles. In v2 the detector is
   a value in the document; plots render it.
3. Rebuild-the-widget-as-state-migration (geometry change destroys the
   explorer and hand-copies view state through serialization methods on the
   widget, order-dependent).
4. Nine hand-tuned QTimer debounces with cross-cancellation; token/generation
   counters as a substitute for cancellable requests. v2 has `coalescer.py` +
   the executor for exactly this.
5. Six hand-rolled QThread subclasses, each with its own cancel/delete dance.
6. `resolve_block_size` re-derived at 3+ call sites, one reading a different
   source. Parameter resolution must have one home.
7. Whole-atlas extraction paid even when scoped to one region (~13× waste) —
   the single largest thing v1's own handoff says to eliminate.

### v2-side considerations

What exists, and the constraints it imposes. File references are into this
repo at `1fab942`.

**What exists toward the goals: nothing.** No wavelet, no structure tensor, no
optical flow, no per-block statistics, no zscore, no detection math anywhere in
`src/`. `wavelet_bands` appears only as a deliberately-unregistered filter id
in tests. Every chunk is greenfield on the v2 side; the constraints below are
about *where* each piece is allowed to live.

**Layering (`.importlinter`) decides placement:**
- `gui → bench → pipeline → filters → decode|backend → core`. The tab may
  import everything below it; nothing below may import the tab.
- `opencv-containment`: **cv2 is legal only in `filters/` and
  `decode/reader.py`.** The Jtt/LK extraction (GaussianBlur, resize) must be a
  pipeline filter; it cannot be tab-side code.
- `core-purity`: numpy/scipy math is legal in `core/` — the natural home for
  ported `wavelet.py` / `detection.py` pure functions (they were the *good*
  part of v1, shared verbatim between live and whole-video paths).

**The filter contract fits extraction but not the Morlet transform:**
- A kernel is per-frame, one-in/one-out, index-preserving; `executor._bind`
  refuses `Mode.WINDOWED`, rate-changing, multi-input (`executor.py:220-235`).
- Jtt / LK extraction is expressible: a **stateful STREAMING kernel** whose
  state is the previous preprocessed frame (`warmup_frames = 1`), emitting a
  small GRAY float32 frame of shape `(ny, nx)` per source frame — a legal
  `Frame`. Stateful ⇒ not cacheable (same caveat as `background_ema`);
  acceptable because extraction at working resolution is ~realtime.
- The Morlet CWT needs the whole series → it stays **outside the pipeline**
  for this milestone, as pure functions applied to the collected `(T, B)`
  series. This mirrors v1's actual dataflow (stream extraction, transform on
  the collected window) and matches "the pipeline graph is invisible for now".
  Growing the kernel protocol to windowed nodes is already deferred in
  `docs/LATER.md:96-135`; this plan does not touch it.

**Per-replicate scoping is free.** The executor applies the replicate ROI at
every root (`executor.py:242`) and the preview renders one replicate. v1's
largest waste (whole-atlas extraction when scoped to one region, ~13×)
disappears by construction.

**Downsample mismatch.** v2's `downsample` filter takes integer `factor`
(2–64); v1's control is a float linear scale 0.05–1.0 in 0.05 steps. Parity
requires the float-scale semantics (0.25 = 25 % linear). Resolution: a new
params version of `downsample` accepting a float scale (INTER_AREA, no-op ≥ 1),
or a separate `rescale` filter. Decide in the work item; the UI shows the v1
scale either way.

**Where knob state lives.** The tab's knobs (downsample, block, normalize,
signal choice) define a three-node pipeline. Because `Pipeline` is a frozen
data structure and cache keys are content-derived, the tab can **construct a
pipeline value from its controls and hand it to
`PreviewRunner.request_render`** without writing the document's artifact, the
undo stack, or the deferred parameter-panel machinery (`docs/LATER.md:366-399`).
Cache reuse across knob wiggles falls out of `node_key`. Persisting these
params into the project artifact is explicitly out of scope here.

**Render plumbing exists and is unused by any view.** `PreviewRunner`
(signals `frame_cost` / `render_started` / `render_finished`, latest-wins
coalescing, tested) is drawn nowhere today. It needs one extension: a way for
the tab to receive **per-frame node outputs** (the block-signal frames) — the
`Consumer`/`on_frame` hook exists at the `PreviewSession` layer
(`preview.py:99`) but is not exposed through `request_render`.

**Detector state must not live in plot widgets** (v1 coupling #2). A Qt-free
value — frequency band, value band, count band, D, centered — owned by the tab
(or `gui/state.py`, the SCAFFOLD-reserved home for UI state with no natural
owner), with plots as dumb renderers taking setters and emitting drag signals.
This matches the house pattern: document/state + signals, views told what to
paint (`timeline_bar.py` is the template — `TimelineStrip` owns no state).

**Plot toolkit is an open decision this milestone settles.**
`mockups/filter_tab.py:143-146` deliberately used QPainter (~60 lines per
graph) to avoid pre-deciding pyqtgraph; napari and pyqtgraph are installed and
imported by nothing (`TODO.md:266-279`). Three bespoke plots with band
handles, log axes, COI fade, and gate shading is exactly the workload that
decides it. Recommendation: QPainter, with the band-handle machinery as one
small shared module — pyqtgraph's value is generic interactivity we would
mostly be fighting.

**Length is already solved.** `TimelineBar` (cross-tab, below the tabs) owns
window start + window length spinboxes in seconds — the target's "length lives
with the cross-tab player" is the current architecture, untouched.

**Debounce/coalesce discipline.** v1's nine QTimers collapse onto v2's
existing two tiers: knob changes → `PreviewRunner`'s latest-wins revisions
(re-render); band drags → cheap pure recompute on the GUI thread or a single
worker with `RequestCoalescer` discipline. The drag-continuous vs
drag-committed split from v1 maps to `band_changed` (re-sum cached cube) vs
`band_committed` (rebuild anything expensive).

**House conventions that bind the work items:** filter = one module + one
markdown, self-registered, discovered namelessly (test-enforced); tests pin
the load-bearing claim, 2–3 per item; TODO items < 150k context, completion
is atomic into `docs/completed-todo/`; measurements go to `docs/findings/`;
latency budget misses are defects (`ARCHITECTURE.md` #4) — the band-drag and
knob-settle interactions should get budget entries or an explicit deferral.

### Reconciliation — carry / adapt / drop

| v1 thing | Verdict | Reason |
|---|---|---|
| Downsample = float linear scale, INTER_AREA | carry | it is the parity semantic |
| Block = working px, 0 = auto from 64 source px | carry | grid fixed in source px is the right invariant |
| Normalize zscore (fused affine, mean 128 sd 32) | carry | parity; `off` too |
| Normalize clahe | drop (optional later) | known edge artifact; not in the nine goals |
| Morlet: W0=6, geomspace(0.5, min(25, .45·fps), 24), COI fade + widen | carry | the transform *is* the feature |
| Pooled-mean scalogram for display + per-block cube for detection | carry | two uses, both needed |
| Jtt = blurred ⟨I_t²⟩, σ=2.0; LK per-pixel solve then reduce, det ≤ 1e-6 → 0 | carry | parity semantics, incl. aperture honesty |
| Density-heatmap rendering of the signal graph | adapt | keep the heatmap idea; simplify (no hatching for lagging cubes unless spans lag) |
| Detection chain as pure functions shared by all paths | carry | the best part of v1 |
| Count band in raw block counts + re-denomination | adapt | store the threshold as a **fraction of region blocks**; render in counts. Kills the 13× foot-gun without the conversion machinery |
| "Visibility decides what is drawn, never what is computed" | carry | as a stated rule in the tab's docstring |
| Drag = cheap update, commit = expensive rebuild | carry | as coalescer-mediated behavior |
| Collapsible per-channel plot stack, 7 channels | drop | two fixed graphs per the target |
| God-object surface/explorer, widget-state-as-truth, 9 debounce timers, 6 QThread subclasses, token staleness guards, rebuild-as-migration, atlas extraction | drop | the reasons the rewrite exists |
| Sidecar persistence (tuning/track stores), whole-video track, process/save buttons, ROI-clip toggle, window-start spinner, All-channels toggle | drop | out of scope / non-goals |

---

## Stage 3 — formal plan

Seven work items, ordered bottom-up along the layer stack so each lands with
its own tests before anything above it needs it. Each is sized to TODO.md
rule 3 and written to be liftable into `docs/TODO.md` as-is.

### Item 1 — Wavelet and detection math (`core/`)

**Files:** `src/sieve/core/wavelet.py`, `src/sieve/core/detection.py`,
`tests/unit/test_wavelet.py`, `tests/unit/test_detection.py`,
`tests/property/` additions where a property pins more than an example.

Port the v1 semantics as Qt-free, cv2-free pure functions:
- `morlet_scales`, `morlet_power(x, fs, freqs)` accepting `(T,)` → `(F,T)` and
  `(T,B)` → `(F,T,B)`; W0 = 6.0, FFT via `scipy.fft`, zero-pad past COI to
  `next_fast_len`, float32 power out.
- `default_freqs(fps)` = `geomspace(0.5, min(25.0, 0.45·fps), 24)`.
- `coi_efolding_s`, `coi_edge_samples`, `band_indices` (empty span snaps to
  nearest scale).
- `inband_count`, `windowed_mean` (prefix-sum, centered/trailing, honest edge
  truncation), `detect_gate`. Count threshold API takes a **fraction of B**
  and converts at the edge, so no `rescale_count_band` port.

Load-bearing claims to test: (a) a pure tone at f₀ concentrates power in the
nearest scale row; (b) `windowed_mean` at clip edges divides by the true
window length, not D; (c) `band_indices` on an empty span returns exactly one
scale. Adds scipy to core deps — confirm `pyproject.toml` and that
import-linter contracts stay green.

### Item 2 — Preprocessing filters (`filters/`)

**Files:** `src/sieve/filters/rescale.py` + `.md` (or a v2 params version of
`downsample` — decide in-item, one paragraph in the module docstring),
`src/sieve/filters/normalize.py` + `.md`,
`tests/unit/test_rescale.py`, `tests/unit/test_normalize.py`.

- `rescale`: float `scale ∈ [0.05, 1.0]`, `round(src·scale)`, INTER_AREA,
  no-op at 1.0. `frame_bytes_ratio() = scale²`.
- `normalize`: `mode ∈ {off, zscore}`; zscore is the fused affine to
  mean ≈ 128, sd ≈ 32 from global per-frame stats, float32 out. (`clahe`
  deliberately omitted; note it in the `.md`'s "what it does not do".)

Claims: rescale at 0.25 yields `round(w·0.25)` and preserves dtype; zscore of
any nonconstant frame has mean ≈ 128 / sd ≈ 32 within tolerance; a constant
frame does not divide by zero.

### Item 3 — Block-signal extraction filter (`filters/`)

**Files:** `src/sieve/filters/block_signal.py` + `.md`,
`tests/unit/test_block_signal.py`.

One filter, `signal ∈ {change_energy, flow_speed}`, `block: int` with
`0 = auto` (`max(1, round(64 · scale))` — the filter receives working-pixel
frames, so auto needs the scale as an explicit param; keep resolution in
**one** function, exported, unlike v1's three call sites).
`@stateful_kernel`, state = previous frame, `warmup_frames = 1`; emits GRAY
float32 `(ny, nx)` frames, index-preserving.
- change_energy: `it = g − gp`, `GaussianBlur(it², σ=2.0)`, block mean.
- flow_speed: 6 tensor products, blur σ=2.0, per-pixel 2×2 LK solve with
  `|det| ≤ 1e-6 → v = 0`, `hypot(u,v)·fps`, block mean. fps enters as a param
  so the kernel stays pure.

Claims: (a) a static input yields exactly zero for both signals from frame 1;
(b) a uniform x-translation of a textured patch yields flow_speed ≈ speed·fps
within tolerance and change_energy > 0; (c) an aperture-degenerate input
(uniform gradient) yields flow_speed exactly 0, not noise. First frame is
warmup, not emitted as signal.

### Item 4 — Per-frame output delivery from the preview (`pipeline/` + `gui/`)

**Files:** `src/sieve/pipeline/preview.py` (if anything),
`src/sieve/gui/preview_runner.py`, `src/sieve/gui/series_collector.py` (new,
Qt-free), tests in `tests/gui/test_preview_runner.py` +
`tests/unit/test_series_collector.py`.

Expose the existing `Consumer` hook through `request_render` so a caller can
receive each `FrameResult` (or one node's output) on the render thread, and
add a Qt-free `SeriesCollector` that assembles `(T, ny, nx)` float32 from
block-signal frames for the current revision, discarding superseded
revisions (reuse the revision numbers `preview_runner` already stamps).
GUI-thread delivery of the completed series rides `render_finished`.

Claims: a superseded render never contributes rows to the served series; the
collected array's frame axis aligns with `plan.span` (lead-in excluded);
per-frame delivery does not regress `slider_to_preview` (budget test).

### Item 5 — Plot widgets (`gui/`)

**Files:** `src/sieve/gui/band_plot.py` (shared QPainter base: series/heatmap
painting, log or log1p axis, two draggable band handles with
drag-past-edge = unbounded, `band_changed`/`band_committed` signals, gate-span
underpaint floored to 1 px), `src/sieve/gui/scalogram_plot.py` (log-f axis,
per-column max reduction, warm ramp, COI alpha fade, band readout in the
title), `tests/gui/test_band_plot.py`, `tests/gui/test_scalogram_plot.py`
(synthetic-event drag tests via the existing `tests/gui/qt_input.py`).

Widgets own **no detector state**: setters in, drag signals out, exactly the
`TimelineStrip` pattern. This item settles pyqtgraph-vs-QPainter: QPainter,
and if that survives review, drop pyqtgraph from the `gui` extra in a
follow-up noted in the completed entry.

Claims: dragging a handle past the plot edge emits an unbounded band; a
1-frame gate run at any zoom paints ≥ 1 px; handle hit-testing tolerates
overlapping handles (disambiguation by side).

### Item 6 — The filter tab (`gui/`)

**Files:** `src/sieve/gui/filter_tab.py`, `src/sieve/gui/detector_state.py`
(Qt-free dataclass: freq band, value band, count fraction band, D frames,
centered, signal choice, knob values, + the pure recompute chain gluing item 1
functions), `src/sieve/gui/main_window.py` (one `addTab` + wiring),
`tests/gui/test_filter_tab.py`, `tests/unit/test_detector_state.py`.

Layout per the target: left — `VideoView` (fed from the existing
`player.frame_changed`), the green **windowed # blocks in band** plot under
it, the **D slider** (frames, label `N fr (S s)`) under that; right — control
row (Downsample float spin 0.05–1.0/0.05 · Block spin 0 = `auto (N)` ·
Normalize combo `off|zscore` · Reset) above the **scalogram** and the
**signal graph** with a two-option selector `change energy (Jtt) | LK optical
flow`. Timeline/Length untouched below the tabs.

Behavior wiring:
- Knob or signal change → build the three-node `Pipeline` value → 
  `request_render`; collected series → pooled scalogram + per-block cube →
  full recompute. Cube built off the GUI thread; latest-wins.
- Freq/value band drag → re-sum/threshold the cached cube (no re-render);
  commit recomputes anything deferred.
- Count band, D, centered → instant pure recompute of windowed/gate.
- Reset → defaults for knobs, bands unset, D ≈ 1 s. Gate computed regardless
  of visibility.

Claims: (a) a knob change while a render is in flight yields exactly one
final recompute with the last value; (b) band drags never trigger a render;
(c) reset restores documented defaults and clears bands; (d) the pipeline the
tab builds round-trips `Dag.build` + `ExecutionPlan.build` with warmup 1.

This item is likely the largest; if it crowds 150k, split the detector-state
model (+ its tests) out as 6a and the widget assembly as 6b.

### Item 7 — Parity comparison finding (`docs/findings/`)

**Files:** `docs/findings/2026.MM.DD-v1-parity-comparison.md`, plus whatever
tiny harness it needs under `tools/`.

The point of the milestone: run v1 and v2 on
`videos-testing/stab_GX010050c2_02_18_26.MP4` with matched settings
(scale 0.25, block auto, zscore, same band, same D) and record: numeric
agreement of count/gate series where comparable, interaction latencies
(knob-settle → first tick, band drag → repaint) against the budget table,
throughput, and a gained/lost list. Anything lost that matters becomes a
LATER.md entry with its trigger.

### Order and gating

1 → (2, 3 in either order; 3 uses nothing from 2) → 4 → 5 (parallel with 4)
→ 6 → 7. Items 1–3 are pure/headless and land independently of any GUI
decision.

### Open decisions to settle at item time (not blockers)

- Item 2: new `rescale` filter vs a params-v2 of `downsample`.
- Item 5: exact colormap stops (copy v1's ramps or restyle to the mockup
  palette).
- Item 6: whether `detector_state.py` is instead the SCAFFOLD-reserved
  `gui/state.py`.
- Whether the knob-settle and band-drag interactions get rows in the
  ARCHITECTURE.md budget table now (recommended: yes, in item 6) or a LATER
  entry.

### Explicitly deferred (with triggers, per LATER.md discipline)

- Persisting tab params into the project artifact + undoable param edits —
  trigger: the parameter-panel item (`docs/LATER.md:366-399`) or the first
  complaint that tuning is lost across sessions.
- Windowed/multi-input kernel protocol (Morlet as a real pipeline node) —
  trigger already written in `docs/LATER.md:96-135`.
- clahe normalize, the five dropped channels, whole-video processing, saved
  detections, detection lanes on the cross-tab timeline (`docs/LATER.md:158`).
