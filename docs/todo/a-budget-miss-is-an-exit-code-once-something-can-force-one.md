---
title: A budget miss is an exit code once something can force one
priority: normal
phase: 6
status: open
gated_on: nothing
opened: 2026-08-07
---

# A budget miss is an exit code once something can force one

v2's `sieve preview --check` exited non-zero when any recorded sample missed
its ceiling, which is what turns "a budget is a defect, not a tradeoff" into
something a script can act on. 06.2 landed the command without it, for
`adr/declared-means-verified.md`'s reason and not for want of a use: the branch
that matters is the *miss*, and nothing in this repo can make a real clock
exceed 100 ms on demand, so the flag would have shipped with only its passing
side ever exercised — and a gate that only ever passes is the failure the whole
budget table exists to refuse.

What unblocks it is a way to drive a miss deterministically. `MetricBus` already
takes an injectable `clock`, so the shape is probably that the command accepts a
bus rather than constructing one and a test hands it a fake — which is a
question about who owns the bus, not about the flag, and should be answered
before the flag returns rather than by it.

Until then the miss is visible and not actionable: `_timings` prints a
`MISS by N ms` suffix, `tests/integration/test_cli_preview.py` covers that
suffix by feeding a `Recorder` directly, and the gate that judges
`slider_to_preview` and `full_preview_render` is 06.3's benchmark against
`bench/budgets.py`.
