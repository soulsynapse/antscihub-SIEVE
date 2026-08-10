---
title: The solo marker's paint is read on a square grid at the fit, so two mutants of it survive
priority: normal
phase: 10
status: open
gated_on: nothing
done_when: 'uv run python scripts/mutation_sweep.py --file src/sieve/gui/canvas.py --mutant "marked = self._field.cell_rect(painted, self._solo) ==> marked = self._field.cell_rect(box, self._solo)" -- uv run pytest -q tests/gui -k soloed_block'
opened: 2026-08-10
---

# The solo marker's paint is read on a square grid at the fit, so two mutants of it survive

10.4's marker case is three grabs of a 2×2 field — bare, cell `(0, 0)` soloed,
cell `(1, 1)` soloed — asserted pairwise unequal, at the fit. Two things about
where the marker lands are invisible to that fixture, and both are live on the
shipped tree:

    $ uv run python scripts/mutation_sweep.py --file src/sieve/gui/canvas.py --mutant "marked = self._field.cell_rect(painted, self._solo) ==> marked = self._field.cell_rect(box, self._solo)" -- uv run pytest -q tests/gui
    SURVIVED  marked = self._field.cell_rect(painted, self._solo)

    $ uv run python scripts/mutation_sweep.py --file src/sieve/gui/emission_paint.py --mutant "return QRectF(xs[col], ys[row], xs[col + 1] - xs[col], ys[row + 1] - ys[row]) ==> return QRectF(xs[row], ys[col], xs[row + 1] - xs[row], ys[col + 1] - ys[col])" -- uv run pytest -q tests/gui
    SURVIVED  return QRectF(xs[col], ys[row], xs[col + 1] - xs[col], ys...

The first is the magnification hole the review of 57e43cb recorded against
`BlockField.draw` and 10.4 closed there, reproduced one line later for the same
reason: the marker is painted through the view rect, the case never magnifies,
and at the fit the two rectangles are the same. A user who has zoomed sees the
mark on a cell that is not the one they picked, while the hit test — which *is*
magnified by a case — keeps naming the right one, so the picture and the trace
disagree with each other and only the picture is wrong.

The second is the fixture: `cell_rect` is the only reader of `(row, col)` on the
paint side, the grid is square, and both soloed cells are on its diagonal, so
transposing the index is invariant over every point the case looks at. Nothing
else in the tree calls `cell_rect`.

One case answers both — a non-square grid, an off-diagonal cell, and a grab
after the wheel — and the second sweep above is what says the fixture half
landed. `done_when` runs only the first.
