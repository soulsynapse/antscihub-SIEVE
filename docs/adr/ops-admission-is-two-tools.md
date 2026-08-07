---
title: ops admission is two tools
adr: 13
position: "01.05"
status: settled
decided: 2026-08-06
---

`core/ops/` holds only math two tools already call: single-caller math lives
in its tool module, and the package itself appears with its first two-caller
entry, gated by a census test.

Why: v2's `ops/` was, by its author's own account, stuff moved there without
much reason — and its docstring then argued the placement well enough that
only a caller census sees through it, which is the case for a gate over
prose. The census: ten callers, six of them `gui/` modules computing, all
collapsing into `tools/detect.py` once the preview is the pipeline
([one-execution-path](one-execution-path.md)) and the detector is a node
([detector-is-a-node](detector-is-a-node.md)) — so v3 starts at zero entries,
and the wavelet and detection-chain math ports into the detect tool's own
module. The n=2 bar is v2.5's catalog admission rule
(`docs/archive/DESIGN-SESSION.md`, Exchange 6): with one caller the shape is
a guess, and an entry is effectively permanent; a duplicated one-liner is the
accepted cost of waiting. Admission conditions the existing contracts already
fix, restated: numpy/scipy-pure (`core-purity` — cv2 stays beside its tool),
stateless, no spec, imported by `tools/` and tests only
([no-kernel-apparatus](no-kernel-apparatus.md)). The census test lands in the
commit that creates the package, so the gate is never younger than what it
guards.
