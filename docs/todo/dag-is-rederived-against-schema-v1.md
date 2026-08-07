---
title: dag is re-derived against schema v1
step: "03.3"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_dag.py -q"
opened: 2026-08-07
---

# dag is re-derived against schema v1

`pipeline/dag.py` — 907 lines, the largest single module in the port —
re-derived against schema v1 (02.1) under PLAN.md's re-derivation clause: the
algorithm is copied line for line, the types are v3's, and the case table is
what stands in for "port the test file first".

`tests/unit/test_dag.py` holds **33 cases in 15 classes**, and this item's
table has 33 rows. Two things come out of the v2 signatures on the way, and
both are decisions already made rather than this item's to take: `Backend` is
a parameter of `Dag.build` and goes with `backend/`
(`adr/no-kernel-apparatus.md`), and `LoweredPrefix` goes with
`pipeline/lowering.py`, which PLAN.md does not build until a budget is missed.
A case whose subject is either of those is *dropped* citing that decision; a
case about edge legality, cycles, port wiring, or type agreement *survives*
and is the reason this module is being copied rather than rethought.

`graph_needs_chroma` is here, and the format contract it belongs to is a
separate pool item
(`the-decode-executor-format-contract-is-rederived.md`) — this item re-derives
the function, not the contract test.

The v2 deferral that produced this split is in
`findings/2026.08.07-v2s-pipeline-does-not-separate-from-its-schema.md`: the
three graph modules and the executor were one item, and 907 + 328 + 430 + 428
lines with four re-derivations under them is not one session's work.
