# AUTO-GUARDRAILS.md

Guardrails are enforced in CI. A violation is a blocking defect. This is meant to be automatic so problems are caught before they become a big problem.

## 1. Import Boundaries
- `core/` imports nothing from above it. No Qt, no Zarr, no subprocess.
- `pipeline/` and `bench/` import no Qt.
- `gui/` never bypasses `pipeline/` to reach `workers/` directly.
- **Check:** .importlinter rules (already exist)

## 2. Pipeline Artifact Purity
- Serialized pipeline contains no GUI-only state (panel layout, zoom, scrub position).
- A pipeline saved from GUI must load and execute identically in CLI.
- **Check:** roundtrip test — GUI serialize → CLI deserialize → execute → diff outputs

## 3. Filter Self-Registration
- A filter is one class + one colocated markdown file.
- Discovery finds it without edits to any registry, manifest, or import list.
- **Check:** test that enumerates filters via discovery and fails if any require manual wiring

## 4. Latency Budgets
- Benchmarks in `bench/budgets.py` are compared against the budget table.
- A regression is a test failure, not a known-issue.
- **Check:** `/bench/budgets.py` (already exists)

## 5. Cache Isolation
- Changing a parameter on one DAG branch does not invalidate sibling branches.
- **Check:** mutation test — alter one branch's param, assert sibling cache hits