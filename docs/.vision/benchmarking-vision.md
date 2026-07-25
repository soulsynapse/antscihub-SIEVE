# Benchmarking Suite — Vision

## Raw vision (USER WRITTEN VISION)

One of the core tenets of the benchmarking plan is that this program, inherently, has a role that is asking about processing economy.

One of the central features of this product is that it asks: when I downsample, how much economy does it produce, and how much detection do I pay for it?

This is seen in the decision to downsample by pixel blocks, vs downsampling the video itself. This is also seen when the user sets the clip length to 5 vs 10 - how long does the active processing take? how much faster than real time are you achieving?

The second central feature is asking: if I allocate these resources, how fast can I do all of it? e.g., I run the whole thing on my pc, when will it be done? if I run it on the hpc, when will that be done? if I change from cpu to gpu, what does that buy me? If I allocate more ram, what does that buy me?

The third central feature is asking: what is inefficient about the program as is? if we a/b test some part of how the program is implemented, how much stuff do we gain?

The third one might be outside the scope of something that needs to be planned deliberately to be user-facing, but I'd like to have a standardized suite so I can visualize which part is taking how much time, and so that between agent sessions, I imagine there is a fairly standard tool/package to reach for to see what is going slow and why, have that both be readable to agents as well as visualized for me when I ask for it to get either a live readout as I navigate the menu (like chrome has, to see where the slowdowns and resource consumption spikes occur) or a report after the fact.

## Purpose

One of the core questions SIEVE answers is **processing economy vs. signal detection**.
The benchmarking suite exists to make that trade-off legible: to the user planning
a run, to the developer optimizing the pipeline, and to agents working in the
repo.

There are many knobs the user can turn to buy back compute — spatial
downsampling (block vs. video-level), temporal downsampling (60fps → 1fps),
clip length, hardware target (local CPU, local GPU, HPC), RAM allocation,
worker count, precision. **A huge part of the tool's value is telling the user
how much of each knob is free.** If dropping 60fps footage to 1fps costs
nothing in detection, the user should know that, and the tool should show the
Pareto frontier that makes it obvious.

The suite has three tenets, and they don't share a data shape. Trying to put
them all in one format hurts the first two.

## Tenet 1 — Economy vs. detection

*"When I downsample, how much economy does it produce, and how much detection
do I pay for it?"*

This is a **parametric sweep** over a grid of settings (spatial factor,
temporal factor, clip length, block-vs-video downsampling, precision, …)
crossed with hardware. Each cell of the grid produces scalar outcomes:
wall_time, peak_rss, throughput_relative_to_realtime, and a detection score
against ground truth (F1, recall at fixed FPR, or whatever the task
specifies).

The natural artifact is a **long-form structured results table**, one row per
run, that supports Pareto-frontier queries and groupby comparisons. Not a
timeline.

## Tenet 2 — Resource scaling

*"If I allocate these resources, how fast can I do all of it?"*

Same shape as Tenet 1: a parametric sweep, but the varying axis is hardware
(local CPU, local GPU, HPC partition, RAM ceiling, worker count) rather than
algorithmic settings. Rows in the same results table, distinguished by a
`hardware_tag` column. This means the user's "how long on my PC vs. HPC"
question and their "how much do I lose going to 1fps" question are answered by
the same substrate — just different groupbys.

## Tenet 3 — Where is time going

*"What is inefficient about the program as-is?"*

This one **is** timeline-shaped: nested spans per pipeline phase, counters
over time (RSS, GPU memory, queue depth), thread/process attribution. It's
what supports the live Chrome-style readout while navigating the app, the
post-hoc "why was this run slow" report, and A/B comparisons of
implementation changes.

Kept as a per-run artifact linked back to the results table by `run_id`.

---

## Architecture — two layers, linked by ID

### Layer A — Results table (Tenets 1 & 2)

**Format:** Parquet, or a DuckDB table over Parquet files. One row per run.

**Schema (initial):**

- `run_id` — UUID, also names the trace file
- `git_sha`, `hostname`, `hardware_tag` (e.g. `local_cpu`, `local_gpu_3090`, `hpc_a100`)
- `params_json` — full parameter dict for the run (spatial factor, temporal
  factor, clip length, downsample_mode, precision, worker count, …)
