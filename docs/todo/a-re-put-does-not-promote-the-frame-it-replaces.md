---
title: Re-caching a held frame does not promote it, and the line that would is a live survivor
status: open
gated_on: nothing
priority: low
phase: 7
done_when: "uv run pytest tests/gui/test_proxy_cache.py -q -k recache_promotes"
opened: 2026-08-08
---

# Re-caching a held frame does not promote it, and the line that would is a live survivor

`ProxyFrameCache.put` deletes an existing index before re-inserting it, and the
delete has exactly one observable effect: an `OrderedDict` assignment to a key
that is already present keeps that key's position, so without the delete a
re-put leaves the frame where it was in the recency order instead of moving it
to the end. `tests/gui/test_proxy_cache.py` covers the re-put's byte accounting
and stops there, so

    uv run python scripts/mutation_sweep.py \
      --file src/sieve/gui/transport/proxy_cache.py \
      --mutant "del self._entries[index] ==> pass" \
      -- uv run pytest tests/gui/test_proxy_cache.py -q

reports SURVIVED against the tree that closed
[the share's missing test file](the-proxy-cache-share-names-a-test-that-has-never-existed.md).
That item named LRU order as one of the four behaviours arriving uncovered; the
five claims it landed cover promotion on `get` and not promotion on `put`.

A re-put is what happens when a source is re-scrubbed over ground it has already
warmed, so the frames losing their recency are exactly the ones the grid keeps
returning to — the failure the LRU exists to prevent, on the path that triggers
it most. The case is put, put, re-put the first, then admit one more frame at a
capacity of two: the correct cache evicts the frame that was not re-put.
