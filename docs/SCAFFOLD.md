---
status: current
---

# SCAFFOLD — where things live

This file answers one question: **where does this module go?**

It is in two halves, and the split is the point. **Built** is what exists;
**Projected** is what the architecture intends and nothing has needed yet.
`tests/docs/test_scaffold.py` asserts both halves — every path under Built must
exist, every path under Projected must not. So this file cannot quietly drift
the way its predecessor did: it named a napari viewer and a visual DAG editor
for two weeks after both were rejected, and named five packages that were never
written, while omitting twenty-seven GUI modules that were.

When you add a module, add its line to Built. When you build something Projected
named, move the line. The test tells you if you forgot.

Annotations are one line and say what the module *owns*, not what it contains.
The load-bearing reasoning lives in `docs/ARCHITECTURE.md` and in the module's
own docstring.

---

## Built

```tree
pyproject.toml                          # deps, ruff, pyright strict, pytest config, entry points
noxfile.py                              # the gates; `checks` is the default session
.importlinter                           # machine-checked layer contract
.github/workflows/ci.yml                # runs `nox -s checks benchmark`
CLAUDE.md                               # agent routing doc — the only doc loaded automatically
tools/doc_index.py                      # generates docs/*/.index.md and docs/.state.md from frontmatter
tools/complete_item.py                  # scaffolds a completed-todo entry; git-derived file lists
tools/new_item.py                       # mints a docs/todo/ item; stamps `opened` to the minute
tools/transcript_stats.py               # mines session transcripts: where agent wall-clock went
tools/doc_drift.py                      # reports stamped prose docs whose subject paths moved
tools/doc_refs.py                       # every path a live doc names must resolve; symbols reported
tools/guardrail_refs.py                 # a claimed check must exist; a fired trigger must have an item
tools/session_hooks.py                  # what the session hooks run; jq-free by necessity
.claude/settings.json                   # the three session hooks: primer, tree report, subagent return size
.claude/agents/comment-critic.md        # naive reader; judges a comment against the code it sits on
.claude/skills/comment-check/SKILL.md   # runs it over the working diff, by line range not by file

src/sieve/core/types.py                 # Frame, ROI, value objects everything pattern-matches on
src/sieve/core/request_intent.py        # why a frame was asked for, and whether it may be snapped, retained, or felt
src/sieve/core/filter_base.py           # THE FILTER CONTRACT: FilterSpec, ParamsBase, Mode, warmup arithmetic
src/sieve/core/filter_registry.py       # the shelf; filters/ puts things on it via decorator
src/sieve/core/pipeline_model.py        # THE SAVED ARTIFACT: pydantic DAG at schema v5, and the .sieve.yaml filename convention
src/sieve/core/history.py               # rollback snapshots at rest: the .history/ directory, its filename grammar, retention
src/sieve/core/replicates.py            # replicate identity, overrides, resolved_params, equivalence groups
src/sieve/core/clip_window.py           # ClipRange's algebra: which of a window's length or edges survives an edit
src/sieve/core/ops/detection.py         # windowed_mean + detect_gate, the detection chain tail
src/sieve/core/ops/wavelet.py           # morlet_band_power, default_freqs (capped at 0.45*fps)
src/sieve/core/machine.py               # the machine read once: available_cpus, available_memory, process_memory_bytes
src/sieve/core/pool_meter.py            # busy-time and depth counters a worker pool exposes to a sampler
src/sieve/core/shares.py                # rule 5's ledger: worker constants, memory shares, sensor lists

src/sieve/decode/reader.py              # the only path to a frame; OpenCV VideoCapture, pinned
src/sieve/decode/prefetch.py            # threaded span reads, measured 1.61x and no further
src/sieve/decode/identity.py            # decoder identity string feeding the cache key

src/sieve/backend/dispatch.py           # device policy only; holds no kernel
src/sieve/backend/identity.py           # backend identity for keys of non-backend_agnostic filters

src/sieve/filters/__init__.py           # pkgutil scan, and §3's markdown half: where guidance lives and what it is made of
src/sieve/filters/downsample.py         # anti-aliased spatial decimation
src/sieve/filters/rescale.py            # intensity rescale
src/sieve/filters/normalize.py          # per-frame global illumination removal
src/sieve/filters/background_ema.py     # first stateful filter; the twin to copy for new stateful ones
src/sieve/filters/block_signal.py       # change_energy, flow_speed, coherence — the 3D structure tensor
src/sieve/filters/temporal_baseline.py  # per-cell median/MAD null; the units thresholds are denominated in
src/sieve/filters/motion_history.py     # MHI: leaky accumulator with dilate/diffuse coupling, declared group delay

src/sieve/pipeline/dag.py               # resolve, reject cycles and untypeable edges, one topological order; linear_order for the graphs a stack can host
src/sieve/pipeline/plan.py              # everything knowable before a frame decodes: params, keys, lead-in
src/sieve/pipeline/cache_key.py         # key derivation; ports bind upstream keys so a-b != b-a
src/sieve/pipeline/cache.py             # store protocol
src/sieve/pipeline/executor.py          # THE ONE EXECUTION PATH. CLI, GUI, and HPC all call this
src/sieve/pipeline/preview.py           # PreviewSession: re-render the working window, pay only below the edit
src/sieve/pipeline/series_collector.py  # one node's per-frame outputs into the (T, ny, nx) series a detector runs on
src/sieve/pipeline/materialize.py       # the replicate crop artifact: cut it, verify the read-back, record it
src/sieve/pipeline/source_home.py       # what a crop record is read against: video, project dir, parent identity — one value
src/sieve/pipeline/resolve_source.py    # which file a replicate reads — a crop artifact or the parent — and in whose numbering
src/sieve/pipeline/crop_binding.py      # its reporting twin: which record backs a replicate, and which clause a stale one missed

src/sieve/storage/crop_writer.py        # FFV1/Matroska encode from arrays; knows no identity

src/sieve/detect/detector.py            # DetectorSettings -> intervals, below both front ends; the settled frontier
src/sieve/detect/tables.py              # a detection as CSV for R — series and intervals as two files

src/sieve/bench/budgets.py              # the budget table; character-exact against ARCHITECTURE.md
src/sieve/bench/metrics.py              # Qt-free metric bus; judges samples against BUDGETS on the way past
src/sieve/bench/retention_trace.py      # session recorder + the retention policies a trace is replayed through
src/sieve/bench/sweep.py                # response surface over core sets and worker counts; affinity is the machine axis

src/sieve/cli/app.py                    # Typer entry point
src/sieve/cli/common.py                 # shared option plumbing
src/sieve/cli/inspect_cmd.py            # `sieve inspect` — a filter's declaration and its guidance
src/sieve/cli/run_cmd.py                # `sieve run` — execute a YAML project
src/sieve/cli/preview_cmd.py            # `sieve preview` — headless window render, --check is an exit code
src/sieve/cli/materialize_cmd.py        # `sieve materialize` — one replicate's crop, written and registered
src/sieve/cli/detect_cmd.py             # `sieve detect` — a saved project's intervals, no Qt
src/sieve/cli/sweep_cmd.py              # `sieve sweep` — decode throughput over core sets; changes affinity, so never a test

src/sieve/gui/app.py                    # QApplication bootstrap
src/sieve/gui/main_window.py            # tabs, the cross-tab timeline, panel orchestration
src/sieve/gui/document.py               # ReplicateDocument: the edited project, clip, selection
src/sieve/gui/commands.py               # QUndoCommands; the only writers of document state
src/sieve/gui/history_dialog.py         # File > History: the restore list, and age_text that renders it
src/sieve/gui/wizard.py                 # project creation flow
src/sieve/gui/wizard_model.py           # its Qt-free half
src/sieve/gui/replicate_tab.py          # video + tools panel + replicate table
src/sieve/gui/replicate_table.py        # per-replicate rows, numeric ROI entry
src/sieve/gui/crop_tools.py             # draw/stamp toggle, stamp size, magnifier reset, parent info
src/sieve/gui/editing_sources.py        # who claims the keyboard: a set of named sources, Qt-free
src/sieve/gui/video_view.py             # the four crop gestures and the source<->widget mapping
src/sieve/gui/gray_toggle.py            # the viewport's decode-format control: manual, auto while rendering, pin
src/sieve/gui/zoom.py                   # the magnifier: zoom, pan centre, and the fit it is clamped against
src/sieve/gui/filter_tab.py             # the tuning surface: composite, chain, plots
src/sieve/gui/chain_stack.py            # the step cards, and the source card above them
src/sieve/gui/chain_model.py            # its Qt-free half
src/sieve/gui/param_form.py             # widgets generated from a filter's params model
src/sieve/gui/commit_combo.py           # a drop menu that commits on selection, never on highlight
src/sieve/gui/block_spin.py             # the Block knob, refusing the sizes the density graph cannot bin
src/sieve/gui/composite_view.py         # the step composite: output over input, plus the block grid overlay
src/sieve/gui/preview_runner.py         # holds a PreviewSession on its own thread; emits per-frame cost
src/sieve/gui/detector_worker.py        # derives the detector off the GUI thread so graphs fill as frames land
src/sieve/gui/materialize_worker.py     # writes a crop artifact off the GUI thread: progress, cancel, one at a time
src/sieve/gui/concurrency.py            # the one declaration of how the session divides the machine
src/sieve/gui/executor_adapter.py       # the ONLY place that knows both bench/metrics and Qt
src/sieve/gui/resource_probe.py         # samples RSS and pool utilisation off the GUI thread, mode-tagged
src/sieve/gui/transport/__init__.py     # frames arriving: the package boundary, and why it is one
src/sieve/gui/transport/player.py       # playback, scrub, frame requests
src/sieve/gui/transport/decode_worker.py  # decode off the GUI thread
src/sieve/gui/transport/proxy_cache.py  # coarse-grid frame cache serving the scrub budget
src/sieve/gui/transport/render_ring.py  # the render's recent frames as proxies, played instead of re-decoded
src/sieve/gui/transport/scrub_policy.py # when to degrade to the coarse grid; Qt-free
src/sieve/gui/transport/coalescer.py    # two slots, rank arithmetic, source stamp; Qt-free
src/sieve/gui/transport/pacing.py       # where playback goes next, and the frontier it folds against; Qt-free
src/sieve/gui/timeline/__init__.py      # the band, and the one-way edge to the transport
src/sieve/gui/timeline/bar.py           # the full-width band: working window and playhead
src/sieve/gui/timeline/geometry.py      # its Qt-free arithmetic: the frame-to-column mapping
src/sieve/gui/band_plot.py              # the base plot widget the rest specialize
src/sieve/gui/graph_hud.py              # per-frame cost series; BandPlot with handles suppressed
src/sieve/gui/scalogram_plot.py         # morlet scalogram with draggable band handles
src/sieve/gui/count_plot.py             # windowed block count with the detection threshold handle
src/sieve/gui/density_plot.py           # detection density
src/sieve/gui/wheel_steps.py            # app-wide one-detent-one-step wheel filter, with run acceleration
src/sieve/gui/keyboard_handback.py      # app-wide filter: Enter or Esc in a spin box releases the keyboard
src/sieve/gui/preferences.py            # persisted user preferences
src/sieve/gui/preferences_dialog.py     # their editor
src/sieve/gui/toast.py                  # transient notices

tests/conftest.py                       # synthetic_video: frame n has blue = n*5, so seeks are assertable
tests/gui/conftest.py                   # importorskip PySide6, modal-dialog muzzle, document fixture
tests/property/conftest.py              # the hypothesis "property" profile, deadline disabled
tests/docs/test_doc_index.py            # index staleness is a test failure
tests/docs/test_scaffold.py             # this file's two halves are a test failure
tests/bench/test_budget_table.py        # ARCHITECTURE.md <-> budgets.py, bidirectional
tests/bench/test_budget_producers.py    # a budget nothing publishes is a number, not a ceiling
tests/unit/test_filter_discovery.py     # non-negotiable #3, AST-checked
tests/unit/test_cache_key.py            # cache isolation between sibling branches
```

