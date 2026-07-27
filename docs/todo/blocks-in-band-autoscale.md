---
title: Blocks in band autoscale
status: open
opened: 2026-07-27
gated_on: nothing structurally — isolated, and no doctrine is disturbed
reads:
  - src/sieve/gui/count_plot.py
  - src/sieve/gui/band_plot.py
---

# Blocks in band autoscale

Noticed `<=2026.07.27`: the blocks-in-band plot caps at "inf" and, depending on
the operations applied, the trace is crushed flat against the bottom.

Both halves are one cause. `CountPlot._range` (`src/sieve/gui/count_plot.py:82-83`)
returns `(0.0, float(self._blocks))` — the total block count, unconditionally.
There is no autoscale of any kind. When a tuning produces counts in the single
digits against a grid of a few hundred blocks, the trace lives in the bottom
percent of the plot and carries no readable shape. The "inf" is not a separate
bug: it is the upper handle sitting at that fixed ceiling, formatted by
`format_value` (`count_plot.py:85-88`), which already has a branch for it.

Full-scale is a defensible default and should stay reachable — "N of M blocks"
is the quantity the plot names, and a plot that silently rescales makes two
tunings look alike when they are not. So the change is to make the ceiling
follow the data with the full-scale reading still available, not to replace one
fixed rule with another. Whatever is chosen, the axis must say which regime it
is in; an autoscaled plot that looks like a full-scale one is rule 6.

The peak to scale against should come from the same windowed array the paint
path already holds (`self._windowed`, `count_plot.py:92-94`), not from a second
pass over anything.

~20–40 lines, `count_plot.py` only, plus its class docstring. Tests: a trace
whose maximum is far below `blocks` occupies a usable fraction of the plot; the
axis labels report the ceiling actually in force; and a single-frame detection
still survives, which is the invariant `band_plot.py:325` exists to protect.
