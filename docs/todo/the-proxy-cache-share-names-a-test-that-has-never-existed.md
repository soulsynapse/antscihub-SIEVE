---
title: The proxy cache's share cites a test that has never existed, so its floor is pinned by nothing
status: awaiting-review
gated_on: nothing
priority: normal
phase: 7
done_when: "uv run pytest tests/gui/test_proxy_cache.py -q"
opened: 2026-08-08
---

# The proxy cache's share cites a test that has never existed, so its floor is pinned by nothing

`mutual/shares.PROXY_CACHE_SHARE` carries a comment saying its floor is the
cache's historical bound and that `tests/gui/test_proxy_cache.py` pins the two
numbers equal. That file has never existed in v3. The ledger was ported at 03.1,
a phase before the cache it sizes, and the citation came over with it.

The consumer landed at 07.6: `gui/transport/proxy_cache.py` declares
`DEFAULT_CAPACITY_BYTES`, and `VideoPlayer` sizes the cache from
`resolved_bytes(PROXY_CACHE_SHARE)` rather than from that default — so the two
numbers being equal is load-bearing for the ledger's arithmetic and asserted by
nothing. The cache's own behaviour is also uncovered: LRU order, byte
accounting, the eviction loop, and the refusal of an image larger than the whole
capacity all arrive with the port and are exercised only incidentally, through
the player, where a wrong answer reads as a slow scrub rather than a red test.

Either the file the comment names exists and holds both claims, or the comment
stops naming it. The first is the one worth having, and it is what `done_when`
asks for.
