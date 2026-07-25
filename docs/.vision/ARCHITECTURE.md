# Architecture

## Raw filter-workflow vision (USER WRITTEN VISION)
At it's core, SIEVE is about applying filters. The absolute bare-bones, pre-optimization version is like this:

1. You have a video file in a folder, and transformations live in subsequent folders.

It does not matter what kind of video file, what preprocessing it has, what encoding it has, SIEVE should be able to ingest it *as is*. The user knows what the folder is, SIEVE doesn't need to know really.

You then apply transformations to it, and again, in the *unoptimized version*, that transformation goes into a folder in that directory. So the logic is clear: you have a source, you did something, the result of that lives in the child folder.

SIEVE should be able to do this for any of the tools that live in the filter tab. It might be making a specialized background subtraction. It might be creating an output video with a mask that only lets through a specific color. It might be the coordinates of that specific color as a csv and enough information to stick it into R. The v1 of SIEVE had it so that you could set morlet wavelet bands, downsample, set pixel block sizes, set thresholds for how many pixels when averaged over time you wanted to count as a detection, and it could do all of that.

But in the simplest, dumbest version of the program, in a way that you can see absolutely everything that happens by navigating folders, each of those would be it's own folder. This would be like an image processor saving the entire processing history to individual files, so that when you have completed the first step, the 2nd step does the thing to the output of the first. Image processing doesn't do it that way because you don't necessarily need the inbetweens, but ideally the user should be able to do that if they want.

2. You crop to replicates

This is a pretty universal step, but is totally optional. You have a cropped replicate, and you can navigate forward and backwards in the replicate tab. This is already built out into SIEVE so it's not a problem.

3. You filter the video.

Keeping with the theme of progressive, layering complexity, below is the next step for elaborating the workflow, but is still relatively simple/dumb, by design. Filters have a ton of different kinds, some of the main important ones for video:

A. Signal/economy interaction filters: Image pyramids, dropping channels, downsampling, frame decimation, pixel blocks and other sampling techniques, blur filters of various kinds. Note that some of these improve signal *and* economy in many situations.

B. Channel filters. Channels might be in the data, and it might be what you compute. So rgb, whatever is in the video, or some kind of computed derivative - optical flow, change energy, etc. The key part is channels are all the information in a single frame. A channel *filter* is when you set acceptance criteria for something downstream.

C. Temporal filters (1d temporal and 3d spatio-temporal) such as IIR, wavelets, frame decimation, MEI, MHI, temporal integration, 3d wavelet transforms.

Note that these things can be done before or after: I could take the optical flow measurement at 1:1, then do the optical flow measurement grouped. I could do a temporal filter on the channel directly (without any filters for thresholding), or do it on the thresholded channel. The order significantly shifts the outcome. But in the dumbest version of this, you do one thing, save it to the whole video (sure hope you have lots of storage), and the downstream is deterministic because it doesn't need to know the stuff above it. At this stage, you don't even have a gui to help you, so it's bumbling around in the dark. Huge files, huge processing overhead, no feedback at all until it's done.

4. You get a gui to tune these things in real time.

Now you have a timeline of the whole clip, but you limit yourself to like 5-10 seconds of it, on a representative part of it chosen by you. As you do transformations, you get feedback on how fast/slow that representative transformation is from the benchmark. This way you're not inherently limited to certain workflows. The multiple transformations are stored in live memory somewhere, so now you can apply multiple things at the same time. When things start getting slow, you can save that representative few seconds to the child layer, and because things are deterministic, it still represents what you're trying to do. Feedback from the benchmark gives you an idea for how expensive things are getting in terms of storage, compute time, required memory. Theres also some kind of information on how much space even just testing is taking up on your storage. You can buy back economy by decimating the video, saving the decimated video, and now you have a huge amount of compute to play with, and you can get some idea of how bad that hurt your ability to process the signal.

