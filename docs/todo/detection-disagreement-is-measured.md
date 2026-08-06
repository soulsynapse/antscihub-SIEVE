---
title: How far trailing and centered detection actually disagree
status: open
opened: 2026-08-05T23:38:44-07:00
priority: high
gated_on: nothing
reads:
  - src/sieve/filters/detect.py
  - src/sieve/detect/detector.py
  - src/sieve/core/ops/detection.py
---

# How far trailing and centered detection actually disagree

Four ranked items wait behind a semantics difference nobody has measured. The
whole detector subtree — `a-kernel-that-sees-past-its-target`,
`the-detector-node-is-centered`, `detector-state-dies`,
`rule-sixs-frontier-moves-into-the-contract` — rests on the claim that
`detect_cpu`'s trailing derivation and `detect_series`' centered whole-record
one claim different events, and that claim is correct in principle and unquantified
in fact. If the disagreement is a boundary effect confined to the first and
last half-window, the migration is nearly free and the look-ahead lag is worth
almost nothing. If it is throughout, the look-ahead protocol is mandatory and
its latency cost has to be paid. Those are opposite plans and the difference
between them is one measurement.

This is also the only instrument the detector migration can ever have.
`tests/integration/test_upgrade_run.py` proved the crop and the span by
rendering a v5 fixture both ways and diffing pixels; that technique is
unavailable here because this migration changes the numbers *on purpose*, so
an equivalence test fails by construction. What replaces it is a
characterization, and it has to exist before anything can argue the migration
is acceptable rather than merely necessary.

What to run: one series, one parameter set, two derivations — `detect_series`
over the whole collected series against `detect_cpu` walked frame by frame over
spans the executor would build — and diff the *claimed intervals*, not the
gate. Interval starts, interval ends, count, and total gated frames, as a
function of position in the record. Then the same across the axes that should
move the answer: the band's lowest frequency (the cone of influence scales as
~1.369/f seconds, so 0.5 Hz and 5 Hz should differ by an order of magnitude),
`window_frames`, and whether events sit near a record boundary or in the
interior.

Synthetic first and it is not a lesser answer: a series with bursts placed at
known positions — against the cut, one half-window in, and mid-record — makes
the boundary hypothesis directly falsifiable in a way real footage cannot,
because the ground truth is the construction. `tests/conftest.py`'s
`synthetic_video` is the shape, and `PAD_EFOLDINGS`' own comment records the
same technique being used to measure wraparound (2.4% of full band-power scale
on a burst placed against the cut). Then one real recording, because a real
detector is tuned against real signal statistics and a synthetic burst is not
that.

Done looks like a finding in `docs/findings/` with the table, and one sentence
somewhere in it that a later session can act on: whether centered semantics
must survive the migration, or whether the difference is small enough and
positioned well enough that a trailing detect node is a declared change rather
than a broken promise. The items above inherit that sentence either way, and
`a-kernel-that-sees-past-its-target` should be read against it before its
latency cost is priced.
