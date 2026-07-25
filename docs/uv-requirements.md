SIEVE — uv Requirements

## Core Dependencies

toml

`[project] dependencies = [     "numpy",     "pydantic>=2.0",     "pydantic-settings",     "pyyaml",     "typer",     "structlog",     "opencv-python-headless",     "zarr>=3.0",     "duckdb",     "pyarrow",          # Parquet read/write ]`

## Optional Extras

toml

`[project.optional-dependencies] gui = [     "PySide6",     "napari",     "pyqtgraph", ] gpu = [     "cupy", ]`

## Development Dependencies

toml

`[tool.uv.dev-dependencies] dev = [     "pytest",     "pytest-benchmark",     "hypothesis",     "nox",     "ruff",     "pyright",     "viztracer",     "py-spy",     "jaxtyping", ] dev-gui = [     "pytest-qt", ]`

## Build System

toml

`[build-system] requires = ["hatchling"] build-backend = "hatchling.build"`

---

## Quick Reference Map

|Requirement|Covers|
|---|---|
|`PySide6`|Application framework|
|`napari`|Image/video viewers|
|`pyqtgraph`|Graphs, benchmark HUD|
|`numpy`|CPU backend, NDArray typing|
|`cupy`|GPU backend (only v1 GPU path)|
|`pydantic[v2]`|Filter/pipeline models, JSON Schema gen, app config|
|`pyyaml`|Pipeline files|
|`typer`|CLI|
|`structlog`|Structured logging, JSON Lines|
|`opencv-python-headless`|Decode (VideoCapture)|
|`zarr>=3`|Materialized arrays (format 3, sharding)|
|`duckdb`|Embedded results query engine|
|`pyarrow`|Parquet analytical results|
|`ruff`|Lint + format gate|
|`pyright`|Static type checking|
|`pytest`|Test runner|
|`hypothesis`|Filter-contract property tests|
|`pytest-benchmark`|Performance regression checks|
|`nox`|Task orchestration, CI gates|
|`viztracer`|CTF phase timelines|
|`py-spy`|Live-process sampling|
|`jaxtyping`|Selective shape annotations|
|`hatchling`|Build backend|

---

**Notes:**

- `multiprocessing` (worker supervision, shared memory) is stdlib — no extra dep.
- `array-api-compat` may be needed if you want the Array API standard namespace; otherwise NumPy ≥2.0 exposes it natively.
- Hydra is explicitly deferred — not listed.
- Torch is explicitly excluded from v1 deps per ADR-016.