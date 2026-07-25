# Architecture

See [workflow-vision](docs\01-vision\workflow-vision.md) for what this is derived from.


# SIEVE — Architecture

This document is the **broad architectural plan**. It commits to structure,
component boundaries, and the criteria that load-bearing contracts must
satisfy. It does *not* specify those contracts — each has its own reference
document so it can be designed carefully in isolation. This document assumes
those specs meet the criteria stated here.

This document is a working guide, not a specification. Treat claims as hypotheses to verify against the code. If you find a contradiction or correction, measure against project goals and code practices.

## Index of reference documents

Load-bearing specs (to be written; criteria for each are stated in this doc):

- `FILTER_CONTRACT.md` — the interface every filter implements
- `PIPELINE_SCHEMA.md` — the serializable DAG artifact (project file / HPC handoff)
- `CACHE_KEY_SPEC.md` — content-addressed cache key derivation
- `WORKER_PROTOCOL.md` — subprocess IPC, shared-memory frame transport
- `BACKEND_DISPATCH.md` — CPU/GPU selection policy
- `GUIDANCE_FORMAT.md` — the markdown convention colocated with filters
- `PREVIEW_SEMANTICS.md` — warmup handling for temporal filters in preview
- `DETERMINISM_POLICY.md` — what "same inputs → same outputs" means concretely
- `REVIEW_OUTPUT_SPEC.md` — Step 7 review-mode data contract

Companion docs (exist or planned):

- `BENCHMARKING_VISION.md` — the two-layer benchmarking plan (results table + CTF traces)
- `HPC_HANDOFF.md` — job script generation, resource sweep semantics

---

## 1. Purpose and core commitments

SIEVE is a video signal-processing tool built around one question: how much economy can the user buy back without losing signal? The whole architecture serves the ability to answer that question interactively for a representative clip, then execute the answer over the full dataset locally or on HPC.

This tool's value is first measured in speed. Speed has two distinct regimes, and both are load-bearing:

Pre-pipeline speed — from opening a video to having replicates cut and a clip selected. This must feel like a video editor, not a distributed system.
In-pipeline speed — from dragging a slider to seeing the graph update. This must feel like direct manipulation, not job submission.
The v1 prototype earned its reception because both regimes felt immediate. Architectural choices that improve one regime at measurable cost to the other are regressions, regardless of how clean they are.

Latency budgets
These are hard targets on a representative development machine (mid-range laptop, no discrete GPU required for the pre-pipeline regime). Any layer that cannot meet them is a bug to be fixed, not a tradeoff to be accepted.

| Interaction | Budget | Regime |
| --- | --- | --- |
| File open → first frame visible | < 500 ms | pre-pipeline |
| Scrub / seek → frame repainted | < 50 ms | pre-pipeline |
| Replicate cut confirmed → ready to add filter | < 200 ms | pre-pipeline |
| First filter added → first graph tick on screen | < 2 s | in-pipeline |
| Slider drag → preview clip repainted | < 100 ms | in-pipeline |
| Slider drag → dependent graph updated | < 200 ms | in-pipeline |
| Full-clip preview render (5–10 s clip, typical pipeline) | < 3 s | in-pipeline |
These budgets are the acceptance criteria for the tuning-loop-is-the-product commitment. They are checked in CI on a canonical clip and canonical pipeline; a PR that regresses any budget by more than 20% requires explicit justification.

Four commitments the architecture never violates
The filesystem is truth — at rest. A user can navigate to any materialized artifact and see exactly what it is, without SIEVE running. During interactive tuning, truth lives in the decoder and in-memory pipeline state; the filesystem-as-truth contract kicks in at compaction and terminal output, not on every slider drag.
The pipeline is a data structure. GUI, CLI, and HPC executor all consume the same serialized artifact. There is no "GUI-only state" that affects pipeline execution. (Pre-pipeline interactions — scrub position, zoom level, panel layout — are UI state and are not part of the pipeline artifact.)
The filter is the extension unit. Adding a filter is writing one class plus one markdown file. The GUI, CLI, cache, and HPC handoff pick it up with no other changes.
Nothing materializes without reason. In-memory during editing; compaction to disk is user-initiated or explicitly pressure-triggered. The "MP4 per step" model is a mental model for reasoning about determinism, not a storage policy.
The tuning loop is the product. The latency budgets above are the operational definition. Any architectural layer that imposes measurable latency on the pre-pipeline or in-pipeline interactive loops is a regression against the tool's core value, regardless of how clean it is.

