---
title: Deciding what stays resident is solved with PostgreSQL's buffer pin
group: Substrate
position: 6
status: settled
decided: 2026-08-30
---

A consumer declares the positions it admits — a set, not a reach — at a named
form; that declaration schedules the fetching and is itself the hold, released
by hand where the consumer's output is not frame-shaped.

## Accepted

PostgreSQL's buffer pin — `ReadBuffer` / `ReleaseBuffer` against a pin count,
where the holder must say when it is done because nothing about the page says
so, and a pinned page cannot be evicted whatever the replacement policy wants
([derived eviction reproduces the fixed window](../findings/2026.08.30-derived-eviction-reproduces-the-fixed-window.md),
[orchestrator-experiments](../../experiments/orchestrator-experiments/)).

The fetching half is `posix_fadvise(POSIX_FADV_WILLNEED)`: declaring intent is
what drives the read, rather than a request separate from the plan that named
it.

Consequences: retention is a window by construction, since anything scrubbable
declares its whole span; and a re-fetch the declaration named is a defect
counted against zero (ADR-0008), where one it could not have predicted is only
a fetch.

## Rejected

Declaration as a pure function of position cautionary tale: the version decided
2026-08-23 held it could be re-derived from where a consumer stood so nothing
could leak, and the graph that works is refcounted with an explicit release
([derived eviction](../findings/2026.08.30-derived-eviction-reproduces-the-fixed-window.md)).

Memory-as-justification cautionary tale: a cap sized to fit a machine makes
retention a tuning number and the window whatever that number bought.
