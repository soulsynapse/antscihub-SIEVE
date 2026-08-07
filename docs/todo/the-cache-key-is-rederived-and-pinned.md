---
title: The cache key is re-derived and its layout pinned
step: "03.4"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_cache_key.py -q"
opened: 2026-08-07
---

# The cache key is re-derived and its layout pinned

`pipeline/cache_key.py` re-derived against schema v1 under PLAN.md's
re-derivation clause. `tests/unit/test_cache_key.py` holds **9 cases in 3
classes**, and this item's table has 9 rows.

The digest changes and that is the point of doing it as a re-derivation. v2's
`node_key` folds `backend_identity(backend)` into every node digest except
where the spec claimed `backend_agnostic`; `backend/` is dropped and Phase 1
cut the declaration, so the sixth position of `_digest("node", ...)` goes
away rather than becoming a hole. Every v3 key therefore differs from its v2
counterpart, deliberately, which is why the Phase 3 gate compares products
and never keys.

What must not change is what a key *means*: `resolved_params(node,
replicate)` is what makes the key canonical per replicate rather than per
node, the identity values are frozen (`adr/tools-not-filters.md`), and no
field recorded for the user's convenience may enter — `checkpoints`,
`outputs` and `visited` are on `Project` precisely so that turning a
checkpoint off for a cluster run cannot move a key.

The layout gets a pin test in the shape `bench/budgets.py` uses: the ordered
list of positions that enter a node key, asserted character-exact, so a later
edit that adds or reorders one is visible in a diff rather than in a cache
that silently misses.