## 2. Progressive-MVP framing

The vision document builds SIEVE up in seven progressive stages, each a
functional product on its own. The architecture must respect this: **each
stage's substrate is a strict subset of the next stage's substrate**. Stage 4
adds the GUI on top of Stages 1–3's execution model; it does not replace it.
Stage 5's guidance layer reads from the same filter metadata that Stage 3's
CLI already exposes.

Practically, this means the CLI executor is built first and remains the
canonical run path. The GUI is a live view over the same executor with a
representative-clip preview mode swapped in.

## 3. Layer model

Strict one-way dependencies. Each layer knows about layers below it, never
above.

```
┌─────────────────────────────────────────────────────┐
│  gui/    cli/    review/                            │  ← user-facing
├─────────────────────────────────────────────────────┤
│  bench/                                             │  ← observation
├─────────────────────────────────────────────────────┤
│  workers/                                           │  ← execution isolation
├─────────────────────────────────────────────────────┤
│  pipeline/         (DAG, executor, cache, preview)  │  ← orchestration
├─────────────────────────────────────────────────────┤
│  backends/    io/                                   │  ← runtime/storage
├─────────────────────────────────────────────────────┤
│  core/             (filters, contract, dtypes)      │  ← pure logic
└─────────────────────────────────────────────────────┘
```

Enforcement: `core/` has no imports from anything above it, no Qt, no Zarr, no
subprocess. `pipeline/` never imports Qt. `bench/` never imports Qt, so that
the CLI and headless benchmark runs can observe without a GUI toolkit; the
QObject adapter over the metric bus lives in `gui/`. `gui/` never imports from
`workers/` directly — it goes through `pipeline/`. This is the mechanism that
makes CLI and HPC parity real rather than aspirational.

## 4. The pipeline is a DAG

Filters fork and merge — one raw video feeds an optical-flow branch and an HSV
branch that get combined downstream. The pipeline model is a directed acyclic
graph. A linear operation list is a degenerate DAG and renders identically in
the UI, but the underlying model must support forks from day one.

Consequences that ripple through the rest of the architecture:

- Cache keys include upstream content hashes (see `CACHE_KEY_SPEC.md`) so
  siblings on a shared parent don't invalidate each other
- Materialization ("compaction") happens at a *node*, not a step index
- The operations panel needs a minimap that appears when the DAG forks; it
  stays invisible in the linear degenerate case
- The pipeline schema is a node list with explicit `inputs:` references, not
  an ordered array with implicit chaining

## 5. Storage substrate — filesystem-as-truth without the cost

The user-facing model: source video in a folder; each transformation writes
its result to a child folder; navigation to any folder shows what that stage
produced. This is the model, not necessarily the physical storage on every
step.

The physical policy:

- **During editing:** intermediates live in-memory in the worker. Nothing is
  written until compaction.
- **At compaction:** user opts to persist a node. The persisted form is Zarr
  (chunked N-D array, dtype-honest, memory-mappable, slice-efficient) with a
  `preview.mp4` sidecar so filesystem navigation still shows a viewable
  artifact. Compaction is initiated by the user or suggested by the memory
  pressure heuristic; it is never automatic.
- **At full-video output:** the executor materializes what the pipeline
  declares as terminal outputs — mask video, coordinate CSV, background-
  subtracted video, whatever the DAG's output nodes specify.

Zarr is not required for the MVP CLI executor to work; it is required once
compaction and HPC handoff are real. The cache/materialization layer is where
this policy lives (see `pipeline/materialize.py` in §14).

