---
title: Rule 6's frontier moves into the execution contract
status: open
opened: 2026-07-29
priority: normal
gated_on: nothing
after: [a-kernel-that-sees-a-span, detector-state-dies]
reads: [src/sieve/gui/detector_worker.py, src/sieve/detect/detector.py]
---

# Rule 6's frontier moves into the execution contract

`settled_for` / `gate_to` — which frames of a windowed derivation are founded
and which are still warming — is rule 6's frontier, and today it is
implemented only in the GUI, which means a CLI run has no spelling of "this
stretch is unexamined". The frontier becomes part of the windowed execution
contract: the executor knows it, every front end reads it, and
unexamined-versus-quiet can finally render differently everywhere
(the standing failure `coverage-and-detection-lanes` inherits).

Mostly a relocation by the time it is reachable — the windowed protocol
(`a-kernel-that-sees-a-span`) will have stated the obligation, and this item
retires the GUI-only implementation against it.
