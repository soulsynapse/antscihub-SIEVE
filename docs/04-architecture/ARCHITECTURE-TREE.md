# Architecture tree

This is the navigatable decisions made for the architecture.






* GUI
    * [PySide6 application framework](../05-adr/ADR-001-use-pyside6-for-the-ui.md)
    * [napari image and video viewers](../05-adr/ADR-001-use-pyside6-for-the-ui.md)
    * [pyqtgraph intensive graphs and benchmark HUD](../05-adr/ADR-001-use-pyside6-for-the-ui.md)

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

* Filter and pipeline contracts
    * [Pydantic v2 filter and pipeline models](../05-adr/ADR-004-use-pydantic-v2-for-the-filter-contract.md)
    * [pydantic-settings application configuration](../05-adr/ADR-004-use-pydantic-v2-for-the-filter-contract.md)
    * [YAML pipeline files](../05-adr/ADR-005-use-yaml-for-pipeline-files.md)
    * [Pydantic-generated JSON Schema](../05-adr/ADR-005-use-yaml-for-pipeline-files.md)
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
    * [VizTracer planned phase timelines](../05-adr/ADR-010-use-viztracer-and-py-spy-for-complementary-profiling.md)
    * [py-spy live-process sampling](../05-adr/ADR-010-use-viztracer-and-py-spy-for-complementary-profiling.md)
    * [Complementary profiler artifact roles](../05-adr/ADR-010-use-viztracer-and-py-spy-for-complementary-profiling.md)
