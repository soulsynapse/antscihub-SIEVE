---
title: Per-tool documents are decided or dropped
priority: normal
phase: 4
status: open
gated_on: nothing
opened: 2026-08-07
---

# Per-tool documents are decided or dropped

Every Phase 4 item currently says "no per-tool `.md`, because PLAN's open
question decides that later", which works for one tool and rots across nine:
by 04.8 the question has been deferred eight times and the tools that could
have carried guidance shipped without it.

Three options, and the evidence for each is in v2. Hand-written like v2 —
they existed, `inspect` printed a path to them, and whether anyone read them
is checkable in that worktree. Generated from `ToolSpec` — the param
stereotypes (01.4) and the two-sided window (01.3) are already spec data, so
a generated page would be derived and could not drift, which is the same
argument `SCAFFOLD.md` won on. Dropped — the docstring is the contract's home
in this repo and a second home is a second thing to keep in step.

What decides it is whether there is anything true about a tool that is not
already in its spec or its docstring. If there is not, generation and
dropping are the same answer and hand-writing is the only wrong one.
