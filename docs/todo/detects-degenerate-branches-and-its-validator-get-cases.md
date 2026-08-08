---
title: detect's degenerate branches and its own validator get cases, and the two max bounds get honest prose
priority: normal
phase: 8
status: open
gated_on: nothing
opened: 2026-08-07
---

# detect's degenerate branches and its validator get cases

04.8's review swept `tools/detect.py` with an AST mutation sweep — 286 single
edits, 89 surviving the whole 445-case suite
(`findings/2026.08.07-detects-two-window-bounds-are-the-same-number-and-the-case-cannot-see-it.md`).
Most of that tail is equivalent mutants and policy constants. Four clusters are
real and one of them is prose rather than a case.

`DetectParams._ordered` is v3's own code and nothing reads it: seven mutants
survive, including `>` swapped for `>=` and the non-negative frequency check
inverted. Two cases — an unordered band and a negative `freq_band` — each
raising `ValueError`.

`morlet_band_power` carries a second, independent copy of `band_indices`' empty-band
snap, and only the first copy is tested (eight survivors). A case that calls
`morlet_band_power` with `i == j` and asserts it returns one scale's power
rather than zeros.

Band-edge inclusivity is pinned on one bound of one comparison.
`inband_count`'s `>=`/`<=` and `detect_gate`'s upper `<=` all survive: a block
sitting exactly on `lo` or on `hi` counts, and that is a claim about what the
user's dragged handle means.

`windowed_mean`'s centred lower clamp survives because the golden's count
series is flat zero across the record's head, which is exactly where the clamp
acts — the "fixture too uniform to disagree with itself" shape. The existing
ported case uses a constant series and cannot see it either. A short
non-constant series with an event at frame 0 is what reaches it.

Separately and not a case: the comment above `MAX_WARMUP_FRAMES` and
`MAX_LOOKAHEAD_FRAMES` says "the trailing shape is what makes the two differ".
Both are 1972 — the transform's reach at the legal corner dominates both window
terms — so the comment describes a distinction the constants do not have. It is
wrong rather than stale and should say what is true: the two expressions differ
and the two values do not, at this `MAX_FPS` and this `MAX_WINDOW_FRAMES`.

`detect` is also the one Phase-4 tool with no assertion on its own
`settling_epsilon`; `block_signal`, `temporal_baseline` and `motion_history`
each wrote one by hand. That belongs with
`a-tools-declaration-is-asserted-by-nothing.md` rather than here, and is noted
so the shelf-wide table knows detect is not covered by an existing per-tool case.
