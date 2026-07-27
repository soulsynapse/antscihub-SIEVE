---
title: Materialization, and the rule that is waiting on it
status: deferred
gated_on: >
  a tuning session slow enough that the user wants a compaction checkpoint —
  downstream of the preview loop in `TODO.md`; lands as one item with
  docs/todo/click-through-navigation.md
reads:
  - docs/SCAFFOLD.md
  - src/sieve/pipeline/cache.py
  - docs/VISION.md
---

# Materialization, and the rule that is waiting on it

**Why not now.** "Filesystem is truth *at rest*" was the first non-negotiable and
nothing in this repo has ever been at rest: `MemoryFrameStore` is a dict, no
sink writes, and `sieve run` refuses a project that declares one. So the rule was
a statement about a state the system cannot enter, which is not a violation —
during interactive tuning truth is *supposed* to live in memory — but it did mean
the rule had never been tested by anything.

**As of 2026.07.27 it is no longer stated as an invariant.** A rule that cannot
be violated cannot be relied on, and stating one in the same voice as the
enforced rules is how unbuilt guarantees read as done. It now sits in
`ARCHITECTURE.md` under *Commitments not yet in force*, and this entry is its
trigger: it returns to the rules table in the commit that lands the first writer.
Rule 1 is now "one execution path", which is enforced and was previously unnamed.

VISION step 1 describes the dumbest version of the product as a folder per
transformation, and step 4's economy argument turns on "save the representative
few seconds to the child layer, and because things are deterministic it still
represents what you're trying to do". Both are `pipeline/materialize.py` plus
`storage/zarr_store.py`. Writing them now means choosing a Zarr v3 chunk and
shard layout against zero workloads, and the layout is the whole decision — a
chunking that suits sequential playback is the wrong one for random access by
replicate, and nobody has yet run the access pattern that would say which
matters.

**What would make it the right time.** A tuning session slow enough that the
user wants a compaction checkpoint — which is downstream of the preview loop in
`TODO.md`, because until previews are re-run interactively there is nothing to
buy back. The first measurement to take is what a session's intermediates
actually weigh, and it belongs in `docs/findings/`.

**Sharpened 2026.07.27:** the writer and the deferred **Click-through
navigation** item, docs/todo/click-through-navigation.md, are one item
approached from both ends — the descent gesture is the user initiation this
entry already required, so neither waits on the other. And the replicate crop
should be split out from the general Zarr question when that item is taken: its
format is a cropped video, its access pattern is the preview loop's own
(sequential playback plus scrubbing), and the decode-budget finding argues its
trigger is already met — none of the chunk-layout unknowns that make general
materialization premature apply to it.

**Related and settled enough to record:** compaction is user-initiated, never
automatic per step. ARCHITECTURE says so and VISION's "you can save that
representative few seconds" is a user gesture. An automatic policy would be a
second answer to the eviction question — the deferred **Cache eviction, and
spilling to disk** item, docs/todo/cache-eviction.md.

Read: `docs/SCAFFOLD.md` `pipeline/materialize.py` and `storage/`,
`src/sieve/pipeline/cache.py`, `docs/VISION.md` steps 1 and 4.
