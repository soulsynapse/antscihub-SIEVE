---
title: The executor ports verbatim and honors lookahead
step: "02.3"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_executor.py tests/unit/test_stateful_execution.py -q"
opened: 2026-08-06
---

# The executor ports verbatim and honors lookahead

`pipeline/executor.py` verbatim plus the one reviewed extension: emission
delayed by declared lookahead, a centered window being warmup + lookahead
(PLAN.md, Phase 2). The extension is the only non-verbatim hunk in the diff —
anything else the diff shows is a mistake by definition. State stays minted
per run from the spec-declared factory and branching stays on declared shape,
never `tool_id` (`adr/no-kernel-apparatus.md`). New emission-delay tests join
`test_executor.py` with `lookahead` in their names.
