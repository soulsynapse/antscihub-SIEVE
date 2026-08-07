---
title: The preview session and its command land
step: "06.2"
status: done
gated_on: nothing
done_when: "uv run pytest tests/unit/test_preview.py tests/integration/test_cli_preview.py -q"
opened: 2026-08-07
---

# The preview session and its command land

`pipeline/preview.py` port-with-rename — a session holds everything about a
preview that does not change while a slider moves (the footage, the working
window, the store) so that a revision re-runs only what the change reached.
This is the object VISION step 4's loop is made of, and it is the reason a
budget can be measured before a widget exists.

`cli/preview_cmd.py` comes with it rather than with Phase 5's commands: it
imports `bench/budgets.py`, `bench/metrics.py` and this module, all three of
which are this phase, and it is the headless surface 06.3 measures through.
Its v2 form also reaches `backend/dispatch.py`, which is dropped, and three
modules that now land ahead of it: `pipeline/cache.py` with the executor,
`resolve_source.py` and `source_home.py` in Phase 5. The replicate it takes
is schema v1's (02.1), not v2's.
