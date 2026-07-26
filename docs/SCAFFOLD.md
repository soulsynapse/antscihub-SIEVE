SIEVE — Projected final repository scaffold.

This is an estimate of how the repo should look in it's final state, more or less.

```
sieve/
├── pyproject.toml
├── noxfile.py
├── README.md
│
├── docs/
│   ├── ARCHITECTURE.md              # North star: commitments, latency budgets, component boundaries
│   └── ARCHITECTURE-TREE.md         # Navigatable decision log (what was chosen and why)
│
├── src/
│   └── sieve/
│       ├── __init__.py
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   │
│       │   ├── types.py
│       │   │   # Frame, ROI, and metadata value objects shared across all layers.
│       │   │   # LOAD-BEARING: Frame carries dtype, shape, channel spec.
│       │   │   # Everything downstream pattern-matches on these — no stringly-typed metadata.
│       │   │
│       │   ├── filter_base.py
│       │   │   # FilterSpec, ParamsBase, ArraySpec, Mode. The contract, as data.
│       │   │   # LOAD-BEARING: this is a *spec*, never an implementation. Nothing
│       │   │   # here executes, so a saved DAG validates structurally with no
│       │   │   # filters installed. Kernels live in filters/, one per backend.
│       │   │   # A spec must carry:
│       │   │   #   - params_model: one pydantic model, the single source of truth
│       │   │   #     (GUI widgets, CLI flags, YAML, and cache key all read it)
│       │   │   #   - accepts/emits ArraySpec (dtype, channels, dims) for static validation
│       │   │   #   - warmup_frames — 0 for stateless; the executor sums these along
│       │   │   #     the path, and an IIR's value is a settled-within-epsilon choice
│       │   │   #   - mode: STREAMING vs WINDOWED (executor uses it for pipelining)
│       │   │   #   - deterministic: same backend, same input, same output. Gates caching.
│       │   │   #   - backend_agnostic: CPU and GPU kernels agree bit for bit. Gates whether
│       │   │   #     backend identity enters the cache key. False for float kernels; claiming
│       │   │   #     it requires an equivalence test.
│       │   │   #   - cost estimate (wall-time/frame, peak memory) for HUD predictions
│       │   │   #   - explicit semver; bump invalidates cache for that node
│       │   │   #   - primary params subset (1-3) for GUI default view; rest behind "Advanced"
│       │   │
│       │   ├── filter_registry.py
│       │   │   # The registry container and lookup, by (filter_id, version).
│       │   │   # Populated from above by decorators at import time — core defines the
│       │   │   # shelf, filters/ puts things on it. Adding a decorated class in
│       │   │   # filters/ is sufficient; nothing here enumerates them.
│       │   │
│       │   ├── pipeline_model.py
│       │   │   # Pydantic v2 model for the serializable pipeline DAG artifact.
│       │   │   # LOAD-BEARING: Given this artifact + source video path, any executor
│       │   │   # (CLI, GUI, HPC) reproduces the run. No implicit state.
│       │   │   # Serializes to YAML. Pydantic generates JSON Schema for validation.
│       │   │
│       │   ├── config.py
│       │   │   # pydantic-settings app config.
│       │   │   # Precedence: CLI flags > env vars > config file.
│       │   │
│       │   └── constants.py
│       │       # Immutable constants: hash version seeds, cache format version.
│       │
│       ├── decode/
│       │   ├── __init__.py
│       │   │
│       │   ├── reader.py
│       │   │   # OpenCV VideoCapture wrapper. Pinned v1 decoder.
│       │   │   # DECISION: Seek accuracy chosen over source bit-depth preservation.
│       │   │
│       │   └── identity.py
│       │       # Decoder identity string for cache key derivation.
│       │       # Changing decoder version invalidates all downstream cache entries.
│       │
│       ├── backend/
│       │   ├── __init__.py
│       │   │
│       │   ├── dispatch.py
│       │   │   # Device policy: given a filter's declared backends and the machine,
│       │   │   # pick one. A dict lookup on (filter_id, backend_name) plus a policy.
│       │   │   # DECISION: CuPy is the only v1 GPU backend. No Torch unless isolated worker.
│       │   │   # LOAD-BEARING: holds no filter's implementation. If adding a filter
│       │   │   # required editing a file here, non-negotiable #3 would be broken.
│       │   │
│       │   ├── namespace.py
│       │   │   # Array-API namespace resolution (numpy vs cupy) and host/device transfer.
│       │   │
│       │   └── identity.py
│       │       # Backend identity string for cache keys, mirroring decode/identity.py.
│       │       # Enters the key for every filter that is not backend_agnostic.
│       │
│       ├── pipeline/
│       │   ├── __init__.py
│       │   │
│       │   ├── dag.py
│       │   │   # DAG construction, validation, cycle detection, topological sort.
│       │   │   # Rejects invalid graphs statically using filter I/O type declarations.
│       │   │
│       │   ├── executor.py
│       │   │   # The single shared executor. CLI, GUI, and HPC all use this identically.
│       │   │   # LOAD-BEARING: GUI adds a view over this — never a separate execution path.
│       │   │
│       │   ├── cache.py
│       │   │   # Content-addressed intermediate cache (memory-resident during tuning).
│       │   │   # Keys include upstream hashes + filter params + decoder identity.
│       │   │   # Non-deterministic filters are legal but flagged for correct cache behavior.
│       │   │
│       │   ├── cache_key.py
│       │   │   # Hash derivation logic.
│       │   │   # Inputs: upstream node hashes, filter version, filter params, decoder identity.
│       │   │
│       │   ├── preview.py
│       │   │   # Representative-clip preview mode.
│       │   │   # Handles temporal filter warmup (consumes warmup_frames before visible clip).
│       │   │   # SPEED REGIME: "In-pipeline" — slider to graph update must feel direct.
│       │   │
│       │   └── materialize.py
│       │       # User-initiated compaction from memory cache to Zarr v3 on disk.
│       │       # Never automatic. User decides when intermediates are worth persisting.
│       │
│       ├── storage/
│       │   ├── __init__.py
│       │   │
│       │   ├── zarr_store.py
│       │   │   # Zarr v3 materialized arrays. Filesystem-is-truth.
│       │   │   # DECISION: No Zarr v2 compatibility path.
│       │   │
│       │   └── sharding.py
│       │       # Workload-specific Zarr v3 sharding configuration.
│       │
│       ├── workers/
│       │   ├── __init__.py
│       │   │
│       │   ├── manager.py
│       │   │   # Supervision of long-lived multiprocessing.Process compute workers.
│       │   │   # Crash isolation: a filter crash cannot take down the host process.
│       │   │
│       │   ├── protocol.py
│       │   │   # Versioned bidirectional IPC message protocol.
│       │   │   # Version negotiation on worker startup.
│       │   │
│       │   ├── shm_transport.py
│       │   │   # Named shared-memory frame transport between parent and workers.
│       │   │   # Zero-copy where possible.
│       │   │
│       │   └── process.py
│       │       # Single worker subprocess lifecycle: spawn, heartbeat, teardown.
│       │       # Cooperative cancellation with escalation to SIGTERM then SIGKILL.
│       │
│       ├── bench/
│       │   ├── __init__.py
│       │   │
│       │   ├── budgets.py
│       │   │   # Latency budget table. Source of truth for both speed regimes.
│       │   │   # LOAD-BEARING: Budget misses are defects, not accepted tradeoffs.
│       │   │   # Tested against ARCHITECTURE.md values by test_budget_table.py.
│       │   │
│       │   ├── metrics.py
│       │   │   # Metric collection bus. No Qt dependency — runs headless.
│       │   │   # GUI's executor_adapter bridges this to Qt signals.
│       │   │
│       │   └── profiling.py
│       │       # VizTracer phase timelines + py-spy live sampling integration.
│       │       # Complementary: VizTracer for structure, py-spy for production sampling.
│       │
│       ├── observe/
│       │   ├── __init__.py
│       │   │
│       │   ├── logging.py
│       │   │   # structlog JSON Lines setup for parent process.
│       │   │
│       │   ├── log_aggregator.py
│       │   │   # Parent-side aggregation of per-worker JSON log streams.
│       │   │   # Dedicated per-worker stderr capture to separate file descriptors.
│       │   │
│       │   ├── ctf.py
│       │   │   # Per-process CTF trace files with post-hoc merge.
│       │   │
│       │   └── results.py
│       │       # Parquet writer for authoritative results dataset.
│       │       # DuckDB queries over Parquet and JSON Lines.
│       │       # HPC: immutable result fragments with explicit compaction.
│       │
│       ├── cli/
│       │   ├── __init__.py
│       │   │
│       │   ├── app.py
│       │   │   # Typer entry point. The canonical run path — built and tested before GUI.
│       │   │
│       │   ├── run.py
│       │   │   # `sieve run` — execute a pipeline DAG from YAML.
│       │   │
│       │   ├── inspect_cmd.py
│       │   │   # `sieve inspect` — print filter metadata and guidance.
│       │   │
│       │   ├── preview_cmd.py
│       │   │   # `sieve preview` — headless representative-clip execution with metrics.
│       │   │
│       │   ├── materialize_cmd.py
│       │   │   # `sieve materialize` — compact intermediates to Zarr v3.
│       │   │
│       │   └── hpc_cmd.py
│       │       # `sieve hpc` — generate job scripts from the serialized DAG.
│       │
│       ├── gui/
│       │   ├── __init__.py
│       │   │   # BOUNDARY: Qt stays in this package. Nothing outside imports PySide6.
│       │   │
│       │   ├── app.py
│       │   │   # PySide6 QApplication bootstrap.
│       │   │
│       │   ├── main_window.py
│       │   │   # Top-level window layout and panel orchestration.
│       │   │
│       │   ├── viewer.py
│       │   │   # napari widget for video/image frame display.
│       │   │
│       │   ├── graph_hud.py
│       │   │   # pyqtgraph real-time benchmark HUD overlay.
│       │   │
│       │   ├── pipeline_editor.py
│       │   │   # Visual DAG editor. Edits the same pipeline_model as CLI/YAML.
│       │   │
│       │   ├── preview_panel.py
│       │   │   # Live representative-clip preview with direct-manipulation feel.
│       │   │
│       │   ├── executor_adapter.py
│       │   │   # QObject adapter: bridges bench/metrics bus → Qt signals.
│       │   │   # This is the only coupling point between executor and Qt.
│       │   │
│       │   └── state.py
│       │       # UI-only ephemeral state (scrub position, zoom, panel layout).
│       │       # Never persisted to pipeline artifact. Never affects execution.
│       │
│       ├── hpc/
│       │   ├── __init__.py
│       │   │
│       │   ├── handoff.py
│       │   │   # Serialize pipeline DAG → cluster job script.
│       │   │   # Same artifact CLI consumes; HPC is not a special path.
│       │   │
│       │   └── sweep.py
│       │       # Resource sweep semantics for batch parameter exploration.
│       │       # Immutable result fragments; explicit compaction to Parquet.
│       │
│       ├── review/
│       │   ├── __init__.py
│       │   │
│       │   └── output.py
│       │       # Post-run review-mode data contract (Step 7 of workflow vision).
│       │
│       └── filters/
│           ├── __init__.py
│           │   # pkgutil scan over this package's modules at import, so a decorated
│           │   # class in a new module is discovered with no edit here.
│           │
│           ├── downsample.py          # FilterSpec + @kernel("cpu") + optional @kernel("gpu")
│           ├── downsample.md          # Guidance, found by convention. A test asserts it exists.
│           │
│           └── optical_flow.py        # May import cv2 or cupy. The spec above it stays pure.
│
└── tests/
    ├── __init__.py
    ├── conftest.py                    # Shared fixtures; fast/slow markers; conditional CUDA/GL sessions
    │
    ├── unit/
    │   ├── __init__.py
    │   ├── test_types.py
    │   ├── test_filter_base.py
    │   ├── test_pipeline_model.py
    │   ├── test_cache_key.py
    │   ├── test_dag.py
    │   ├── test_dispatch.py
    │   ├── test_protocol.py
    │   ├── test_shm_transport.py
    │   └── test_config.py
    │
    ├── integration/
    │   ├── __init__.py
    │   ├── test_executor.py
    │   ├── test_worker_lifecycle.py
    │   ├── test_materialize.py
    │   └── test_decode.py
    │
    ├── bench/
    │   ├── __init__.py
    │   ├── test_budget_table.py       # Asserts budgets.py matches ARCHITECTURE.md values
    │   └── test_perf_regression.py    # pytest-benchmark latency checks
    │
    ├── property/
    │   ├── __init__.py
    │   └── test_filter_contract.py    # Hypothesis: any conforming filter satisfies contract invariants
    │
    └── gui/
        ├── __init__.py
        └── test_executor_adapter.py   # pytest-qt: signal emission correctness (dev-gui only)
```
