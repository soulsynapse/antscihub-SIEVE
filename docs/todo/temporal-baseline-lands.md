---
title: temporal_baseline lands
step: "04.5"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_temporal_baseline.py -q"
opened: 2026-08-06
---

# temporal_baseline lands

`tools/temporal_baseline.py` in the ADR-2 shape, stateful, factory declared.
Parity per 02.4; kernel ports from v2 (PLAN.md, porting discipline). If its
windowed-mean machinery turns out to be what detect also needs, do not
extract it here: `ops/` admission is designed at 04.8 with both signatures
in hand (`adr/ops-admission-is-two-tools.md`).
