---
title: rescale and normalize land
step: "04.3"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_rescale_normalize.py -q"
opened: 2026-08-06
---

# rescale and normalize land

`tools/rescale.py` and `tools/normalize.py`, two modules in the ADR-2 shape;
v2 covered both in one test file and that pairing ports as-is. Parity per
03.7's golden mechanism; kernels port from v2 (PLAN.md, porting discipline).
cv2 calls stay inside each tool module — duplication of a one-liner between
tools is the accepted cost (`adr/ops-admission-is-two-tools.md`).
