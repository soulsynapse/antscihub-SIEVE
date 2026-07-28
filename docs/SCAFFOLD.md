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
tools/transcript_stats.py               # mines session transcripts: where agent wall-clock went
tools/doc_drift.py                      # reports stamped prose docs whose subject paths moved

src/sieve/core/types.py                 # Frame, ROI, value objects everything pattern-matches on
src/sieve/core/filter_base.py           # THE FILTER CONTRACT: FilterSpec, ParamsBase, Mode, warmup arithmetic
src/sieve/core/filter_registry.py       # the shelf; filters/ puts things on it via decorator
src/sieve/core/pipeline_model.py        # THE SAVED ARTIFACT: pydantic DAG, schema v2 with Edge.port
src/sieve/core/replicates.py            # replicate identity, overrides, resolved_params, equivalence groups
src/sieve/core/detection.py             # windowed_mean + detect_gate, the detection chain tail
src/sieve/core/wavelet.py               # morlet_band_power, default_freqs (capped at 0.45*fps)
src/sieve/core/machine.py               # the machine read once: available_cpus, available_memory

src/sieve/decode/reader.py              # the only path to a frame; OpenCV VideoCapture, pinned
src/sieve/decode/prefetch.py            # threaded span reads, measured 1.61x and no further
src/sieve/decode/identity.py            # decoder identity string feeding the cache key

src/sieve/backend/dispatch.py           # device policy only; holds no kernel
src/sieve/backend/identity.py           # backend identity for keys of non-backend_agnostic filters

src/sieve/filters/__init__.py           # pkgutil scan; names no filter module (a test enforces this)
src/sieve/filters/downsample.py         # anti-aliased spatial decimation
src/sieve/filters/rescale.py            # intensity rescale
src/sieve/filters/normalize.py          # per-frame global illumination removal
src/sieve/filters/background_ema.py     # first stateful filter; the twin to copy for new stateful ones
src/sieve/filters/block_signal.py       # change_energy, flow_speed, coherence — the 3D structure tensor
src/sieve/filters/temporal_baseline.py  # per-cell median/MAD null; the units thresholds are denominated in
src/sieve/filters/motion_history.py     # MHI: leaky accumulator with dilate/diffuse coupling, declared group delay

src/sieve/pipeline/dag.py               # resolve, reject cycles and untypeable edges, one topological order
src/sieve/pipeline/plan.py              # everything knowable before a frame decodes: params, keys, lead-in
src/sieve/pipeline/cache_key.py         # key derivation; ports bind upstream keys so a-b != b-a
src/sieve/pipeline/cache.py             # store protocol
src/sieve/pipeline/executor.py          # THE ONE EXECUTION PATH. CLI, GUI, and HPC all call this
src/sieve/pipeline/preview.py           # PreviewSession: re-render the working window, pay only below the edit
src/sieve/pipeline/materialize.py       # the replicate crop artifact: cut it, verify the read-back, record it

src/sieve/storage/crop_writer.py        # FFV1/Matroska encode from arrays; knows no identity

src/sieve/bench/budgets.py              # the budget table; character-exact against ARCHITECTURE.md
src/sieve/bench/metrics.py              # Qt-free metric bus; judges samples against BUDGETS on the way past
src/sieve/bench/retention_trace.py      # session recorder + the retention policies a trace is replayed through

src/sieve/cli/app.py                    # Typer entry point
src/sieve/cli/common.py                 # shared option plumbing
src/sieve/cli/inspect_cmd.py            # `sieve inspect` — a filter's declaration and its guidance
src/sieve/cli/run_cmd.py                # `sieve run` — execute a YAML project
src/sieve/cli/preview_cmd.py            # `sieve preview` — headless window render, --check is an exit code
src/sieve/cli/materialize_cmd.py        # `sieve materialize` — one replicate's crop, written and registered

