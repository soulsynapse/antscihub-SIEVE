---
title: Correctness is the default; performance is opt-in
adr: 11
position: "04.02"
status: settled
decided: 2026-08-06
---

The naive path is the product surface, not a fallback: every tool runs
correct-but-slow on any machine, and a fast path lands only on a measured
budget violation, at parity with what it replaces.

Why: the users are scientists and the tail is where the research is — a
pipeline a grad student runs twice and publishes from must be as trustworthy
as the hot path (`docs/archive/DESIGN-SESSION.md`, Exchanges 5 and 6).
PLAN.md's revival table is this rule applied: GPU and backend machinery
return only with a kernel measured over budget on target hardware, workers
only with a stall prefetch cannot hide. The v2.5 mechanism the invariant rode
on — the op algebra with `Opaque` as the default shape — is dissolved
([no-kernel-apparatus](no-kernel-apparatus.md)); the invariant survives the
mechanism.
