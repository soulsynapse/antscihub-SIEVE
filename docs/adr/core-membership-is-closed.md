---
title: core's membership is closed
adr: 6
position: "03.02"
status: settled
decided: 2026-08-06
---

`core` owns exactly: the dimensioned types, the tool contract and its
registry, schema v1, and `ops/`. A new direct child is a revision of this
ADR, refused by the gate until the revision is made.

Why: core's only intrinsic claim is purity — importable by everything,
importing nothing heavy — and a constraint admits anything shared, which is
how dumping grounds grow. What prevents dumping is the closed door, not a
better label, so no top-level split: the residents already have an inside
path — one that outgrows its module becomes a subfolder here, `types.py` a
sister beside it — and the enumeration absorbs that as a rename, not a
relayering. The same treatment lands on `gui` at Phase 7, when its
subpackage set is enumerated.