5.5 The pre-pipeline loop
Before any filter exists, the user opens a video, scrubs to find the interesting segments, cuts replicates, and selects a representative clip. This is not filter execution and does not route through the pipeline executor, the cache, or the worker subprocess. It is a direct, in-process interaction with the decoder and the UI, governed by the pre-pipeline latency budgets in §1.

Treating crop and replicate selection as pipeline nodes — which is architecturally tempting for uniformity — would route every scrub through DAG construction, cache-key derivation, IPC serialization, and shared-memory handoff. That is the correct machinery for filter execution and the wrong machinery for showing a user their own video.

Requirements
Eager head-decode on open. As soon as a file is selected, the decoder begins decoding the head of the video into a ring buffer. The first frame is on screen before any user action is required. The full keyframe index builds in the background and does not block display.
Index-based scrubbing. Scrub and seek hit the nearest keyframe plus a short forward decode. No worker roundtrip, no cache lookup, no pipeline evaluation. A scrub interaction is a decoder call and a widget repaint.
Replicates materialize in the background by default. Cropping a small ROI out of an HD decode is where the ~25× speedup lives; keeping crops virtual throws that speedup away on every subsequent scrub, filter add, and slider drag. On replicate commit, a background worker begins writing the cropped frame range to a fast local intermediate (raw or lightly-compressed, dtype-honest, keyframe-dense for scrub). The UI reports "materializing — Nx speedup incoming" non-modally; the user is not blocked and can start adding filters against the still-decoding source. As soon as the materialized version is ready, the executor swaps its source pointer transparently. Filters already running continue against the original decode until their next invocation.
Opt-out is a setting, not a prompt. Storage-constrained users can disable background materialization globally; the loop then falls back to virtual crops against the original decode. This is the only case where the pre-pipeline latency budgets are allowed to slip, and the UI states so.
Materialized replicates are not cache entries. They are source artifacts owned by the project, tied to the replicate record, not to any pipeline node's cache key. Invalidation happens when the user edits the replicate's frame range or bbox, not when the pipeline changes.
Replicates become sources, not filters. When the user commits to tuning a filter, the selected replicate becomes the source of the pipeline's root node — consumed lazily by the executor via the same virtual coordinates. The filter DAG does not contain a "crop" node for the replicate; the crop is intrinsic to the source.
In-process decode for display. The subprocess boundary described in §10 exists for filter execution. Decode-for-display, overlay compositing, and scrub playback remain in the main process (with a dedicated decoder thread where appropriate) to stay inside the < 50 ms scrub budget.
Preview-clip extraction is the handoff point. Only when a filter is added does the pipeline executor engage, at which point it pulls frames for the selected replicate (plus warmup padding per §11) through the worker protocol. Until then, no worker process needs to exist.
What the pre-pipeline loop does not need
No cache. Scrub results are ephemeral; caching them would cost more than recomputing.
No pipeline artifact. Replicate selection is UI state that becomes pipeline state at first filter add.
No backend dispatch. Decode uses the pinned decoder from §12; there is no CPU/GPU choice to make.
No determinism ceremony. Displayed frames are for the user's eyes; the deterministic decode path is exercised when the executor pulls frames for filter input.
Component placement
The pre-pipeline loop lives in io/video_read.py (decode, keyframe index, ring buffer) and gui/panels/video_viewer.py (scrub, overlay, replicate widgets), with a thin gui/replicates.py holding the virtual-replicate list. It does not import from pipeline/, workers/, or backends/. When a replicate is committed to a pipeline, pipeline/graph.py reads the replicate record and constructs the source node; the coupling is one-way and only at commit time.



## 6. Filter contract — criteria

See `FILTER_CONTRACT.md` for the specification. The architecture requires that
the contract satisfy:

- **Single source of truth for parameters.** Whatever schema mechanism it uses
  (Pydantic model, dataclass, whatever) must be the sole declaration of a
  filter's parameters. GUI widgets, CLI flags, YAML fields, cache-key
  contribution, and cost-model input all read from it. No parallel
  definitions anywhere in the codebase.
- **Declared I/O typing.** Each filter declares input and output stream specs
  (dtype, channel count, spatial/temporal dimensionality, valid ranges).
  Enough for the executor to reject invalid graphs statically without
  running them.
