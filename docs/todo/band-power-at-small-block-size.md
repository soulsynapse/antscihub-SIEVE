---
title: Band power at small block size
status: open
opened: 2026-07-27
gated_on: >
  nothing structurally — but it is only reachable through the wheel bug, so
  take `docs/todo/wheel-over-the-panel.md` first or the repro is by accident
reads:
  - src/sieve/gui/density_plot.py
  - src/sieve/gui/detector_worker.py
  - src/sieve/gui/filter_tab.py
---

# Band power at small block size

Noticed `<=2026.07.27` as "band power in block may randomly give out if the
block signal block number is low enough". It is not random. Three things chain.

**How it is entered.** The Block spin box (`filter_tab.py:278-279`) has range
`(0, 256)` and is a block *edge in pixels*, so scrolling it *down* multiplies
the block count. One accidental wheel notch — the exact defect in
`docs/todo/wheel-over-the-panel.md` — drops it from a comfortable value toward
1, and B goes to roughly the crop's pixel count.

**Where the time goes.** `DensityPlot.set_series`
(`src/sieve/gui/density_plot.py:80-81`) bins `(T, B)` band power into
`(96, T)` counts with an `np.add.at` scatter, and materializes
`cols = np.repeat(np.arange(T), B)` to do it. That is unbuffered scatter over
`T·B` elements, plus `T·B·8` bytes for `cols` and `T·B·4` for `idx` — 12 bytes
per (frame, block) pair, before the scatter's own cost. At B in the hundreds of
thousands that is gigabytes and seconds, and it runs **on the GUI thread**,
inside what the docstring calls "the cheap tier". The docstring's claim that
the binning "is one `np.add.at`, which is what makes a frequency-band drag
repaint this surface live" is true at the block sizes anyone means to use and
false at the ones one wheel notch away.

The scatter is replaceable by `np.bincount` over a flattened bin/frame index,
which is buffered and does not need the `cols` array at all — `cols` is a pure
repeat pattern, so the flat index is derivable arithmetically. A speedup near
8x and bit-identical output was measured during the sweep that produced this
item; that measurement was not reproduced here, so re-take it before quoting it
— and if it holds, it belongs in `docs/findings/`, not in the completed entry.

**Why it reads as "gives out" rather than "is slow".**
`DetectorWorker.compute` (`src/sieve/gui/detector_worker.py:213-216`) catches
`ValueError` and `FloatingPointError` and *returns* — no emit, no report. Its
docstring argues that a failure there is a defect in the module rather than
something a user can act on, and that a reported error would misrepresent a
merely-incomplete graph. That argument justifies not raising a modal; it does
not justify the graph going quiet with nothing said, which is rule 6 exactly:
unexamined must not render as quiet. A `MemoryError` at this size is not even
caught — it escapes and kills the pass some other way.

So: cut the scatter, and stop swallowing. ~30–60 lines.

Tests that fail for distinct reasons: `bincount` and `add.at` agree
bit-for-bit on a small `(T, B)`; a raising derivation leaves a visible notice
rather than a stale plot; and a benchmark pinning `set_series` at the reference
block count (`tests/bench/`, `pytestmark = [gui, benchmark]`) — the budget
table in `bench/budgets.py` has no producer for this surface today, and rule 4
says a ceiling nothing publishes is not a budget.

**Decided 2026-07-27: refuse at the control.** A block size whose implied B
exceeds a stated bound is rejected by the spin box, with the bound and the
reason in its tooltip — refusing over computing slowly is rule 6's preference,
and a value one wheel notch from a multi-second GUI-thread stall is not a
value the control should accept silently. The bound is coupled to the
benchmark this item already requires: the `set_series` budget in
`bench/budgets.py` is the producer, and the refusal threshold is the B that
budget is pinned at — a ceiling with a producer, per rule 4, not a magic
number in a widget. Provisional until that benchmark lands: **B <= 16,384**
(a 128x128 grid — an order of magnitude above any grid anyone tunes with,
and two below where the scatter was measured to hurt). Note the bound is on
*B*, which depends on the crop extent, so the spin box minimum is derived
per-replicate rather than constant. *Rejected side:* computing every legal
value and letting the benchmark alone guard the cost — the benchmark runs in
CI against the reference count, not against the value a wheel notch just set,
so it cannot protect the session that matters.
