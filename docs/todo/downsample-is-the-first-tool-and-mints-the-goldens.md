---
title: downsample is the first tool and mints the golden mechanism
step: "03.7"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_downsample.py -q"
opened: 2026-08-06
---

# downsample is the first tool and mints the golden mechanism

`tools/downsample.py` in the ADR-2 shape — a `ToolSpec` plus one plain
`run` — and the parity mechanism every Phase-4 item reuses: v2 golden arrays
are checked into v3 under `tests/goldens/`, and each golden's test records
the exact `git -C ../antscihub-SIEVE-v2` regeneration command — the recorded
command is what keeps a checked-in golden falsifiable. (This settles PLAN's
goldens question the way its own text recommended.) Parity is v3 output
equal to the golden, not approximately equal; a tolerance is a decision this
item does not grant.
