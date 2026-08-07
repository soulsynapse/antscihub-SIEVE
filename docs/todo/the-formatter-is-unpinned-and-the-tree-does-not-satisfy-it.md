---
title: The formatter is unpinned and the committed tree does not satisfy it
status: open
gated_on: nothing
priority: normal
opened: 2026-08-07
---

# The formatter is unpinned and the committed tree does not satisfy it

`uv run ruff format --check .` reports five files it would reformat, and every
one of them is committed and untouched by the work that found this:
`src/sieve/pipeline/executor.py`, `tests/integration/test_crop_serving.py`,
`tests/integration/test_checkpoints.py`, `tests/unit/test_crop_binding.py`,
`tests/unit/test_tool_contract.py`. The rewrites it wants are the shape a
formatter version bump produces — collapsing a wrapped call onto a line that
lands at exactly the 100-char limit, and one blank-line and one docstring-quote
change — not the shape of anyone's edit.

`pyproject.toml` lists `"ruff"` with no floor and no ceiling, so the version
that formatted these files is not the version that runs today (0.16.1 here). A
check that disagrees with the tree on a clean checkout is a check nobody can
use as a gate, and every session from here reads its output as noise it has to
decide to ignore — which is how a real formatting regression gets waved past.

What lands: the version constrained so the answer is reproducible, and the
tree made to satisfy it in one commit that touches formatting and nothing else,
so the diff of any later commit is legible. Whether the same is owed to `ruff
check` is untested — it passes today. `mypy` is worth a look while in here: it
is not installed in the dev group at all, so nothing in this repo type-checks,
which is a larger question than a formatter pin and may want its own item.
