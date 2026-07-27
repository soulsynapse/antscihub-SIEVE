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

Open question worth settling while here: whether a block size that implies more
than some bound on B should be refused outright at the control rather than
computed slowly. Refusing is rule 6's preference over approximating, and the
spin box's minimum is where it is cheapest to state.