Directories not listed line by line, because their contents are conventional and
the test only guards the named files: `tests/unit/` (49 modules), `tests/gui/`
(39), `tests/integration/` (11), `tests/property/` (6).

---

## Projected — not built

Each line is a module the architecture intends and nothing has yet needed. None
of these exists; the test asserts that, so a line here is a promise, not a lie.
Where a deferral has *reasoning and a trigger*, that reasoning lives in
the matching `docs/todo/` item and is named in the annotation — this file only
says where the file would go.

```tree
src/sieve/core/config.py                # pydantic-settings app config — todo/application-config.md
src/sieve/core/constants.py             # hash seeds, cache format version (currently inline)
src/sieve/backend/namespace.py          # array-API namespace resolution — todo/gpu-execution.md
src/sieve/storage/zarr_store.py         # Zarr v3 arrays, the general store — todo/materialization.md
src/sieve/storage/sharding.py           # workload-specific sharding
src/sieve/workers/manager.py            # crash isolation — todo/process-isolation.md
src/sieve/workers/protocol.py           # versioned IPC
src/sieve/workers/shm_transport.py      # shared-memory frame transport
src/sieve/workers/process.py            # worker lifecycle, cooperative cancellation
src/sieve/observe/logging.py            # structlog JSON Lines
src/sieve/observe/log_aggregator.py     # per-worker stream merge
src/sieve/observe/results.py            # Parquet results dataset
src/sieve/bench/profiling.py            # VizTracer + py-spy, both already in the dev group
src/sieve/hpc/handoff.py                # DAG -> job script — todo/hpc-handoff-and-review-mode.md
src/sieve/hpc/sweep.py                  # parameter sweeps, immutable fragments
src/sieve/review/output.py              # VISION step 7 review contract — todo/hpc-handoff-and-review-mode.md
src/sieve/cli/hpc_cmd.py                # arrives with hpc/handoff.py
src/sieve/gui/state.py                  # only when UI state has no natural owner; see docs/SETTLED.md
src/sieve/gui/source_boundary.py        # the crop card and its write pass, out of filter_tab — todo/the-source-boundary-is-its-own-object.md
src/sieve/filters/crop.py               # the ROI as a filter, identity crop is full-frame — todo/the-crop-is-a-filter.md
src/sieve/filters/span.py               # the clip span as a filter; decode pushdown stays a planner optimization — todo/the-span-is-a-filter.md
src/sieve/filters/detect.py             # detection emitting a per-frame channel — todo/detection-is-a-filter.md
src/sieve/mutual/__init__.py            # dependency-shared, not agreement-shared: shares, machine, pool_meter — todo/the-mutual-tier.md
```