- **Explicit warmup declaration.** Each filter declares `warmup_frames` (0
  for stateless filters). This is what `PREVIEW_SEMANTICS.md` uses to make
  the representative clip behave correctly for stateful temporal filters.
- **Explicit streaming capability.** Each filter declares whether it can
  process frame-by-frame or requires a windowed/full-stream view. The
  executor uses this to pipeline streaming filters and avoid materializing
  in-between.
- **Determinism declaration.** Each filter declares whether it is
  deterministic under the project's `DETERMINISM_POLICY.md`. Non-
  deterministic filters (some GPU reductions, some optical-flow variants)
  are legal but must be flagged so the cache can behave correctly and the
  bench layer can annotate results.
- **Cost estimation.** Each filter provides a cost estimate given input
  spec and params: predicted wall-time per frame, peak resident memory,
  GPU memory. Rough is fine — used for the HUD's "this will cost ~40s on
  the full video" prediction and for the guidance layer's suggestions.
- **Backend registry.** Each filter declares which backends it implements
  (`cpu_numpy`, `gpu_cupy`, `gpu_torch`, etc.). The dispatcher picks; the
  filter does not decide.
- **Colocated guidance.** Each filter has a markdown file next to its
  source file (see `GUIDANCE_FORMAT.md`) that the guidance panel renders.
  Content changes are documentation changes, not code changes.
- **Registration is decorator-driven.** Filters register at import time via
  a decorator. The registry is a plugin directory: adding a file with a
  decorated class is sufficient.
- **Versioned.** Each filter has an explicit semver. A bump invalidates
  cache entries for that node.
  Primary parameters declared. Each filter's parameter schema marks a subset (typically 1–3) as primary. The GUI shows only these by default; the rest are behind "Advanced." CLI and YAML expose all parameters equally; this distinction is UI-only.
Toolbar eligibility is metadata, not automatic. A filter declares whether it is a candidate for the default toolbar. The actual toolbar contents are a curated project-level list that draws from candidates. New filters do not silently appear in the user's primary workflow.

If the filter contract meets these criteria, the "GUI panels are generated,
CLI flags are generated, HPC handoff is generated" promise holds. If any is
missing, one of those three fragments.




## 7. Pipeline artifact — criteria

See `PIPELINE_SCHEMA.md`. The architecture requires:

- **Fully describes a run.** Given the pipeline artifact plus the source
  video path, any executor (CLI, GUI preview, HPC) can reproduce the run.
  No implicit state.
- **Human-editable.** A user comfortable with YAML can hand-edit a
  pipeline. This is a debugging affordance and an HPC-power-user
  affordance.
- **Round-trips through the GUI losslessly.** Loading a pipeline into the
  GUI, saving it without changes, must produce a byte-identical (modulo
  formatting) artifact.
- **Node references are explicit.** Each node declares its input nodes by
  ID and output slot. This is what makes the DAG a DAG rather than a list.
- **Versioned.** The schema itself has a version so future changes can be
  migrated cleanly.
- **Cache-key stable.** Reordering unrelated nodes, reformatting, adding
  comments, does not change any node's cache key. See `CACHE_KEY_SPEC.md`.

The pipeline artifact is the project file, the CLI input, and the HPC
handoff artifact. It is the single interchange format.

## 8. Cache key — criteria

See `CACHE_KEY_SPEC.md`. The architecture requires the cache key for a node
to be a deterministic function of:

- The node's parameters (canonicalized)
- The content hashes of all upstream nodes it depends on
- The filter's `name` and `version`
- The selected backend identifier (CPU and GPU results may differ; the
  cache honors this)
- A code-version hash sufficient to invalidate on filter implementation
  changes not captured by `version` bumps (may be tied to git SHA in dev,
  filter-source hash in release)

Anything that can change the output must be in the key. Anything that cannot
must not be, or siblings will spuriously invalidate.

## 9. Backend dispatch — criteria

See `BACKEND_DISPATCH.md`. The architecture requires:

- **Runtime capability detection.** CUDA available? Enough VRAM? MPS?
  Number of CPU cores? Detected once, cached, exposed to the dispatcher.