- `wall_s`, `cpu_s`
- `peak_rss_mb`, `gpu_peak_mb`
- `throughput_realtime_ratio` — how many × real time
- `detection_metric_name`, `detection_metric_value`
- `trace_path` — path to the CTF file for this run

**Queries this enables directly:**

- Pareto frontier of detection vs. wall_time at each spatial factor
- "At what temporal downsample does detection start to fall off?" — plot
  `detection_metric_value` vs. `params_json.temporal_factor` at fixed spatial
- "What does GPU buy me?" — groupby `hardware_tag`, compare `wall_s`
- Regression check across `git_sha` at fixed params

### Layer B — Per-run timeline (Tenet 3)

**Format:** Chrome Trace Event Format (CTF) JSON — the format Chrome DevTools
Performance and Perfetto UI both consume, and which LLM agents parse
trivially. `chrome://tracing` is effectively deprecated; the current viewer is
Perfetto UI (`ui.perfetto.dev`).

**Emitter:** [VizTracer](https://github.com/gaogaotiantian/viztracer). Valid
CTF output, ~10–30% overhead for typical workloads (much less than cProfile),
ships a bundled Perfetto-based viewer (`vizviewer`).

**Instrumentation strategy:** Trace at **algorithmic-phase level**, not
function level, by default. Wrap the phase boundaries you care about — decode,
downsample, detect, aggregate, write — with explicit `tracer.log_event()` or
`@log_sparse` decorators. Drop into function-level tracing only when a phase
looks suspicious. Full-fidelity function tracing has bad noise-to-signal on
tight numpy loops and bloats the JSON.

**Counter events** (`"ph": "C"`) overlay RSS, GPU memory, queue depth, and any
other resource-over-time series. This is what enables the resource-spike
visualization.

### Live readout in the PyQt6 app

Separate from the trace file — VizTracer flushes at process exit, not live.

**Design:** A lightweight metric bus — a `QObject` with signals emitting
`(name, value, t)` — that both feeds a `pyqtgraph` panel for the in-app HUD
and gets logged as CTF counter events when a tracer is active. Same numbers,
two views.

---

## GPU caveat

If real work runs on the GPU, CPU-side Python tracers show launch and sync
points but not what the GPU actually did between them. Time will be
misattributed to whichever function was blocking on the sync.

- **PyTorch stages:** use `torch.profiler` directly. It emits CTF that
  interleaves CPU and CUDA — do not layer VizTracer on top.
- **Plain CuPy / hand-written kernels:** NVTX ranges from within the GPU
  code, viewed in Nsight Systems for authoritative timing. Mirror the same
  range names as CTF spans on the CPU side so the two views line up.
- Expect two views (CPU CTF + GPU Nsight) rather than one unified trace,
  unless the whole GPU path is inside torch.

---

## Explicitly not doing

- **cProfile** — deterministic tracing overhead (10–100% on Python-heavy
  code), single-threaded model, output doesn't compose across runs. Fine for
  a five-minute local check, not a benchmarking suite.
- **OpenTelemetry** — its span model works, but the tooling is oriented at
  distributed request-response services, not signal processing pipelines.
  Not worth the fight without a distributed system.
- **Encoding Tenet 1's sweep inside a single CTF file** — that's a table, not
  a timeline. Both Perfetto and agent tooling would ignore the structure.
- **Speedscope as primary viewer** — nicer flamegraph, but no counter or
  async event support. Fine as a secondary view.

## Possibly worth adding later

- **ASV (airspeed velocity)** — what numpy/scipy/scikit-learn use for
  tracking benchmark regressions over git history. Not useful for the
  economy-vs-detection sweep, but if the results-table layer above is built
  right it's a superset of what ASV does, and ASV can be dropped in later
  for the regression-tracking use case.

---

## Open questions

- What ground-truth set(s) define the detection metric for Tenet 1? The
  Pareto frontier only means something if the y-axis is fixed.
- Which pipeline phases are the right default trace granularity? First cut:
  decode / downsample / detect / aggregate / write. Refine after first
  traces.
- Does any pipeline stage cross the process boundary (multiprocessing
  workers, HPC job splits)? If so, CTF's process/thread model needs a
  deliberate assignment scheme so the timeline stays readable.