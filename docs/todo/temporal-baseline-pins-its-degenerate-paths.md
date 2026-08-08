---
title: temporal_baseline pins the three paths its prose argues for and no case enters
priority: normal
phase: 8
status: open
gated_on: nothing
opened: 2026-08-07
---

# temporal_baseline pins the three paths its prose argues for and no case enters

`tests/unit/test_temporal_baseline.py` kills 31 of 47 mutants, and the three
that matter among the survivors are on branches the module documents at length:
a ring that is still filling, a frame with no variation anywhere, and a window
that is not a whole number of frames. `docs/findings/2026.08.07-temporal-baselines-documented-degenerate-paths-are-asserted-by-nothing.md`
has the sweep and the mutants that name each one.

What should be different: `filled = size` should fail, and should fail for a
reason other than luck about what the allocator returned — the finding's
allocator probe is the check that the new case actually reads an unfilled slot.
`spread > 0.0` widened to `>= 0.0` should fail, on a frame where every cell is
constant and the module's answer is zero rather than the mutant's NaN.
`math.ceil` narrowed to `math.floor` should fail, in `window_frames` and in
`ring_capacity` both, which one window that is not a whole number of frames
does for both.

The implementation is right on all three — this adds the assertions, not a fix.
Worth doing before the next stateful tool ports its window machinery from the
same v2 files, since the same fixtures get copied along with it.
