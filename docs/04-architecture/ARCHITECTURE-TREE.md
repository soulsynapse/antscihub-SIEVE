# Architecture tree

This is the navigatable decisions made for the architecture.






* GUI
    * [PySide6 application framework](../05-adr/ADR-001-use-pyside6-for-the-ui.md)
    * [napari image and video viewers](../05-adr/ADR-001-use-pyside6-for-the-ui.md)
    * [pyqtgraph intensive graphs and benchmark HUD](../05-adr/ADR-001-use-pyside6-for-the-ui.md)

* Worker execution
    * [Long-lived subprocess compute workers](../05-adr/ADR-002-use-subprocess-workers-and-shared-memory-for-frames.md)
    * [Named shared-memory frame transport](../05-adr/ADR-002-use-subprocess-workers-and-shared-memory-for-frames.md)
    * [multiprocessing.Process worker supervision](../05-adr/ADR-015-manage-long-lived-workers-with-multiprocessing-process.md)
    * [Cooperative cancellation and termination escalation](../05-adr/ADR-015-manage-long-lived-workers-with-multiprocessing-process.md)
    * [Versioned bidirectional worker protocol](../05-adr/ADR-015-manage-long-lived-workers-with-multiprocessing-process.md)

* Development quality
    * [Ruff Python linting and formatting gate](../05-adr/ADR-003-adopt-ruff-as-the-python-quality-gate.md)
    * [Pyright remains the static type checker](../05-adr/ADR-003-adopt-ruff-as-the-python-quality-gate.md)
    * [pytest test runner and fixtures](../05-adr/ADR-008-use-pytest-hypothesis-and-pytest-benchmark.md)
    * [Hypothesis filter-contract properties](../05-adr/ADR-008-use-pytest-hypothesis-and-pytest-benchmark.md)
    * [pytest-benchmark performance regression checks](../05-adr/ADR-008-use-pytest-hypothesis-and-pytest-benchmark.md)
    * [Fast and slow test tiers](../05-adr/ADR-008-use-pytest-hypothesis-and-pytest-benchmark.md)
    * [Nox task orchestration](../05-adr/ADR-009-use-nox-for-task-orchestration.md)
    * [Composed local and CI quality gates](../05-adr/ADR-009-use-nox-for-task-orchestration.md)
    * [Conditional CUDA and GL sessions](../05-adr/ADR-009-use-nox-for-task-orchestration.md)

* Packaging and environments
    * [uv and Hatchling packaging](../05-adr/ADR-012-use-uv-and-hatchling-for-packaging.md)
    * [pyproject.toml as the sole dependency declaration](../05-adr/ADR-012-use-uv-and-hatchling-for-packaging.md)
    * [Qt and the GPU backend as optional extras](../05-adr/ADR-019-split-qt-and-gpu-into-optional-extras.md)
    * [pytest-qt confined to the dev-gui extra](../05-adr/ADR-019-split-qt-and-gpu-into-optional-extras.md)

* Decode
    * [OpenCV VideoCapture as the pinned v1 decoder](../05-adr/ADR-018-pin-opencv-videocapture-as-the-v1-decode-path.md)
    * [Seek accuracy chosen over source bit-depth preservation](../05-adr/ADR-018-pin-opencv-videocapture-as-the-v1-decode-path.md)
    * [Decoder identity inside the code-version hash](../05-adr/ADR-018-pin-opencv-videocapture-as-the-v1-decode-path.md)

* Filter and pipeline contracts
    * [Pydantic v2 filter and pipeline models](../05-adr/ADR-004-use-pydantic-v2-for-the-filter-contract.md)
    * [pydantic-settings application configuration](../05-adr/ADR-004-use-pydantic-v2-for-the-filter-contract.md)
    * [YAML pipeline files](../05-adr/ADR-005-use-yaml-for-pipeline-files.md)
    * [Pydantic-generated JSON Schema](../05-adr/ADR-005-use-yaml-for-pipeline-files.md)
    * [CuPy as the only v1 GPU backend](../05-adr/ADR-016-use-cupy-as-the-only-v1-gpu-backend.md)
    * [No speculative Torch backend or dependency](../05-adr/ADR-016-use-cupy-as-the-only-v1-gpu-backend.md)
    * [Isolated worker for a future required Torch backend](../05-adr/ADR-016-use-cupy-as-the-only-v1-gpu-backend.md)
    * [Zarr format 3 materialized arrays](../05-adr/ADR-014-use-zarr-format-3-for-materialized-arrays.md)
    * [Workload-specific Zarr v3 sharding](../05-adr/ADR-014-use-zarr-format-3-for-materialized-arrays.md)
    * [No internal Zarr v2 compatibility path](../05-adr/ADR-014-use-zarr-format-3-for-materialized-arrays.md)
    * [Array API-compatible portable filter kernels](../05-adr/ADR-011-use-array-api-compatible-filter-code-and-numpy-typing.md)
    * [NumPy-specific NDArray typing](../05-adr/ADR-011-use-array-api-compatible-filter-code-and-numpy-typing.md)
    * [Selective jaxtyping shape annotations](../05-adr/ADR-011-use-array-api-compatible-filter-code-and-numpy-typing.md)

* CLI and configuration
    * [Typer command-line interface](../05-adr/ADR-006-use-typer-and-pydantic-settings-for-cli-configuration.md)
    * [Configuration ownership and precedence](../05-adr/ADR-006-use-typer-and-pydantic-settings-for-cli-configuration.md)
    * [Defer Hydra pending complex sweep requirements](../05-adr/ADR-006-use-typer-and-pydantic-settings-for-cli-configuration.md)

* Observability and benchmarking
    * [structlog structured application logging](../05-adr/ADR-007-use-structlog-for-structured-logging.md)
    * [JSON Lines logs queryable with DuckDB](../05-adr/ADR-007-use-structlog-for-structured-logging.md)
    * [Separate logs, benchmark results, metrics, and traces](../05-adr/ADR-007-use-structlog-for-structured-logging.md)
    * [Parent aggregation of worker JSON logs](../05-adr/ADR-017-aggregate-worker-json-logs-in-the-parent.md)
    * [Dedicated per-worker stderr bridge](../05-adr/ADR-017-aggregate-worker-json-logs-in-the-parent.md)
    * [Separate per-process CTF files and post-hoc merge](../05-adr/ADR-017-aggregate-worker-json-logs-in-the-parent.md)
    * [Parquet as the authoritative analytical results dataset](../05-adr/ADR-013-use-duckdb-over-parquet-for-analytical-results.md)
    * [DuckDB as the embedded results query engine](../05-adr/ADR-013-use-duckdb-over-parquet-for-analytical-results.md)
    * [Immutable HPC result fragments and explicit compaction](../05-adr/ADR-013-use-duckdb-over-parquet-for-analytical-results.md)
    * [VizTracer planned phase timelines](../05-adr/ADR-010-use-viztracer-and-py-spy-for-complementary-profiling.md)
    * [py-spy live-process sampling](../05-adr/ADR-010-use-viztracer-and-py-spy-for-complementary-profiling.md)
    * [Complementary profiler artifact roles](../05-adr/ADR-010-use-viztracer-and-py-spy-for-complementary-profiling.md)
