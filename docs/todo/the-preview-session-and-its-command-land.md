---
title: The preview session and its command land
step: "06.2"
status: open
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
Its v2 form also reaches `backend/dispatch.py` (dropped) and several
`pipeline/` modules with no disposition yet — `cache.py`,
`resolve_source.py`, `source_home.py`. What this item may not do is decide
those in passing; if the port needs one, it stops with the blocker written
down, the way 02.1 did.

The replicate argument does not come over as it stands: `core/replicates.py`
is not admitted by `adr/core-membership-is-closed.md`, which is one of the
plan's open questions.