`.importlinter` declares `(sieve.workers)` in parentheses, so the layer contract
governs it from its first commit rather than being widened afterwards to
accommodate it. When it is built, drop the parentheses in the same commit that
moves its line up — which is what `sieve.storage` did on 2026-07-28, when
`crop_writer.py` became the first module in it.

---

## Rejected — do not build these

The previous version of this file named all three, and an agent following it
would have written code that three separate decisions had already refused.

- **`gui/viewer.py` (napari)** and **`gui/pipeline_editor.py` (visual DAG
  editor)**. The plot layer settled as QPainter widgets over `band_plot.py`, and
  the one item that still owned a napari question — the three-way overlay —
  answered it by collapsing to two layers and one opacity slider. Re-adding
  either needs a new demand, not a revisit. See `docs/SETTLED.md`. The list
  VISION step 4 actually asks for is an ordinary list widget over `Dag.order`;
  whether a branching graph later wants one widget that degrades to a list or
  two views over one model is settled by watching a user, not by argument, and
  cannot arise before `Edge` grows named ports
  (`docs/todo/kernel-protocol-beyond-one-frame.md`).
- **`docs/ARCHITECTURE-TREE.md`**. `docs/findings/` holds measurement-driven
  decisions one file at a time and `docs/completed-todo/` holds what was built;
  nothing was left for a third log to carry.
- **`src/sieve/docs/*.md`** — the eight interface specs `SIEVE-HANDOFF.md` used
  to ask for. That directory never existed. The contracts live in module
  docstrings with their reasoning in the matching completed-todo entry, which is
  the arrangement that survived; the handoff now says so.
