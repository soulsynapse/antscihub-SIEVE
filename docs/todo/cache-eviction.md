---
title: Cache eviction, and spilling to disk
status: deferred
gated_on: >
  a tuning session that exhausts memory, or `materialize.py` landing —
  compaction to Zarr is where spilling belongs
reads:
  - src/sieve/pipeline/cache.py
  - docs/SCAFFOLD.md
---

# Cache eviction, and spilling to disk

**Why not now.** `MemoryFrameStore` is a dict with no bound, and a bound picked
today would be picked from nothing — no measurement exists of what a tuning
session actually holds. The protocol is in place, so the executor is already
written against the thing that will grow the policy rather than against a dict
it would have to be rewritten off.

**What would make it the right time.** A tuning session that exhausts memory,
or `materialize.py` landing — compaction to Zarr is where spilling belongs, and
an eviction policy written before it would be a second answer to where a frame
goes when it stops fitting.

**Also deferred here, for a related reason:** cache-aware lead-in shortening. A
cached upstream could in principle shorten a decode range, but only if the entry
covered the lead-in span too, which the store does not record. Slow and correct
beats fast and occasionally wrong, per `cache_key.py`'s asymmetry rule. A store
that tracked coverage would reopen the question.

Read: `src/sieve/pipeline/cache.py`, `docs/SCAFFOLD.md` `pipeline/`,
`storage/`.
