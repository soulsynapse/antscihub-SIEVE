---
title: A declaration is a fetch plan
group: Substrate
position: 6
status: settled
decided: 2026-08-30
---

A consumer declares the positions it admits — a set, not a reach, because
sparse inputs make those different numbers — at a named form, and that
declaration is what schedules fetching. It is held until released rather
than re-derived: refcounts drop a frame when its last consumer is done, and
a consumer whose output is not frame-shaped releases explicitly, since
nothing in its own position says when it has finished with an input.
Holding is therefore the eviction rule, so anything scrubbable declares its
whole span and retention becomes a window by construction — memory was
never the justification. A re-fetch the declaration named is a defect,
counted, target zero (ADR-0008); one it could not have predicted is only a
fetch.

Replaces the version decided 2026-08-23, which held the declaration to be a
pure function of position rather than a pin-and-release protocol, so that
nothing could leak. That is the part that was wrong: the graph that works is
refcounted, and a non-frame consumer needs an explicit release. Its refusal
of the memory argument is confirmed rather than overturned. Evidence in
`docs/findings/` (2026.08.30) and `experiments/orchestrator-experiments/`.
