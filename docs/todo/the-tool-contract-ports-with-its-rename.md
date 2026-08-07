---
title: The tool contract ports with its rename
step: "01.2"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_tool_contract.py tests/unit/test_tool_discovery.py -q"
opened: 2026-08-06
---

# The tool contract ports with its rename

`core/tool_base.py` and `core/tool_registry.py` from v2's `filter_base.py`
and `filter_registry.py`, renamed per `adr/tools-not-filters.md` and cut to
what v3 consumes: id, version, params model, window shape (`mode`,
`stateful`, `warmup_frames`), state factory. The cut list is exhaustive —
cost estimates, `backend_agnostic`, `frame_bytes_ratio`, and the merging
protocol do not come; each returns with its consumer
(`adr/declared-means-verified.md`). Registration refuses by name anything
declared and unconsumed — a state factory without `stateful` is the worked
example (`adr/no-kernel-apparatus.md`). The v2 module docstrings are the
contract's primary source; the ported docstring is cut the same way the code
is. Tests port from `test_filter_contract.py` and `test_filter_discovery.py`
under the new names, minus cases covering cut declarations (PLAN.md, porting
discipline).
