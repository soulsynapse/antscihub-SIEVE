# storage-experiments

Where SIEVE finds out how snappy the tuning loop can get *without* paying a
full transcode-and-crop first. The decode experiments settled what each file
format costs (see `../decode-experiments/2026.08.21-best-combinations.md`);
this folder measures the strategies that *avoid or defer* making those files:
RAM memoization, attention-guided background fill, lazily grown cuts,
keyframe strips, and cached analysis.

## The architecture under test

A tier stack, each layer leaning on a measured number from the decode shelf:

1. **Keyframe strip** — downscaled keyframes for instant orientation before
   anything else exists; scrub snaps to keyframes, exact on release.
2. **RAM memoization** — decoded frames in a dict, warmed by *sequential*
   background fill (the cheap rate) so scattered access (the expensive rate)
   becomes unnecessary rather than faster. Scrubs steer fill priority; they
   do not feed the store.
3. **Background cut** — a permissive-envelope lossy-intra file grown behind
   the RAM tier, persisting spans (not frames) at the level of interest,
   regenerated only ever from the original.
4. **Analysis cache** — the reduced series, invalidated only from flow
   upward; everything below the flow/threshold line recomputes live.

Frame identity is pts everywhere durable (ADR-0004). Coverage is recorded
explicitly, never inferred from an empty value.

## The rule for a result

Same as decode-experiments: the shared `harness.py` there attaches build,
machine and probed footage, keeps every per-iteration sample, and discards a
stated warm-up. Experiments here import it and repoint `RESULTS` at this
folder. Results are committed; a silently absent case reads as a case that
came out equal.

## What to measure, roughly in order

1. **Time-to-tunable**: from cold open of a region, how long until
   interactive latency reaches cut-level — transcode-first against lazy
   fill, and fill order as a policy knob (sequential vs radiating from the
   playhead).
2. **Non-disruptive generation**: background fill + encode against felt
   foreground latency as fill progresses; pausable GOP-aligned chunks.
3. **The lazily grown cut**: persisting the RAM tier to disk at the level of
   interest; what coverage tracking costs and when the swap pays.
4. **Envelope invalidation**: what a form change (crop, resolution, chroma)
   costs to re-derive, and how permissive the stored form must be for that
   to stay rare (gated on exp07's transparency numbers).

## Running

    uv run --group experiments python experiments/storage-experiments/<name>.py

Footage comes from `video-tests/` (gitignored); derived scratch files this
folder makes are temporary and cleaned up by the experiment that made them.
