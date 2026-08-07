---
title: The gate does not check formatting
status: open
priority: low
phase: 0
gated_on: nothing
opened: 2026-08-07
---

# The gate does not check formatting

`uv run ruff format --check .` fails on `v3` and has for at least two commits:
`src/sieve/core/tool_base.py`'s `caption_unknown` comprehension is one line
where the formatter wants three. Nothing caught it because the gate is `ruff
check && lint-imports && pytest` — the linter, not the formatter — so
`ruff format` reads the same `[tool.ruff]` line length the linter does and is
never run.

Either it joins the gate and the tree is reformatted once, or it is
deliberately not part of the contract and `pyproject.toml` says which. The state to avoid is the current one, where a contributor who
runs the formatter produces diff noise in files they did not otherwise touch.
