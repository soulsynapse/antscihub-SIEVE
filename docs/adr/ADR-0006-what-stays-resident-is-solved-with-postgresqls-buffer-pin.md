---
title: Deciding what stays resident is solved with PostgreSQL's buffer pin
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

## Accepted

PostgreSQL's buffer pin — `ReadBuffer` / `ReleaseBuffer` against a pin count
per buffer descriptor, where a holder must say when it is done because
nothing about the page itself says so, and a page with a live pin cannot be
evicted whatever the replacement policy wants. That is the half this tree
kept exactly: a consumer whose output is not frame-shaped has no position to
be read as a release, so it releases by hand.

The fetch-scheduling half is `posix_fadvise(POSIX_FADV_WILLNEED)` — declaring
intent is itself what drives the read, rather than a request separate from
the plan that named it.

Settled by [derived eviction reproduces the fixed window](../findings/2026.08.30-derived-eviction-reproduces-the-fixed-window.md)
and [experiments/orchestrator-experiments/](../../experiments/orchestrator-experiments/).

## Rejected

Declaration as a pure function of position cautionary tale: the version
decided 2026-08-23 held that a declaration could be re-derived from where a
consumer stood, so that nothing could leak. The graph that works is
refcounted and a non-frame consumer needs an explicit release — falsified by
the same experiments above, which also confirmed rather than overturned that
version's refusal of the memory argument.

Memory-as-justification cautionary tale: a cap sized to fit a machine makes
retention a tuning number, and the window it produces is whatever the number
bought. Retention here is a consequence of what was declared, so a scrubbable
span is resident because something said it needed it.
