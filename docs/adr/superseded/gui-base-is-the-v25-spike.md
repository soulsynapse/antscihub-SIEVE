---
title: The GUI's base is the v2.5 spike, not v2's gui
adr: 14
status: superseded
superseded_by: a-position-is-asked-for-in-the-chain
decided: 2026-08-06
---

`gui/` starts from the v2.5 spike's skeleton — `proto_sieve`'s `gui` and
`session` — not v2's `gui/`; v2 components port into it where they held, and
the layout operates as VISION describes.

Why: v2's `gui/` is the half whose boundaries did not hold, so re-derivation
was already the plan; the spike is a working sketch of exactly the operating
model VISION describes — the project/pipeline/step control rail with hotkey
navigation, up/down walking a spanning tree over the DAG (a choice the GUI
makes, not a fact the pipeline holds), the canvas/control split, and a
Qt-free `session/` holding undo/redo as two stacks of whole pipeline values
whose prefix reuse falls out of the executor's cache. PLAN.md Phase 7 already
cites two of its decisions; this adopts the skeleton they live in. The
adoption is `gui/` and `session/` only: the spike's kernel/resolver half is
the dissolved algebra ([no-kernel-apparatus](../no-kernel-apparatus.md)), and
its colocated `__tests__/` layout stays behind — v3's `tests/` tree is
already load-bearing. v2 parts whose contracts held — `gui/transport/`,
`gui/timeline/` — port into the skeleton, not the other way around. The
spike lives at `../antscihub-SIEVE` (branch `rewrite`) under `proto_sieve/`;
its brief continuation in v2's history (d5affef brings it over, bd72418 and
6bbb9d1 evolve the control rail into the three-position track) is off `main`
since the 2026-08 rollback and readable by hash.
