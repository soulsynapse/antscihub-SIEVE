---
title: Declared lookahead joins the window contract
step: "01.3"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_tool_contract.py -k lookahead -q"
opened: 2026-08-06
---

# Declared lookahead joins the window contract

`lookahead_frames` beside `warmup_frames`, same bound/refinement/cross-check
discipline — the declaration v2's trailing-only window lacked and the
detector node needs (PLAN.md, Phase 1). Contract-side only: the executor
honors it in 02.3; here it is declared, validated, and refused where it is
nonsense — negative, fractional, or set by a spec whose mode has no window.
Test names carry `lookahead` so the `-k` gate above selects exactly this
item's claim.
