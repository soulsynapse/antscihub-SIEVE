"""One structural check per ADR, each registered under the ADR's number.

Contracts are registered in `pyproject.toml` under `[tool.importlinter]` and
run by `uv run lint-imports` — one registry, one runner. An ADR about the
import graph uses a built-in contract type and needs no module here; any other
brings a custom contract type in `adrNNNN.py`. An ADR absent from the registry
is unchecked, not settled differently.
"""
