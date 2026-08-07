---
title: rescale and normalize land
step: "04.3"
status: done
gated_on: nothing
done_when: "uv run pytest tests/unit/test_rescale_normalize.py -q"
opened: 2026-08-06
---

# rescale and normalize land

`tools/rescale.py` and `tools/normalize.py`, two modules in the ADR-2 shape;
v2 covered both in one test file and that pairing ports as-is. Parity per
03.7's golden mechanism; kernels port from v2 (PLAN.md, porting discipline).
cv2 calls stay inside each tool module — duplication of a one-liner between
tools is the accepted cost (`adr/ops-admission-is-two-tools.md`).

## Reopened by review, 2026-08-07

The criterion is green and re-verified, the three goldens are byte-identical to
arrays this review regenerated out of v2 at `main` in a separate process, and
both mutants the run named do die. What a twenty-mutant sweep reached that the
run's two did not is the semantic in the first test's own name.

`test_rescale_rounds_each_extent_and_preserves_dtype` says "round(src x scale)
per axis, not floor" in its comment, and `round` replaced by `int` leaves all
twelve tests passing. No fixture in the file separates them: 101 x 0.25 is
25.25 and 53 x 0.25 is 13.25, both fractional parts under a half, so round and
floor agree; 12 x 8 at 0.05 gives 0.6 and 0.4, where `max(1, ...)` covers the
disagreement; the other two frames sit at scale 1.0 and never reach the
arithmetic. The rescale golden is the 101x53 array, so it has the same blind
spot — it pins the interpolation and not the rounding. A frame whose scaled
extent lands above the half, 6 x 6 at 0.45, separates them 3 to 2.

Three smaller survivors of the same sweep, all cheap in the same file:

| Mutant that lived | What has no case |
|---|---|
| `code = cv2.COLOR_BGR2GRAY` unconditionally | `ChannelSpec.RGB`, which `_gray_stats` branches on and nothing exercises |
| `index=frame.index` to `index=0` in `normalize.run` | normalize carrying the frame index; `rescale` asserts it and normalize does not |
| `MIN_STD` from `1e-6` to `1e-30` | the threshold's value — the constant-frame fixture has std exactly 0, so any positive cutoff passes |

The third is honest and named so the next run does not chase it: a frame with
std between those two bounds is not a thing v1's cutoff was chosen against.
`done_when` is untouched and still the file passing.
