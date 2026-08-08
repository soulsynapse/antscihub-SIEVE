---
title: The detection chain's two non-finite guards get the case their subject needs
priority: normal
phase: 8
status: open
gated_on: nothing
opened: 2026-08-07
---

# The two non-finite guards get the case their subject needs

`inband_count`'s `np.isfinite` and `count_band_to_counts`'s finite check are
the two survivors of 04.8's mutation sweep: delete either and all nineteen
cases across the three files still pass
(`findings/2026.08.07-the-detection-chains-non-finite-guards-survive-their-ported-cases.md`).

Both survive because the case that names their subject does not reach it. The
ported chain case feeds a NaN column and asserts the count excludes it — but
every comparison against NaN is already false, so the count excludes it either
way. The guard's live subject is an *infinite* block value under an unbounded
value band, which nothing produces. The second guard's live subject is a region
of zero elements, where `inf * 0` is NaN and the gate silently goes all-false.

Two cases, in `tests/unit/test_detect_tool.py` rather than in the ported file:
a block whose power is `+inf` against `value_band=(-inf, inf)`, and a count
band converted against zero elements. Each must fail with its guard removed —
which is the check that this item was worth doing at all.
