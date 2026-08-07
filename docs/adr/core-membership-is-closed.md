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
how dumping grounds grow. The name stays because every split strands
`types.py`: the four residents are the language the rest of the system
speaks, and that shared roof is a function, not looseness. What prevents
dumping is the closed door, not a better label. The same treatment lands on
`gui` at Phase 7, when its subpackage set is enumerated.