- **User preference layered on capability.** Global "prefer GPU when
  available"; per-filter override; hard "CPU only" mode for reproducibility.
- **Cost-model tie-breaking.** Some filters are pointless on GPU because
  transfer cost dominates (frame decimation, ROI crop). The filter's cost
  estimate for each backend informs the choice.
- **Graceful fallback.** GPU OOM or missing backend falls back to CPU with
  a logged warning and a bench-layer annotation.
- **Visible in the HUD.** The user always sees which backend actually ran.

## 10. Worker architecture — criteria

See `WORKER_PROTOCOL.md`. The GIL and Qt event loop mean that filters cannot
run in the same process as the GUI without freezing it. The requirements:

- **Compute runs in a separate process**, not a thread. Long-lived worker
  subprocess is preferred over per-job spawns.
- **Frames move via shared memory**, not pickled through a queue. At HD ×
  30fps × 3 channels the pickle cost is prohibitive.
- **GPU worker is singular and serial.** One process owns the CUDA context.
  Multiple GPU jobs queue on it.
- **Qt main thread only orchestrates.** Dispatches jobs, receives
  completion signals, updates widgets. Never runs a filter.
- **The same worker protocol serves the CLI.** The CLI is the worker
  process without the Qt frontend. This is what keeps CLI/GUI parity real.
- **Cancellation is first-class.** A user changing a slider in the GUI
  must be able to interrupt an in-flight preview render cleanly.

## 11. Preview semantics — criteria

See `PREVIEW_SEMANTICS.md`. Temporal filters have warmup transients. A 5-second
preview clip's output at t=0 is not what the full-video output looks like at
that same absolute time. Without correction the tool lies to the user in edge
cases involving IIR, temporal integration, MEI/MHI, 3D wavelets, and Morlet
banks.

Requirements:

- **Warmup padding.** Preview extraction pulls the user-selected window
  *plus* the sum of upstream `warmup_frames` on the temporal path.
- **Trimmed display.** The padded frames are computed but not shown.
- **User-visible warmup budget.** If the padded window would exceed the
  clip length available, the UI tells the user and either extends the
  clip or warns explicitly.
- **Warmup is a filter property, composed by the executor.** Filters do
  not know they are in a preview context.

## 12. Determinism policy — criteria

See `DETERMINISM_POLICY.md`. "Deterministic downstream" is a load-bearing
claim of the vision. It only holds under enforcement.

Requirements:

- **Thread counts fixed per worker.** `OMP_NUM_THREADS`, `MKL_NUM_THREADS`,
  `OPENBLAS_NUM_THREADS` set explicitly. Benchmark numbers reproducible;
  float reduction order stable.
- **Deterministic GPU mode available.** `torch.use_deterministic_algorithms`,
  `CUBLAS_WORKSPACE_CONFIG` set when the user opts in. Off by default (slow);
  on for CI and reproducibility runs.
- **Video decoder pinned.** The decode library and its version are part of
  the code-version hash contributing to cache keys. Decode truncation is a
  hard error by default; opt-out requires an explicit flag and is recorded in
  the run's provenance.
- **CI determinism test.** A canonical short clip runs a standard pipeline;
  outputs are byte-compared across runs and platforms (with documented
  tolerances for GPU float ops).
- **Non-deterministic filters are legal but flagged.** They set
  `is_deterministic = False`; the cache still stores their outputs but
  the bench layer notes it and the pipeline artifact records a run seed.

## 13. Signal-preservation measurement

Half the "GUI guides you" promise depends on being able to say something
useful when the user considers swapping one filter for another. The naive
framing — "does this alternative preserve signal?" — assumes a ground truth.
SIEVE does not assume a universal ground truth. When the user supplies labeled
intervals, positive or negative, the guidance layer uses them. Otherwise it
does not invent labels or truth claims; it reports deltas only. More smoothing
with longer accumulation is not wrong-vs-right against a shorter-window
alternative; it is a different point in a (signal-fidelity × latency ×
economy) space, and which point is correct is a domain judgment SIEVE is not
entitled to make.

