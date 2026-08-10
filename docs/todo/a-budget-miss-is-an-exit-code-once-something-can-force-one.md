---
title: A budget miss is an exit code once something can force one
priority: normal
phase: 8
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

A fake clock would also close a hole the same benchmark now has. `f1bc0fd`
rewired `Reading.misses()` from the fixture's narrowed per-gate map onto
`Reading.published`, the run's whole series — the whole point of
[the-per-sample-gate-sees-every-sample-the-run-published.md](the-per-sample-gate-sees-every-sample-the-run-published.md)
— and the review's mutant putting it back onto `gated` survived the entire
module. It survives because `assert not missed` is an empty expectation over a
healthy clock: no sample misses either way, so nothing distinguishes the two
collections. The new gate's count assertions pin that `published` is whole, not
that `misses()` is the thing reading it. What would kill the mutant is a
`Reading` carrying one over-ceiling sample in a position the clears drop, which
is the same fake-clock capability this item is waiting on and wants the same
answer about who owns the bus. Doing it here is cheaper than twice
([findings/loop/2026.08.07-a-live-gate-asserting-a-collector-is-empty-passes-for-a-collector-that-collects-nothing.md](../findings/loop/2026.08.07-a-live-gate-asserting-a-collector-is-empty-passes-for-a-collector-that-collects-nothing.md)).

The same seam runs the other way on the band surface, and there it is not
hypothetical: `test_every_band_drag_the_session_published_is_gated` was red in
one whole-suite run and green in the next with nothing under it changed
([findings/2026.08.10-the-band-drags-per-sample-gate-is-red-under-a-full-suite-and-green-alone.md](../findings/2026.08.10-the-band-drags-per-sample-gate-is-red-under-a-full-suite-and-green-alone.md)).
So a live clock is not only a gate that cannot be made to miss — it is a gate
that misses for reasons the code under it does not own, which costs a session a
diagnosis every time it fires. Whoever answers who owns the bus should treat the
bench fixtures as a caller too, not just the `--check` flag: an injected clock
that can force a miss is the same capability as one that can refuse a miss the
scheduler caused.
