---
title: One definition of edge legality, two consumption modes
status: open
opened: 2026-07-29
priority: normal
gated_on: nothing
reads: [src/sieve/pipeline/dag.py, src/sieve/gui/chain_model.py]
---

# One definition of edge legality, two consumption modes

`Dag.build` raises on the first bad edge — right for execution, useless for a
stack that must draw a chain a removal or a loaded file broke, which is why
`gui/chain_model.py` grew `grade`: a second spelling of edge legality, in a
widget, that drifts from the first by construction.

`Dag.validate() -> list[Diagnostic]` with per-node verdicts; `Dag.build()`
becomes validate-then-raise-on-first. One definition, two consumption modes —
fail-fast for the executor, collect-all for anything that must render a
broken graph. Not GUI-private knowledge: a batch linter over saved chain
files wants exactly the same list.

`chain_model.grade` is then deleted (with `ChainKind`, whose type distinctions
`ElementKind` and `TableSpec` already carry — the old draft's correction 3).
The GUI reads diagnostics; it does not compute them. Independent of the
protocol and schema work, and it unblocks the GUI extractions early —
`detector-state-dies` waits on it.