The architecture therefore commits to delta characterization, not scoring:

- For any candidate swap, the guidance layer reports observable differences
  against the user's current pipeline: detection count delta, temporal lag
  delta (frames until the signal crosses threshold), spatial footprint delta,
  cost delta. Never a single "preservation" number.
- The user's current pipeline is the reference only in the weak sense that it
  is what the alternative is being compared against. The guidance never claims
  the alternative is closer to truth.
- Optional labeled intervals. If the user marks positive intervals where the
  signal should fire, or negative intervals where it should not, those labels
  anchor the guidance metrics that depend on supervision. This is cheap to
  author and worth surfacing when available. It is not required.

This resolves the labeled-clip vs. baseline-proxy dichotomy: it is neither.
It is labeled-interval-aware when supervision exists, and characterize-the-
delta otherwise. The results table schema
(`BENCHMARKING_VISION.md`) and guidance format (`GUIDANCE_FORMAT.md`) follow
from this commitment.

## 14. Component decomposition

```
sieve/
├── core/                       # Pure algorithms, no I/O, no Qt, no Zarr
│   ├── contract.py             # Filter protocol, StreamSpec, CostEstimate
│   ├── registry.py             # Filter discovery & registration
│   ├── dtypes.py               # Stream dtype declarations
│   └── filters/
│       ├── signal_economy/     # Decimation, pyramid, blocks, blur, pyramid
│       ├── channel/            # RGB↔HSV, optical flow, change energy, ...
│       ├── temporal/           # IIR, Morlet bank, MEI/MHI, temporal integration
│       └── spatial/            # ROI, spatial wavelets, ...
│       Each filter: `<name>.py` + `<name>.md` (guidance) side by side.
├── pipeline/
│   ├── graph.py                # DAG data model
│   ├── executor.py             # Runs a graph
│   ├── cache.py                # Content-addressed cache
│   ├── materialize.py          # Compaction policy (§5)
│   └── preview.py              # Warmup-aware clip extraction (§11)
├── io/
│   ├── video_read.py           # Seek-accurate decode boundary; reports the
│   │                           # dtype it delivers vs. source depth (ADR-018)
│   ├── zarr_store.py           # Chunked intermediate persistence
│   ├── preview_mp4.py          # Sidecar viewable renders
│   └── sidecar.py              # CSV / JSON / Parquet outputs
├── backends/
│   ├── dispatch.py             # Backend selection (§9)
│   ├── capabilities.py         # Runtime capability detection
│   ├── cpu_numpy.py
│   ├── gpu_cupy.py
│   └── gpu_torch.py            # Only if any filter uses torch
├── workers/
│   ├── worker_process.py       # Long-lived compute subprocess
│   ├── gpu_worker.py           # Serial GPU dispatch
│   ├── shm_frames.py           # Shared memory frame transport
│   └── protocol.py             # Job/result messages
├── bench/                      # See BENCHMARKING_VISION.md
│   ├── tracer.py               # VizTracer wrapper (CTF timeline)
│   ├── pyspy.py                # py-spy attach wrapper for ad hoc live diagnosis
│   ├── results_table.py        # Parquet/DuckDB (economy vs. detection)
│   ├── metric_bus.py           # Qt-free metric bus; plain callbacks. The
│   │                           # QObject adapter lives in gui/ so that CLI
│   │                           # and headless runs import bench/ without Qt.
│   └── cost_model.py           # Aggregates filter-declared cost estimates
├── cli/
│   ├── run.py                  # `sieve run pipeline.yaml`
│   ├── bench.py                # `sieve bench pipeline.yaml --sweep ...`
│   ├── hpc_gen.py              # `sieve hpc-export ...` — job script wrapper
│   └── validate.py             # Pipeline lint before submission
├── gui/                        # Qt6, view layer over pipeline + workers
│   ├── main_window.py
│   ├── panels/
│   │   ├── video_viewer.py     # Video + overlay stack
│   │   ├── toolbar.py          # Top ribbon
│   │   ├── operations_list.py  # DAG view; linear when degenerate
│   │   ├── operation_detail.py # Current-op panel + graph + refine
│   │   ├── benchmark_hud.py    # Live cost readout
│   │   └── guidance_panel.py   # Renders filter's colocated markdown
│   ├── widgets/
│   │   ├── schema_to_qt.py     # Auto-generates widgets from params schema
│   │   ├── color_picker.py     # HSV clicker etc.
│   │   └── ...
│   ├── wizards/
│   │   ├── new_project.py
│   │   ├── compaction.py       # Suggested when memory is high
│   │   ├── hpc_export.py
│   │   └── output_export.py
│   └── theming/
├── review/                     # Step 7 — output review mode
│   ├── report_generator.py
│   └── viewer.py               # See REVIEW_OUTPUT_SPEC.md
└── docs/
    ├── filters/                # Auto-generated from filter classes + .md
    └── ...
```

