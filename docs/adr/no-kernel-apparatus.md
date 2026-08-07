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

Checked against v2 (2026-08-06): its ten filters used three of dispatch.py's
four protocols — five plain, four stateful, one windowed, zero merging, zero
GPU — all projections of the one signature; the four registration decorators
existed to catch arity mismatches this signature makes inexpressible. Two v2
lessons ride along. State is minted per run by the executor from a
spec-declared factory, never closed over — and a factory on a spec not
declaring `stateful` is refused at registration, since `stateful` is also
what denies the node a cache key. And the executor branches on declared
shape (`mode`, `stateful`), never on `tool_id`: a new *shape* — merging when
a two-port tool arrives, rate-changing — is a contract-plus-executor change,
exactly as in v2.
