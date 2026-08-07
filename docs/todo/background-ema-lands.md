---
title: background_ema lands
step: "04.6"
status: done
gated_on: nothing
done_when: "uv run pytest tests/unit/test_background_ema.py -q"
opened: 2026-08-06
---

# background_ema lands

`tools/background_ema.py` in the ADR-2 shape, stateful, factory declared —
state minted per run by the executor, never closed over
(`adr/no-kernel-apparatus.md`). Parity per 03.7; kernel ports from v2
(PLAN.md, porting discipline).
