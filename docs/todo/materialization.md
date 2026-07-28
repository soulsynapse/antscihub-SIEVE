---
title: Materialization, and the rule that is waiting on it
status: open
gated_on: >
  nothing — the trigger fired 2026-07-27 (a session where the render's decode
  was the whole wall clock, measured); the takeable scope is the replicate crop,
  not the general Zarr layout, and it lands with
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

**Promoted 2026.07.27 — the trigger fired, and here is the measurement.** The
condition this entry set was "a tuning session slow enough that the user wants a
compaction checkpoint." That session happened. On the reference footage the
preview decodes at 22.4 ms/frame and the player's own decode of the *same* frames
costs 22.7 ms alone and 41.9 ms while the render runs — so a 70 s window renders
in ~94 s and playback drops to 0.40x real time for the duration, with the ratio
invariant in the window length because both sides are linear in the frame count.

That is the trigger, and it also says which half to take. Every millisecond above
is decode of full-resolution frames from the source; none of it is filters, and
none of it is touched by the chunk-layout questions that make general
materialization premature. The takeable item is the **replicate crop** — a
cropped video, written once, whose access pattern is the preview loop's own —
which the sharpening below had already split out on exactly these grounds. The
general Zarr store stays where it was: still waiting on a workload that can say
what the chunking is for.

Two items filed the same day take pressure off this one without replacing it:
docs/todo/grayscale-and-the-luma-decode.md removes the colour convert (19.4 →
8.0 ms/frame of decode) and docs/todo/render-fed-playback.md stops the window
being decoded twice. Both make the decode cheaper. Only this one makes it stop
happening.

**The crop artifact's own decisions, settled 2026-07-27 so the takeable half
starts without a design stop:**

- **Lossless is not a preference, it is the identity line.** The crop is
  hashed geometry: decoding the artifact must yield byte-identical pixels to
  decoding the source and cropping, or every cache key downstream of it lies
  about what a result is. A lossy re-encode is therefore not a smaller
  version of this artifact but a *different source*, and rule 7 refuses the
  straddle. (If a lossy proxy tier is ever wanted for review on a laptop,
  it is a new identity, declared as one — a decision for review mode, not
  here.)
- **The codec inside "lossless" is a measurement, not a debate.** The access
  pattern is the preview loop's own — sequential playback plus scrubbing —
  so the test is decode throughput and seek latency under exactly that
  pattern, plus bytes on disk: FFV1 against lossless H.264 (`-qp 0`) against
  frame-array-in-Zarr, on the reference crop. Pre-stated expectations, so
  the result can surprise: FFV1 to win on size, `-qp 0` on decode speed and
  on reusing `VideoReader` unchanged, Zarr on seek but at a size that
  disqualifies it for footage. The winner is a finding; the writer cites it.
- **The artifact registers in `Project.outputs`, keyed identity-side** by
  source identity plus crop geometry (and decoder identity, exactly as
  `source_key` folds it today) — so a moved ROI misses it by construction,
  the same argument the lock item makes for cache entries. Where the file
  *lives* is location, not identity, and stays out of the hash.

**Related and settled enough to record:** compaction is user-initiated, never
automatic per step. ARCHITECTURE says so and VISION's "you can save that
representative few seconds" is a user gesture. An automatic policy would be a
second answer to the eviction question — the deferred **Cache eviction, and
spilling to disk** item, docs/todo/cache-eviction.md.

Read: `docs/SCAFFOLD.md` `pipeline/materialize.py` and `storage/`,
`src/sieve/pipeline/cache.py`, `docs/VISION.md` steps 1 and 4.
