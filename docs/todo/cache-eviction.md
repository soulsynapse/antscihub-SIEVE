---
title: Cache eviction, and spilling to disk
status: deferred
after: [materialization]
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

**Sharpened 2026-07-27, two decisions that will already be made when this
lands:** the *bound* is not this item's to pick — it is a declared share of the resource ledger's byte budget
(docs/completed-todo/2026.07.27-resource-ledger.md), so what remains here is
only the policy (*which* entry goes when the share is full). And the first step
stays a measurement, now with a vehicle:
docs/todo/ledger-measurements.md's H4 instruments a reference
tuning session's actual footprint, which is exactly the "what a session holds"
number this file says nobody has taken — one instrumented session serves both.
Spilling remains materialization's, not eviction's: an evicted frame is
recomputable by construction (that is what the cache key means), so eviction
discards, and anything worth keeping instead goes through the user-initiated
compaction path.

**Also deferred here, for a related reason:** cache-aware lead-in shortening. A
cached upstream could in principle shorten a decode range, but only if the entry
covered the lead-in span too, which the store does not record. Slow and correct
beats fast and occasionally wrong, per `cache_key.py`'s asymmetry rule. A store
that tracked coverage would reopen the question.

Read: `src/sieve/pipeline/cache.py`, `docs/SCAFFOLD.md` `pipeline/`,
`storage/`.
