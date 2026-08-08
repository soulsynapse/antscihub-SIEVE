---
title: temporal_baseline's declared epsilon is run by nothing, and its own assertion is a restatement
priority: normal
phase: 8
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_temporal_baseline.py -k two_runs_meeting_at_a_frame_agree_to_within_the_declared_epsilon -q"
opened: 2026-08-08
---

# temporal_baseline's declared epsilon is run by nothing, and its own assertion is a restatement

`SETTLED_EPSILON = 100.0` was measured (`findings/2026.08.08-temporal-baselines-two-runs-disagree-by-more-than-a-detection-threshold.md`),
and the measurement was taken in a scratch harness that was not committed. In
the tree it is now read by three things: `ToolSpec.__post_init__`, which checks
only that it is not zero; `cache_key`'s refusal string, which prints it; and
`inspect_cmd`, which prints it. Nothing runs it. The other two tools that
declare an epsilon do not have this shape — `background_ema` and
`motion_history` both feed theirs to `settle_frames()`, which is what derives
`warmup_frames`, so a wrong epsilon there moves a number the plan reads.
`adr/declared-means-verified.md` is the standard this fails: a declaration is
consumed by running machinery or refused by name at registration, and a
registration check that cannot tell 100.0 from 1.0 is standing in for a
consumer that does not exist. Change `_floored`'s substitution and the true
divergence can move two orders of magnitude with nothing going red.

`test_the_declared_warmup_is_the_worst_case_over_the_legal_range` looks like
the missing check and is not. Its `assert SPEC.settling_epsilon == 0.0` was a
literal pin; it now reads `== SETTLED_EPSILON`, and `SPEC` is constructed from
`SETTLED_EPSILON` twenty lines earlier, so both sides move together and the
line holds at 100.0, at 1.0, and at 0.0 — where zero would already have been
refused at import by the new contract check, which is the only reason the
declaration is guarded at all.

What should be different: the divergence probe in the finding becomes a case,
in `background_ema`'s shape — `test_the_declared_warmup_is_the_worst_case...`'s
sibling there runs two seeds two hundred levels apart and asserts they converge
to within the declared epsilon, which is why that constant is not a
restatement. Here that is two runs entered at offsets spanning one sample
stride over one configuration, compared per cell past both warmups, asserting
the maximum is under `SPEC.settling_epsilon`. One configuration and a small
frame count is enough; the finding holds the sweep and this holds the claim.
The case must be able to fail on a number, so it reads `SPEC.settling_epsilon`
on one side and array data on the other, never the constant on both.

Worth taking with `temporal-baseline-pins-its-degenerate-paths.md` if that one
runs first — both add cases to the same file, and the ring-filling fixture that
item needs is most of the entered-at-an-offset fixture this one needs.
