---
title: block_signal lands
step: "04.4"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_block_signal.py -q"
opened: 2026-08-06
---

# block_signal lands

`tools/block_signal.py` in the ADR-2 shape, stateful, factory declared
(`adr/no-kernel-apparatus.md`). The optical flow it computes stays private
to the module — a second tool wanting it is `ops/`'s first admission
question, answered then, not now (`adr/ops-admission-is-two-tools.md`).
Parity per 02.4; kernel ports from v2 (PLAN.md, porting discipline).
