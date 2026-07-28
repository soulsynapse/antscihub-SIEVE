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

**Status note 2026-07-27: an implementation already sits uncommitted in the
working tree** (`count_plot.py` + `tests/gui/test_detect_plots.py`, from a
prior session). The decisions it embodies answer this item's open design
question and read as correct: the axis top is the tallest thing actually on
the plot — series peak unioned with the band edges, x1.06 headroom — capped
at B; zero stays the floor (rule 6: twenty blocks must not draw as nothing);
the axis freezes for the duration of a handle drag so the handle does not
chase its own rescale; nothing is latched across windows. The band-union is
the subtle one and is right: without it a threshold placed against a loud
stretch falls off the axis after a scrub to a quiet one. Remaining work is
verification, not design: run the gate, then complete by move.

~20–40 lines, `count_plot.py` only, plus its class docstring. Tests: a trace
whose maximum is far below `blocks` occupies a usable fraction of the plot; the
axis labels report the ceiling actually in force; and a single-frame detection
still survives, which is the invariant `band_plot.py:325` exists to protect.
