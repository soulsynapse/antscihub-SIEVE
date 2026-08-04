"""Band power by block: the population the count comes from, as a density.

**A histogram, not a mean line** (parity plan § 2). The detector counts
blocks whose band-power value sits inside the value band, so the graph the
user tunes that band against must show the whole population per frame — a
mean line would hide exactly the spread the count is made of. Each pixel
column is the distribution of all blocks' values at that frame, on a log1p
value axis (the noise floor and the bursts differ by orders of magnitude and
both must be placeable).

**Solo answers the opposite question.** The trace overlaid on the density is
one block's series — "what is *this* block doing" — and which block that is
belongs to the state model, not to this widget: the tab passes the already
selected column through `set_series`, so there is nothing here to go stale
when solo changes hands.

The value band handles are the base's: dragging past the top reads as
unbounded (``inf``), which for a band that *shapes a signal* is the correct
default resting state.

**There is no `MAX_BLOCKS`, deliberately** (2026-07-28,
`docs/todo/budgets-attribute-cost-they-do-not-cap-it.md`). It was 16,384 —
where the 100 ms `density_rebuild` ceiling landed *on one workstation* — and
`gui/block_spin.py` refused every block size implying more. Block count is a
scientific choice about the grain of the analysis; the HPC target has neither
that machine's clock nor that refusal's justification, and a user who wants a
256x256 grid is not making a mistake to be prevented. What made the refusal
defensible was that the binning ran on the GUI thread, where slow is frozen and
frozen is rule 6's mirror clause. It does not any more
(`gui/detector_worker.derive`), so what is left of the ceiling is an
attribution: the HUD names this span when it is the dominant cost. Slow is
acceptable; slow and unexplained is not.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import pairwise
from typing import Any

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QPointF, QRect, QRectF
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import QWidget

from sieve.gui.band_plot import ACCENT, BandPlot, argb_to_qimage, ramp_lut

FloatArray = NDArray[np.floating[Any]]

#: Cyan sequential ramp — the density's own surface, distinct from the
#: scalogram's warm one so the two heatmaps never read as one scale.
DENSITY_STOPS: tuple[tuple[int, int, int], ...] = (
    (21, 22, 25),
    (24, 56, 74),
    (32, 110, 138),
    (70, 180, 200),
    (190, 240, 248),
)

#: Vertical resolution of the histogram, in value bins.
_BINS = 96


def bin_counts(band_power: FloatArray, value_max: float, bins: int = _BINS) -> NDArray[np.float32]:
    """`(T, B)` band power binned to `(bins, T)` counts on a log1p value axis.

    Module-level and public because it is the only part of `set_series` that can
    be *wrong* — the rest is a lookup table and a blit — and asserting on a
    rendered QImage to find out is a test of the ramp pretending to be a test of
    the histogram.

    **A `bincount` per frame, not one `np.add.at` over everything.** The
    `add.at` version was the obvious vectorization and the wrong one: it is the
    unbuffered ufunc path, which is scalar-at-a-time, and it needed a column
    index *per element* to say which frame each value belonged to. At the
    reference stress workload (599 frames x 210,672 blocks, block size 1) that
    index was a 1,010 MB `intp` array built per drag tick beside a 505 MB
    `int32` of bin numbers, and the scatter alone measured **4,840 ms** against
    a 50 ms budget. Binning row by row needs no column index at all, because the
    row *is* the column, and measures **263 ms** for the same histogram. The
    loop is over frames — a few hundred — not over the hundred million values,
    so the per-iteration Python cost is noise.
    `docs/findings/2026.07.27-the-density-histogram-was-a-scatter.md`.

    Indices are clipped at *both* ends, where the `add.at` version clipped only
    the top. A NaN or a negative reaching `astype` lands somewhere
    unrepresentable, and the two paths disagree about what happens next:
    `add.at` wraps a negative index round and silently adds the value to the
    *brightest* bin, while `bincount` refuses outright. Neither is a histogram,
    so such a value is pinned to the floor before either can see it. This is a
    guard on a value the transform should not be able to produce — band power is
    a sum of squares and `block_signal`'s edge blocks always cover at least one
    real pixel — which is why flooring is acceptable here and would not be if
    the case were reachable: rendering undefined as quiet is rule 6's own
    example of the thing not to do.
    """
    m = np.asarray(band_power, np.float32)
    frames = m.shape[0]
    top = math.log1p(max(value_max, 0.0)) or 1.0
    with np.errstate(invalid="ignore"):
        # The clip below is the handling; the warning would only announce that
        # a case documented three lines up happened, once per repaint.
        idx = np.clip((np.log1p(m) / top * (bins - 1)).astype(np.int32), 0, bins - 1)
    counts = np.zeros((bins, frames), np.float32)
    for t in range(frames):
        counts[:, t] = np.bincount(idx[t], minlength=bins)
    return counts


@dataclass(frozen=True, slots=True)
class DensitySurface:
    """The picture and the axis it implies, without a widget or a `QImage`.

    Everything expensive about `DensityPlot.set_series` and nothing that needs
    the GUI thread, so it can be computed wherever the band power was — see
    `density_surface`.
    """

    #: The array's own maximum, which the value axis and the band handles are
    #: denominated in.
    value_max: float
    #: `(bins, T)` ARGB rows, already flipped so row 0 is the top of the plot.
    #: Never None: every B is binned now, however long it takes.
    argb: NDArray[np.uint32]
    #: Blocks binned, so a consumer that reports the cost can say what the cost
    #: was *for*. Carried on the surface rather than re-derived at the HUD
    #: because the array it describes does not travel that far.
    blocks: int


def density_surface(band_power: FloatArray) -> DensitySurface:
    """Bin `(T, B)` band power into the picture, off any particular thread.

    Split out of `DensityPlot.set_series` so the work can happen on the thread
    that already holds this array — `gui/detector_worker.py` computed it — and
    the GUI thread is left with a `QImage` wrap and a repaint. This is what let
    the block-count cap go: a rebuild the user waits for on the GUI thread is
    why `MAX_BLOCKS` existed, and one that is not on the GUI thread does not
    need a refusal — it needs the HUD to name what it costs.

    Nothing here touches Qt. `ramp_lut` is a numpy lookup table that happens to
    live beside Qt code; the `QImage` is deliberately *not* built here, because
    the widget is the thing that owns it and one wrap is not what costs.
    """
    m = np.asarray(band_power, np.float32)
    blocks = m.shape[1]
    value_max = float(m.max()) or 1.0
    counts = bin_counts(m, value_max)
    norm = np.log1p(counts) / math.log1p(max(blocks, 2))
    lut = ramp_lut(DENSITY_STOPS)
    return DensitySurface(
        value_max=value_max, argb=lut[(norm * 255).astype(np.uint8)][::-1], blocks=blocks
    )


class DensityPlot(BandPlot):
    """Per-frame value histogram over all blocks, with the value band on top."""

    title = "band power by block"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._image: QImage | None = None
        self._max = 1.0
        self._solo: NDArray[np.float32] | None = None
        #: The exact array `_image` was binned over. Identity, not equality —
        #: see `set_series`.
        self._source: FloatArray | None = None

    # ---- data ---------------------------------------------------------------

    def set_series(
        self,
        band_power: FloatArray,
        solo: FloatArray | None = None,
        *,
        surface: DensitySurface | None = None,
    ) -> None:
        """The `(T, B)` band power to bin, and one block's `(T,)` trace or None.

        `surface` is `density_surface(band_power)` when a caller already ran it
        off the GUI thread. Optional rather than required because the cheap
        tier hands the same array back and never reaches the binning at all.

        **The surface is rebuilt only when the array behind it moves.**
        `filter_tab`'s cheap tier — value band, count threshold, D, centered,
        solo — hands the *same* `band_power` object back on every mouse-move by
        construction: reusing it is what makes that tier cheap, and the band
        drawn on top of this surface is not part of the surface. So an identity
        check answers "is this the picture I already have", and a drag repaints
        the handles over a cached image instead of re-binning a hundred million
        values per tick. `filter_tab._heat_scale` guards a percentile over the
        same array the same way and for the same reason.

        Identity rather than equality on purpose. `np.array_equal` over `(T, B)`
        would cost within a small factor of just re-binning, so an equality
        check that succeeded would have saved nothing and one that failed would
        have doubled the work. What makes identity *sufficient* is that
        `recompute` never writes into a retained `band_power` — it either passes
        the previous array through untouched or allocates a new one — and
        `DetectorUpdate` is frozen. A future cheap tier that mutated in place
        would break this, which is why that array is documented as retained
        rather than as scratch.

        `solo` is deliberately outside the check: it changes only the overlaid
        trace, which `paint_content` draws from state on every repaint anyway.
        """
        m = np.asarray(band_power, np.float32)
        if m is not self._source:
            self._source = m
            # `surface` when the caller already paid for it off the GUI thread,
            # and only then: a caller handing a surface for a *different* array
            # would put one population's picture under another's axis, so the
            # identity check above is what makes accepting one safe.
            built = density_surface(m) if surface is None else surface
            self._max = built.value_max
            self._image = argb_to_qimage(built.argb)
        self._solo = None if solo is None else np.asarray(solo, np.float32)
        self.update()

    # ---- the value axis -------------------------------------------------

    def _fwd(self, value: float) -> float:
        return math.log1p(max(value, 0.0))

    def _inv(self, t: float) -> float:
        return math.expm1(t)

    def _range(self) -> tuple[float, float]:
        return 0.0, self._max

    # ---- painting ---------------------------------------------------------

    def paint_content(self, painter: QPainter, r: QRect) -> None:
        painter.fillRect(r, QColor(*DENSITY_STOPS[0]))
        target = self.content_rect()
        if self._image is not None and target.width() > 0:
            painter.drawImage(QRectF(target), self._image)
        if self._solo is None or self._count <= 0:
            return
        painter.setPen(QPen(ACCENT, 1.4))
        frames = len(self._solo)
        step = max(1, frames // max(r.width(), 1))
        points = [
            QPointF(self.x_of(self._start + t), self.y_of(float(self._solo[t])))
            for t in range(0, frames, step)
        ]
        for a, b in pairwise(points):
            painter.drawLine(a, b)
