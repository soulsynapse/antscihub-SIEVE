---
title: No kernel apparatus
adr: 2
position: "01.02"
status: settled
decided: 2026-08-06
---

A tool module is a `ToolSpec` plus one plain `run(params, window, state)`;
the spec points at it, the registry hands it to the executor, and the
executor never reaches into `ops/` directly.

Why: the alternative — the executor translating params/state/window per tool,
keyed by `tool_id` — makes adding a tool edit the one file that must not grow
with the tool count. `core/ops/` keeps its v2 role, shared math with no spec
attached, and a trivial tool's `run` is a one-line delegation into it. This
is also what dissolves v2's `backend/dispatch.py` scaffolding: a declared
version on the spec, entering the cache key, is what keeps cv2 kernels
honest instead.