src/sieve/gui/app.py                    # QApplication bootstrap
src/sieve/gui/main_window.py            # tabs, the cross-tab timeline, panel orchestration
src/sieve/gui/document.py               # ReplicateDocument: the edited project, clip, selection
src/sieve/gui/commands.py               # QUndoCommands; the only writers of document state
src/sieve/gui/history.py                # automatic rollback snapshots: whole projects on disk; Qt-free
src/sieve/gui/history_dialog.py         # File > History: action text plus age, and the restore
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
src/sieve/gui/chain_stack.py            # the step cards
src/sieve/gui/chain_model.py            # its Qt-free half
src/sieve/gui/param_form.py             # widgets generated from a filter's params model
src/sieve/gui/commit_combo.py           # a drop menu that commits on selection, never on highlight
src/sieve/gui/composite_view.py         # the step composite: output over input, plus the block grid overlay
src/sieve/gui/preview_runner.py         # holds a PreviewSession on its own thread; emits per-frame cost
src/sieve/gui/detector_worker.py        # derives the detector off the GUI thread so graphs fill as frames land
src/sieve/gui/concurrency.py            # the one declaration of how the session divides the machine
src/sieve/gui/executor_adapter.py       # the ONLY place that knows both bench/metrics and Qt
src/sieve/gui/player.py                 # playback, scrub, frame requests
src/sieve/gui/decode_worker.py          # decode off the GUI thread
src/sieve/gui/proxy_cache.py            # coarse-grid frame cache serving the scrub budget
src/sieve/gui/render_ring.py            # the render's recent frames as proxies, played instead of re-decoded
src/sieve/gui/scrub_policy.py           # when to degrade to the coarse grid; Qt-free
src/sieve/gui/coalescer.py              # two slots, rank rule, source stamp; Qt-free
src/sieve/gui/timeline_bar.py           # the full-width band: working window and playhead
src/sieve/gui/timeline_model.py         # its Qt-free arithmetic
src/sieve/gui/band_plot.py              # the base plot widget the rest specialize
src/sieve/gui/graph_hud.py              # per-frame cost series; BandPlot with handles suppressed
src/sieve/gui/scalogram_plot.py         # morlet scalogram with draggable band handles
src/sieve/gui/count_plot.py             # windowed block count with the detection threshold handle
src/sieve/gui/density_plot.py           # detection density
src/sieve/gui/series_collector.py       # accumulates per-frame series for the plots
src/sieve/gui/wheel_steps.py            # app-wide one-detent-one-step wheel filter, with run acceleration
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
the test only guards the named files: `tests/unit/` (37 modules), `tests/gui/`
(28), `tests/integration/` (6), `tests/property/` (4).

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
src/sieve/bench/profiling.py            # VizTracer + py-spy — todo/profiling-as-a-module.md
src/sieve/hpc/handoff.py                # DAG -> job script — todo/hpc-handoff-and-review-mode.md
src/sieve/hpc/sweep.py                  # parameter sweeps, immutable fragments
src/sieve/review/output.py              # VISION step 7 review contract — todo/hpc-handoff-and-review-mode.md
src/sieve/cli/hpc_cmd.py                # arrives with hpc/handoff.py
src/sieve/gui/state.py                  # only when UI state has no natural owner; see TODO.md deferred decisions
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
  either needs a new demand, not a revisit. See `docs/TODO.md` *Deferred
  decisions* and `docs/todo/pipeline-editor-list-or-graph.md`.
- **`docs/ARCHITECTURE-TREE.md`**. `docs/findings/` holds measurement-driven
  decisions one file at a time and `docs/completed-todo/` holds what was built;
  nothing was left for a third log to carry.
- **`src/sieve/docs/*.md`** — the eight interface specs `SIEVE-HANDOFF.md` used
  to ask for. That directory never existed. The contracts live in module
  docstrings with their reasoning in the matching completed-todo entry, which is
  the arrangement that survived; the handoff now says so.
