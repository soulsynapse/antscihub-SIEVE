# ADR digest

[INTENT] One entry per ADR file in `docs/05-adr/`, keyed to the same number,
compressed to the operative constraint — the part that changes what code gets
written. Rationale, alternatives, and consequences stay in the source.

[STABLE] An entry here summarizes a decision whose `Status` is `Accepted`. A
proposed or superseded ADR does not belong in this digest; a decision leaves
the digest when the ADR that supersedes it enters.

[STALE WHEN] An ADR is added, superseded, or amended. `docs/05-adr/` is the
source of truth; this file is derived and loses to it.

---

**ADR-001 — PySide6 for the UI.**
PySide6 + Qt Widgets (LGPLv3, unlike PyQt6's GPLv3). Embedded napari
`ViewerModel`/`QtViewer` for image/video surfaces; pyqtgraph for dense
time-series and the benchmark HUD. napari is a viewer, not the data model —
only public APIs at the boundary, no `napari._*`. OpenCV/NumPy stay in the
processing layer; adaptation happens at the GUI boundary.
[OPEN QUESTION] The comparison harness ran against PyQt6; the ADR requires
revalidation with PySide6 before first production use. Not yet done.

**ADR-002 — Subprocess workers, shared memory for frames.**
Compute runs in a long-lived subprocess, never in the Qt process or a Qt
thread. Frames move via `multiprocessing.shared_memory.SharedMemory`. The
control channel carries descriptors only (name, shape, dtype, strides,
generation) — never frame bytes. Segment stays alive until the consumer is
done. `setImage(..., autoLevels=False)`.

**ADR-003 — Ruff as the quality gate.**
`ruff check .` and `ruff format --check .`, config in root `pyproject.toml`,
stable rules only (no preview). Automated workflows do not apply fixes.
Pyright stays as the separate type gate, strict on `src/sieve/core` and
`src/sieve/pipeline`. The rule set ratchets up, never down.

**ADR-004 — Pydantic v2 for the filter contract.**
Filter params are Pydantic v2 fields, `ConfigDict(frozen=True)`, and are the
sole declaration. Polymorphic nodes use discriminated unions on the filter-type
field. JSON Schema is generated, never hand-written. `pydantic-settings` for
app config, kept separate from scientific models. Validation happens at
boundaries (load, GUI commit, CLI), never per-frame.

**ADR-005 — YAML pipeline files.**
`pipeline.yaml`, safe loader, data not code. Validated against the ADR-004
models; JSON Schema generated from them. Cache keys derive from validated model
data, never from YAML bytes — reformatting cannot change cache identity.
Comments and anchors are not promised to round-trip.

**ADR-006 — Typer CLI, pydantic-settings config.**
Typer commands are thin adapters; no pipeline composition or scientific logic
in callbacks. Three distinct sources with precedence:
`explicit CLI flag > pipeline value > user preference > application default`.
Absent is distinct from explicitly-false. Hydra is deliberately not adopted.

**ADR-007 — structlog for structured logging.**
Structured event dicts with stable field names; context bound at lifecycle
boundaries (run/node/filter/backend/worker ids). UTC timestamps; console
renderer interactively, JSON Lines for files and HPC. Durations measured with a
monotonic clock and rendered as numeric fields. Per-frame logging is off by
default or sampled. Logs are not the benchmark results table.

**ADR-008 — pytest, Hypothesis, pytest-benchmark.**
Hypothesis property tests derive valid params from each filter's Pydantic
model; the shared contract suite lives in `tests/contract/`. Determinism is
tested with ordinary assertions, not by timing. `slow` marker registered; inner
loop is `pytest -m "not slow"`. Benchmark fixtures are fixed and deterministic;
generation never happens inside the timed region.
[ASSUMPTION] A single wall-time threshold across heterogeneous machines is
explicitly rejected — regression gates need recorded environment metadata.

**ADR-009 — Nox for task orchestration.**
Root `noxfile.py`. Session names are the public automation interface; CI calls
sessions, not their internals. Required names: `lint`, `typecheck`, `test`,
`test_slow`, `determinism_check`, `benchmark`, `build_docs`, `checks`.
`checks` is the composed non-mutating gate. Gate sessions never rewrite the
checkout. GPU CI runs in required-GPU mode where missing CUDA fails.

**ADR-010 — VizTracer + py-spy.**
VizTracer for planned opt-in phase-level CTF timelines via `bench/tracer.py`;
py-spy via `bench/pyspy.py` for attaching to an already-running process. Both
are optional diagnostic dependencies, not runtime imports. Their timings are
not comparable and are not enabled simultaneously during regression runs.

**ADR-011 — Array API kernels, NumPy typing.**
Filter kernels use `array-api-compat` namespaces obtained from the input array;
no hard-coded `np.`/`cp.` inside portable kernels, and no `np.asarray` coercion
to force portability. Backend-specific branches are localized behind named
adapters. `npt.NDArray[...]` only at NumPy-specific boundaries, never on
backend-neutral params. jaxtyping used selectively; shape annotations are
documentation, not runtime checks on hot paths.

**ADR-012 — uv + Hatchling for packaging.**
Hatchling build backend, PEP 621 `[project]` metadata, `dev` optional extra.
`pyproject.toml` is the only dependency declaration — no `requirements.in`.
`uv.lock` is committed as generated data. Nox sessions install with
`uv pip install -e ".[dev]"`, which is constraint-resolved, *not* lock-exact.
This supersedes ADR-009's `.venv` pass-through and `venv_backend="none"`.

**ADR-013 — Parquet authoritative, DuckDB as query engine.**
One row per run in Parquet; DuckDB queries the files directly. A `.duckdb` file
holds disposable views only. `bench/results_table.py` is the sole boundary — no
scattered pandas or ad hoc SQL. Immutable fragments written to temp then
atomically renamed; workers never share a writer. Core dimensions are typed
columns, with full validated params retained in a structured column. No Hive
partitioning until measurements justify a partition key.

**ADR-014 — Zarr format 3 for materialized arrays.**
`zarr_format=3` set explicitly; `zarr>=3,<4`. `io/zarr_store.py` is the sole
construction/opening boundary. No v2 writer, reader fallback, or dual-format
path — v2 stores are rejected with a diagnostic. Group root records a SIEVE
store-schema version (distinct from `zarr_format`), provenance, and completion
state. Sharding is a per-array layout choice, not a global default.

**ADR-015 — Long-lived workers on `multiprocessing.Process`.**
`spawn` context on every platform, explicit (`mp.get_context("spawn")`). Duplex
`Pipe` for control; versioned typed messages carrying protocol version, worker
identity, process generation, request ID, request generation.
Commands: `RUN CANCEL SHUTDOWN PING`. Events: `READY STARTED PROGRESS
COMPLETED CANCELED FAILED PONG STOPPED`. Cancellation is cooperative first
(mark stale locally → `CANCEL` → checkpoint → `CANCELED`), with termination
escalation only on crash or grace-period expiry. Results publish only when
identity + both generations match. Preview requests use latest-wins coalescing;
the GPU worker serializes.

**ADR-016 — CuPy as the only v1 GPU backend.**
Backend registry is exactly `cpu_numpy` and `gpu_cupy`. No `gpu_torch.py`, no
Torch dependency, no placeholder stub — its absence is intentional and tested.
The controller process imports and runs without CuPy or CUDA. CuPy is an
optional extra, one CUDA variant per environment. `gpu_cupy` registration is
per-filter and requires equivalence tests against the CPU implementation.
[STALE WHEN] `BACKEND_DISPATCH.md` is written — ADR-016 specifies the
12-point "add a new backend" checklist it needs to contain.

**ADR-017 — Worker JSON logs aggregated in the parent.**
Each worker gets a dedicated one-way logging connection, separate from the
ADR-015 control channel. Worker replaces `sys.stderr` with a line-buffered
adapter writing newline-delimited JSON; the parent parses and re-emits through
its own structlog sinks. Parent overwrites worker-supplied identity with
supervisor-authoritative values and preserves both worker and receive
timestamps. Bounded buffers with level-aware drop accounting; warnings, errors,
and crash evidence are never silently dropped. VizTracer CTF is a separate
artifact channel — one file per traced process generation, merged post-hoc by
`bench/tracer.py`.
[ASSUMPTION] Replacing `sys.stderr` captures Python-level writes only. Native
writes from CUDA libraries or C extensions bypass it; the ADR explicitly
declines to promise OS-level fd-2 capture.

---

## Proposed, being built against

**ADR-018 — OpenCV VideoCapture as the v1 decode path.**
One decoder for both display and executor input. It was the only candidate to
pass the seek-accuracy gate across the codec corpus; the cost is that source
bit depth above 8 bits is reduced at the decode boundary, reported at open time
and recorded in provenance rather than hidden. Decoder identity participates in
the code-version hash. `io/video_read.py` is the sole decode boundary.
[STALE WHEN] A filter needs more than 8 bits, or a seek-then-decode-forward
strategy lets a depth-preserving backend pass the gate — see the ADR's
reopening conditions.

## Decisions with no ADR yet

[OPEN QUESTION] Layer enforcement tooling (import-linter or equivalent). Named
in `SIEVE-HANDOFF.md` but covered by no ADR, and it would be a new top-level
development dependency.
