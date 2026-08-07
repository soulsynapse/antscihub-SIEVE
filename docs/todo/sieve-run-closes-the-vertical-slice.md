---
title: sieve run closes the vertical slice
step: "03.8"
status: open
gated_on: nothing
done_when: "uv run pytest tests/integration/test_cli_run.py -q"
opened: 2026-08-06
---

# sieve run closes the vertical slice

A minimal `sieve run` over an inline/YAML pipeline: one tool, one video, end
to end on `synthetic_video` — Phase 2's gate made a command. Port-with-rename
from v2's run command, cut to what the ported `test_cli_run.py` exercises;
the full CLI is Phase 5 and nothing beyond `run` comes now. Headless is a
contract, not a hope: the command imports no Qt, and the `.importlinter`
`headless` list already says so (00.2).