The gui gives you a few specific things: the representation of the video, the order of operations, the graphical representation (where you can choose from a few different ways to view the data.. summed total for a given frame, for example, but representative of the specific operation you're looking at. For a given operation, something like 'filter the hsv channel' there are buttons for tools specific to that filter, like a clicker tool to click the video and see how the color is represented in the color space, and handles on that color space to show where you want things cordoned off.

So you have 1: the video which is playing in the time-constained representative clip, 2: the overlay of that video which can switch between transparent (so the user can see the raw video), some kind of overlay representation showing the whole of the current state if you include all the operations, a third overlay showing the relative representation the current operation has on the one immediately before it, then 3: a top toolbar similar to stuff like fusion, word, photoshop that have buttons to implement things to the timeline, 4: the operations history which has stuff like saved to child (frees compute and memory, consumes storage), filter operations like downsampling, computed channels, etc. Then 5: to the right of that filter operation list there's information on the specific filter applied, the live graph with a vertical bar showing where in the 5-10s clip is represented on the graph. To the right of that, theres a few buttons: a) adjust visualization which makes a pop up wizard with options like log transform, change to a different visualization, etc), b) refine, which allows you to do the selection stuff I mentioned (which, when done, is just another operation on the operation list), and then 6: a benchmark summary of what the specific operation costs you.

So with all of the above, you have a comprehensive filter suite that lets you isolate and refine signals over time in a way that you can get direct feedback, progressively see how much it is going to cost you, etc. You can rapidly isolate signals based on signal theory and all of these live in modules so that if I want to add operations over time, it isn't difficult.. if you know how everything works.

5. The GUI guides you

So the user isn't going to know how everything works necessarily, but the key part here is we just bought a bunch of active feedback for the user, now we refine that feedback so that the many options don't overwhelm them.

Given that we have the benchmark information, and can generally know how the different things work, sometimes you don't need dense optical flow. So this is why the 'current operation' step gets a decent amount of screen realestate: users can scroll down from the pure information on that operation and see explanations, alternatives to try, and useful next steps. Information on what this step tends to buy, information on what this step doesn't buy, what isn't recoverable with this step, which formulas tend to work well with it, all that. These actively either try to swap out things or not.

When your memory use is getting high theres some kind of thing in the gui that suggests doing a compaction step - saving to a child folder, at least for the representative clip. It gives you feedback on how fast the video with overlay with graph is going compared to real time which is indirect feedback on compute overhead. But then what does the user do with it?

6. You create outputs

Once you've got your whole timeline, now you need to output everything. This is the final step of the workflow: since the different steps compound, the user can save the video representation of it, maybe tweak how the representation is shown a bit, or select a specific stage to output data to analyze. They can also go to some kind of HPC wizard that will help them with the commandline options - the user might do a compaction checkpoint for their local machine on the test clip, but provided the HPC memory capabilities, storage availability, cpu and gpu access, thread utilization, etc, maybe they don't need to. so the hpc wizard lets them toggle off stuff like a compaction state, or other things. Then tidies it up for them to hand off. Alternatively, the user can opt to do it all on their local computer with something like 'process whole video' and it'll pop up with progress on how that's going. Most projects won't need HPC - SIEVE should just be HPC ready.

7. Review outputs

Something like a processing report and durable results should be the end product. The ability to see the detection blocks, or the background subtracted footage output, or scrub the timeline to see when detection happened or not. This is a first class tool to interpret the outputs after the program runs.


So all in all, you have an intuitive workflow to completely isolate the signal based on replicates, and view the results.

---

Helpful textbook for ideas, but largely single image-focused: https://visionbook.mit.edu/

---


# SIEVE — Architecture

This document is the **broad architectural plan**. It commits to structure,
component boundaries, and the criteria that load-bearing contracts must
satisfy. It does *not* specify those contracts — each has its own reference
document so it can be designed carefully in isolation. This document assumes
those specs meet the criteria stated here.

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

SIEVE is a video signal-processing tool built around one question: **how much
economy can the user buy back without losing signal?** The whole architecture
serves the ability to answer that question interactively for a representative
clip, then execute the answer over the full dataset locally or on HPC.

Four commitments the architecture never violates:

1. **The filesystem is truth.** A user can navigate to any materialized
   artifact and see exactly what it is, without SIEVE running.
2. **The pipeline is a data structure.** GUI, CLI, and HPC executor all consume
   the same serialized artifact. There is no "GUI-only state."
3. **The filter is the extension unit.** Adding a filter is writing one class
   plus one markdown file. The GUI, CLI, cache, and HPC handoff pick it up
   with no other changes.
4. **Nothing materializes without reason.** In-memory during editing;
   compaction to disk is user-initiated or explicitly pressure-triggered.
   The "MP4 per step" model is a mental model for reasoning about
   determinism, not a storage policy.

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
subprocess. `pipeline/` never imports Qt. `gui/` never imports from `workers/`
directly — it goes through `pipeline/`. This is the mechanism that makes CLI
and HPC parity real rather than aspirational.

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
  the code-version hash contributing to cache keys.
- **CI determinism test.** A canonical short clip runs a standard pipeline;
  outputs are byte-compared across runs and platforms (with documented
  tolerances for GPU float ops).
- **Non-deterministic filters are legal but flagged.** They set
  `is_deterministic = False`; the cache still stores their outputs but
  the bench layer notes it and the pipeline artifact records a run seed.

## 13. Signal-preservation measurement

This is a design commitment, not a code layer, but it belongs in the
architecture because half the "GUI guides you" promise depends on it.

The guidance layer's suggestions ("this alternative usually preserves signal
at half the cost") require the ability to measure signal preservation during
preview. Two paths, and the project needs to pick one:

- **User-provided ground truth.** A labeled reference clip against which
  detection metrics (F1, recall at fixed FPR) are computed. Cleaner
  semantics; requires the user to have labeled data.
- **Baseline-pipeline proxy.** The user marks one pipeline as the
  reference; alternatives are scored by agreement with the reference's
  outputs. Doesn't require labels; the reference has no independent claim
  to correctness.

This choice affects the results table schema (`BENCHMARKING_VISION.md`) and
the guidance format (`GUIDANCE_FORMAT.md`). Flagged as an open question in
§20.

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
│   ├── video_read.py           # Dtype-preserving decode
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
│   ├── results_table.py        # Parquet/DuckDB (economy vs. detection)
│   ├── metric_bus.py           # QObject signal bus for live HUD
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

## 20. Open questions

- **Detection-metric ground truth.** See §13 — the guidance layer's
  suggestions depend on how signal preservation is measured. Choice of
  labeled-clip vs. baseline-pipeline-proxy affects `BENCHMARKING_VISION.md`
  and `GUIDANCE_FORMAT.md`.
- **Intermediate dtype policy.** Standardize all filters on float32
  internally with uint8 at edges (simpler, some memory cost), or let each
  filter declare its own dtype and have the executor handle promotions
  (efficient, more executor complexity)? Recommend float32 for v1.
- **Multiprocess-worker HPC semantics.** How CTF trace files from
  multiple worker processes on HPC compose into a single readable
  timeline. Deferred to `WORKER_PROTOCOL.md` / `BENCHMARKING_VISION.md`
  interaction.
- **Undo/redo scope.** Trivial if the pipeline artifact is authoritative,
  but decisions about coalescing (slider drags shouldn't produce 200
  undo entries) belong somewhere.
