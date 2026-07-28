---
title: Materialization, and the rule that is waiting on it
status: deferred
gated_on: >
  a workload that can say what the general store's chunking is for — the
  replicate-crop half was split out 2026-07-28 (crop-artifact-writer /
  -serving / crop-boundary-gesture, takeable in order) and no longer waits
  here; "filesystem is truth at rest" returns to the rules table with the
  writer item, not with this one
reads:
  - docs/todo/crop-artifact-writer.md
  - docs/findings/2026.07.28-the-crop-artifact-is-ffv1.md
  - docs/SCAFFOLD.md
  - docs/VISION.md
---

# Materialization, and the rule that is waiting on it

**Why not now.** "Filesystem is truth *at rest*" was the first non-negotiable
and nothing in this repo has ever been at rest: `MemoryFrameStore` is a dict,
no sink writes, and `sieve run` refuses a project that declares one. So the
rule was a statement about a state the system cannot enter, which is not a
violation — during interactive tuning truth is *supposed* to live in memory —
but it did mean the rule had never been tested by anything.

**As of 2026.07.27 it is no longer stated as an invariant.** A rule that
cannot be violated cannot be relied on, and stating one in the same voice as
the enforced rules is how unbuilt guarantees read as done. It sits in
`ARCHITECTURE.md` under *Commitments not yet in force*; the
crop-artifact-writer item is now its trigger — it returns to the rules table
in the commit that lands that first writer.

VISION step 1 describes the dumbest version of the product as a folder per
transformation, and step 4's economy argument turns on "save the
representative few seconds to the child layer, and because things are
deterministic it still represents what you're trying to do". The general form
of both is `pipeline/materialize.py` growing node-output compaction plus
`storage/zarr_store.py`. Writing the store now means choosing a Zarr v3 chunk
and shard layout against zero workloads, and the layout is the whole
decision — a chunking that suits sequential playback is the wrong one for
random access by replicate, and nobody has yet run the access pattern that
would say which matters. That is what this entry still waits on.

**What left this entry on 2026.07.28.** The trigger this entry set — a
tuning session slow enough that the user wants a compaction checkpoint —
fired on 2026-07-27 with a measured session (render decode was the whole
wall clock; 0.40x playback for the render's duration), and the promoted half
was the **replicate crop**: a cropped video, written once, whose access
pattern is the preview loop's own. Its codec is measured
(docs/findings/2026.07.28-the-crop-artifact-is-ffv1.md: FFV1 on every axis,
and the qp0 route serves wrong pixels through the unchanged reader) and its
design is settled in the three split items. One settlement from 2026-07-27
did not survive contact: "lossless is not a preference, it is the identity
line" was revised 2026-07-28 to the child-source model — the artifact is a
source with its own identity rather than a byte-exact stand-in for the
parent's key — and the reversal is recorded where the decision now lives,
in docs/todo/crop-artifact-writer.md.

**What stays here.** The general store: materializing *node outputs* (the
folder-per-transformation of VISION step 1), the Zarr layout question,
spilling from the memory cache (the deferred **Cache eviction** item,
docs/todo/cache-eviction.md, names `materialize.py` as where spilling
belongs), and the node-output boundaries in the chain-stack (the deferred
**Click-through navigation** item, docs/todo/click-through-navigation.md,
keeps the descent-through-node-outputs design). The first measurement to
take when this promotes is what a session's intermediates actually weigh,
and it belongs in `docs/findings/`.

**Related and settled enough to record:** compaction is user-initiated,
never automatic per step. ARCHITECTURE says so and VISION's "you can save
that representative few seconds" is a user gesture. An automatic policy
would be a second answer to the eviction question. Note the register shift
the child-source model causes: materializing is result-*changing* (it
re-keys what sits below), so when node-output boundaries offer it, the offer
belongs in the deliberate class of the rule-7 division, not the
accept-casually class the 2026-07-27 notes assumed.

Read: `docs/SCAFFOLD.md` `storage/`, `src/sieve/pipeline/cache.py`,
`docs/VISION.md` steps 1 and 4, and the three crop items for what already
left.