## 15. GUI structure

Panels match the vision document's six regions:

1. **Video viewer** — the representative clip playing
2. **Overlay stack** — raw / composite / current-op-relative overlays,
   toggleable
3. **Toolbar** — top ribbon of filter categories and global actions
4. **Operations panel** — the DAG; a minimap appears when it forks
5. **Operation detail** — current-op parameters (auto-generated from the
   filter's schema), a graph view of the operation's output over the clip
   (with a vertical bar for playhead), and action buttons: *adjust
   visualization* (log transform, alternate view), *refine* (filter-
   specific tool, e.g. HSV clicker)
6. **Benchmark HUD** — live cost of the current operation and projected
   cost for the full video, backend actually running, memory pressure

The six-region layout described is the maximum GUI, not the default. The default is: video viewer, overlay toggles, curated toolbar, graphs. Operations list, operation detail, guidance panel, and benchmark HUD are dockable and closed on first launch. A user who never opens them still has a working tool.



Menus:

- **Project** — new / open / save; the pipeline YAML is the project file
- **Replicate** — navigation, crop management
- **Filter** — add, disable, materialize (compaction), rerun from here
- **Preview** — set representative clip, warmup budget, refresh
- **Backend** — global CPU/GPU preference, memory budget, worker count,
  determinism mode
- **Benchmark** — start trace, open Perfetto on last run, sweep this
  filter's parameters
- **Export** — local run (whole video), HPC handoff, output selection
- **Review** — enter review mode on a completed run

15.5 UI philosophy — curated surface, deep interior
The v1's reception was partly earned by what it did not show. A small, opinionated set of filters (change energy, LK optical flow, intensity, a scalogram band picker) meant the user was never choosing from a menu of twenty options they did not understand. The general-purpose filter framework in §6 is a capability commitment, not a UI commitment.

Principles
Default view is graphs, playback, and the replicate. No DAG minimap, no benchmark HUD, no guidance panel, no operations list expanded, no backend readouts. Just the clip playing with overlays and the graphs filling in below it. This is the state the tool opens into and the state a first-time user sees.
Curated filter shortlist on the toolbar. The default toolbar exposes the small set that solves the 80% case: intensity, change energy, LK optical flow, scalogram band, windowed-block detector, threshold. "More filters…" is one click away and opens the full registry. Adding a filter to the codebase does not add it to the toolbar; toolbar contents are a curated list, edited deliberately.
Power lives in wizards and menus, not in the main view. Compaction, HPC export, backend selection, determinism mode, sweep configuration, review mode — all reachable, none visible by default. The main window's job is to keep the tuning loop uncluttered.
Progressive disclosure per filter. Each filter's detail panel opens with two or three parameters — the ones that actually matter for tuning. "Advanced" reveals the rest. The filter contract's parameter schema (§6) declares which parameters are primary; the widget generator (schema_to_qt.py) respects that declaration.
HUD is opt-in. The benchmark HUD is powerful and belongs in the tool, but it is a panel the user opens, not a strip that occupies screen real estate by default. When collapsed, cost and backend information appear as a single-line status footer, not a panel.
The DAG minimap stays hidden until the graph forks. Restated from §4; reinforced here because it is the single biggest source of visual noise in the general case where the pipeline is linear.





## 16. CLI and HPC

The CLI is the canonical run path. Everything else is built over it.

```
sieve run pipeline.yaml [--source PATH] [--output-dir PATH] [--backend cpu|gpu|auto]
sieve preview pipeline.yaml --clip START,END      # for headless verification
sieve bench pipeline.yaml --sweep params.yaml     # parametric benchmarking
sieve hpc-export pipeline.yaml --scheduler slurm  # generates job script
sieve validate pipeline.yaml                       # lint before submit
```

HPC handoff produces a bundle: the pipeline YAML, the resource declaration
(cores, memory, GPU count), and a scheduler-specific job script that invokes
`sieve run`. See `HPC_HANDOFF.md`.

## 17. Coherence mechanisms

Three enforced patterns keep the codebase from drifting as filters accumulate:

1. **Filter contract is the sole source of truth.** GUI widgets, CLI flags,
   YAML schema, guidance panel, cost model all derive from it. Adding a
   filter never requires touching GUI code.
2. **Pipeline YAML is the interchange format.** The GUI never has state the
   YAML cannot represent. Every GUI action is a mutation of the graph. This
   gives undo/redo (Command pattern), inter-user sharing, and HPC handoff
   for free.
3. **Guidance is data.** Markdown next to the filter, rendered by one
   widget. Refining suggestions is a documentation change.

## 18. Performance patterns worth committing to now

- **Streaming when possible, batching when not.** Filters declare
  `is_streaming`; the executor pipelines them to avoid intermediates.
- **Zero-copy through shared memory** between worker and Qt process.
- **Lazy materialization.** Nothing to disk until compaction or output.
- **Deterministic threading** in workers (see §12).
- **Content-addressed cache** so re-runs with same params are free.

## 19. Maintainability patterns

- **Property-based tests on the filter contract.** For any valid params,
  output shape/dtype matches declaration; no NaN unless declared.
- **CI determinism check** on a canonical clip.
- **Registry auto-discovery** via decorator; filters are plugins.
- **Explicit filter versioning** protects users from silent output changes.
- **Type-checked pipeline schema** at load time — bad graphs are rejected
  before any frame is decoded.

## 20. Resolved policies

The following were open questions in earlier drafts and are now committed.
Cross-referenced here so the reasoning is preserved.

- **Signal preservation is delta characterization, not scoring.** See §13.
- **Intermediate dtype is per-filter, not global.** Each filter declares its
  storage dtype (float16, bfloat16, float32, or integer) via the filter
  contract. Accumulators for temporal state (IIR, MEI/MHI, temporal
  integration, wavelet coefficients) are float32 regardless of storage dtype.
  Edges — decoded input and terminal output — remain at their native dtype.
  Rationale: benchmarks show float16 storage roughly halves memory with no
  meaningful accuracy loss for most filters, but temporal accumulators and
  coefficient-quantization-sensitive filters (Morlet banks, 3D wavelets near
  band edges) can drift. Separating storage from accumulator dtype absorbs
  both cases without forcing a global choice. bfloat16 is preferred over
  float16 where the filter's numeric range benefits from wider exponent
  (optical flow magnitudes, integration accumulators near zero).
- **Multiprocess CTF traces compose via Perfetto Trace Processor.** Each worker
  writes a Chrome/Perfetto-compatible fragment to a run-scoped directory
  (`traces/<run_id>/worker_<pid>.pftrace`) with a stable process name set at
  worker init. On run completion, a post-processing step invokes Trace
  Processor to merge fragments into one viewable timeline; parametric sweeps
  use Batch Trace Processor. On HPC, workers write to node-local scratch and
  sieve collects on job completion, landing one merged trace next to the
  results Parquet. Details in `BENCHMARKING_VISION.md` and
  `WORKER_PROTOCOL.md`.
- **Undo/redo coalescing is a UI concern, not an architecture concern.**
  Continuous parameter changes on the same node within a short window collapse
  into one undo entry, committed on mouse-up or focus loss. Structural edits
  (add / remove / reconnect nodes) never coalesce. Stated once in the pipeline
  schema spec; not load-bearing here.
