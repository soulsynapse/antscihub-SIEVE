"""The picture a band's handles are grabbed on, one panel per declared surface.

`graph_panel.py`'s sibling, and the difference is which channel it draws.
The graph draws a node's *output* — one value per frame, assembled by
`SeriesCollector`. This draws a node's *display surface* — many values per frame,
assembled by `SurfaceCollector` off the preview-only channel
(`adr/a-parameters-space-is-resolved-by-the-graph.md`). Two panels rather than
one with a mode, for the reason the two collectors are two classes: the thing
that must never happen is a surface being drawn as if it were something the
graph declared.

**Per surface kind, never per tool** (`adr/gui-knows-kinds-not-tools.md`). The
kind decides three things and this module holds all three in one place, because
they are one decision each way round:

- what the picture *is* — a scalogram is a field, a trace is many values per
  frame on one axis, a count is one value per frame;
- what the vertical axis is denominated in;
- and therefore whether a pair of cuts placed on it is a value the parameter can
  take.

**The third is a refusal for one of the three, and it is `RegionEditor`'s
refusal.** A `COUNT` axis is a fraction of the whole and a `TRACE` axis is the
upstream node's own units, so on both a y coordinate reads straight back as a
parameter value. A `SCALOGRAM`'s rows are the Morlet bank's, and `freq_band` is
in Hz — the column the tool fills carries the power and not the frequencies it
was taken at, so nothing here can turn a row into a number the document would
accept. Placing the editor is therefore also the decision not to offer it:
better a band the user types than handles that commit whatever the bank happened
to be indexed by. What would lift the refusal is the display channel carrying
its own axis, which is a revision of the ADR above and not a change to this
panel (`docs/todo/a-surface-carries-its-values-and-not-the-axis-they-sit-on.md`).

**Time runs across and the value runs up**, on all three, because the surfaces
sit under a graph and over a scrubber that both already read that way — and
because the handles are *horizontal* cuts, which is a claim about the axis they
are read on rather than about how a scalogram is conventionally drawn.

**Stale is labeled, not blanked**, which is `graph_panel.py`'s rule and holds
for the same reason: what is on screen answers to the parameters before the drag,
and it is the only thing the next refill can be compared against.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen, QPolygonF
from PySide6.QtWidgets import QSizePolicy, QWidget

from sieve.core.tool_base import DisplaySurface
from sieve.gui.canvas import image_of
from sieve.pipeline.series_collector import CollectedSeries

#: How much taller than the peak a data-derived value axis runs. The graph's
#: number, because the two are read side by side and a trace that breathed
#: differently from the one above it would read as a different quantity.
_HEADROOM = 1.06

_BACKGROUND = QColor(18, 18, 22)
_TRACE = QColor(120, 200, 255)
_STALE = QColor(120, 200, 255, 90)
_HINT = QColor(120, 120, 130)

#: What a panel asks for, and — unlike the graph's — also the least it will
#: accept. The graph is alone in a slot and can be squeezed to whatever is left;
#: these sit in a scrolling column between a form and an expander, where a
#: preferred height is a suggestion the layout drops to zero the moment the pane
#: is shorter than its contents. A plot at zero pixels is not a smaller plot: its
#: axis has no length, so the handles on it coincide and the gesture the surface
#: exists for has nowhere to happen. The pane scrolls, which is what makes a
#: floor affordable here and not a widget insisting on space it has not got.
_SURFACE_HEIGHT = 160

_EMPTY_HINT = "No surface yet"
_STALE_NOTICE = "stale — refilling"

#: Surfaces whose vertical axis is in the units the parameter is stored in, and
#: so the ones a pair of cuts can be committed from. Written out rather than
#: derived by excluding `SCALOGRAM`, for `SURFACES_WITHOUT_PAINTER`'s reason: a
#: fourth member would join the permissive side silently.
EDITABLE_AXIS: frozenset[DisplaySurface] = frozenset({DisplaySurface.TRACE, DisplaySurface.COUNT})


class SurfacePanel(QWidget):
    """One declared surface's picture, and the axis its handles would be read on."""

    def __init__(self, surface: DisplaySurface, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._surface = surface
        self._picture: CollectedSeries | None = None
        self._columns: NDArray[np.float32] | None = None
        self._stale = False
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(_SURFACE_HEIGHT)

    # ---- what it is handed -----------------------------------------------

    @property
    def surface(self) -> DisplaySurface:
        """Which kind of picture this is, and therefore what its axis means."""
        return self._surface

    @property
    def picture(self) -> CollectedSeries | None:
        """The columns on screen, or None before the first refill lands."""
        return self._picture

    @property
    def is_stale(self) -> bool:
        """Whether what is drawn answers to parameters that have since moved."""
        return self._stale

    @property
    def takes_handles(self) -> bool:
        """Whether a cut placed here reads back as a value the parameter takes.

        False for a scalogram — see the module docstring. A caller building an
        editor asks this rather than testing the kind, so the refusal has one
        home and moves when the channel does.
        """
        return self._surface in EDITABLE_AXIS

    def set_picture(self, picture: CollectedSeries | None) -> None:
        """Show `picture`, which is current by definition — a refill produced it."""
        self._picture = picture
        self._columns = None if picture is None else _columns(picture)
        self._stale = False
        self.update()

    def mark_stale(self) -> None:
        """The parameters under the picture have moved; a refill is on its way."""
        self._stale = True
        self.update()

    def status_text(self) -> str:
        """The line drawn over the picture, empty when it speaks for itself."""
        if self._stale:
            return _STALE_NOTICE
        if self._columns is None or self._columns.size == 0:
            return _EMPTY_HINT
        return ""

    # ---- geometry --------------------------------------------------------

    def sizeHint(self) -> QSize:
        return QSize(super().sizeHint().width(), _SURFACE_HEIGHT)

    def value_range(self) -> tuple[float, float]:
        """Floor and ceiling of the vertical axis, in that surface's own terms.

        A `COUNT` is a fraction of a whole, so its axis is zero to one and is
        *fixed*: an axis that followed the data would move the handles under a
        drag that changed nothing about what they cut. The other two are read off
        the columns, because neither the signal's units nor the bank's depth is
        knowable here.
        """
        if self._surface is DisplaySurface.COUNT:
            return 0.0, 1.0
        if self._surface is DisplaySurface.SCALOGRAM:
            rows = 0 if self._columns is None else self._columns.shape[1]
            return (0.0, float(rows)) if rows else (0.0, 1.0)
        finite = self._finite()
        if finite.size == 0:
            return 0.0, 1.0
        low = float(finite.min())
        top = low + (float(finite.max()) - low) * _HEADROOM
        return (low, top) if top > low else (low, low + 1.0)

    def x_of(self, frame: int) -> float:
        """Centre of the column `frame` occupies, or 0.0 when there is no axis.

        `graph_panel.x_of`'s rule, for its reason: the horizontal axis is the
        refill's own frames, and a panel reading the ordinal would place every
        picture at the origin.
        """
        if self._picture is None or self._columns is None or self._columns.size == 0:
            return 0.0
        offset = frame - self._picture.start_index
        return self.width() * (offset + 0.5) / self._columns.shape[0]

    def y_of(self, value: float) -> float:
        """Where `value` sits, with the axis floor on the widget's bottom edge."""
        low, top = self.value_range()
        return self.height() * (1.0 - (value - low) / (top - low))

    def value_at(self, y: float) -> float:
        """What a cut at `y` is worth, clamped to the axis.

        `y_of`'s inverse, and the whole of what an editor needs from this panel.
        Clamped rather than extrapolated because a handle dragged past the top of
        the plot means the edge of the axis, not a value the picture never showed.
        """
        low, top = self.value_range()
        if self.height() <= 0:
            return low
        return low + (top - low) * min(max(1.0 - y / self.height(), 0.0), 1.0)

    def _finite(self) -> NDArray[np.float32]:
        if self._columns is None:
            return np.empty(0, np.float32)
        return self._columns[np.isfinite(self._columns)]

    # ---- painting --------------------------------------------------------

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), _BACKGROUND)
        columns = self._columns
        if columns is not None and columns.size:
            if self._surface is DisplaySurface.SCALOGRAM:
                self._paint_field(painter, columns)
            elif self._surface is DisplaySurface.TRACE:
                self._paint_cloud(painter, columns)
            else:
                self._paint_trace(painter, columns)
        notice = self.status_text()
        if notice:
            painter.setPen(_HINT)
            painter.drawText(
                self.rect().adjusted(8, 4, -8, -4),
                int(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft),
                notice,
            )
        painter.end()

    def _paint_field(self, painter: QPainter, columns: NDArray[np.float32]) -> None:
        """The scalogram, stretched to the panel. Rows up, frames across.

        `canvas.image_of` does the greyscale mapping, which is the same one the
        viewport uses — two pictures of pipeline arrays mapped two ways would
        read as two different quantities. Flipped, because row zero is the bottom
        of an axis and the top of an image.
        """
        image = image_of(np.ascontiguousarray(columns.T[::-1]))
        if image is None:
            return
        painter.setOpacity(0.55 if self._stale else 1.0)
        painter.drawImage(QRectF(self.rect()), image)
        painter.setOpacity(1.0)

    def _paint_cloud(self, painter: QPainter, columns: NDArray[np.float32]) -> None:
        """The trace surface: every value of every frame, at its own height.

        Points and not a polyline: the values in one column are unordered — they
        are the region's blocks, and joining them would draw a shape out of
        whatever order the extractor happened to emit them in. What the band cuts
        is the set of them, which is what a cloud shows and a line does not.
        """
        painter.setPen(QPen(_STALE if self._stale else _TRACE, 1.6))
        start = 0 if self._picture is None else self._picture.start_index
        points: list[QPointF] = []
        for offset, column in enumerate(columns.tolist()):
            x = self.x_of(start + offset)
            points.extend(QPointF(x, self.y_of(value)) for value in column if np.isfinite(value))
        painter.drawPoints(QPolygonF(points))

    def _paint_trace(self, painter: QPainter, columns: NDArray[np.float32]) -> None:
        """The count surface: one value per frame, drawn the way the graph is."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(_STALE if self._stale else _TRACE, 1.6))
        start = 0 if self._picture is None else self._picture.start_index
        run: list[QPointF] = []
        for offset, value in enumerate(columns[:, 0].tolist()):
            if not np.isfinite(value):
                if run:
                    painter.drawPolyline(QPolygonF(run))
                run = []
                continue
            run.append(QPointF(self.x_of(start + offset), self.y_of(value)))
        if run:
            painter.drawPolyline(QPolygonF(run))


def _columns(picture: CollectedSeries) -> NDArray[np.float32]:
    """`picture` as `(T, N)`: one column of N values per frame.

    The tool fills a surface with an `(N, 1)` frame per frame and the collector
    stacks those, so what arrives is `(T, N, 1)` — flattened here rather than at
    the fill, because the trailing axis is the `Frame` contract's and not this
    picture's, and a tool reshaping around a panel would be the tool knowing
    about the panel.
    """
    data = np.asarray(picture.data, np.float32)
    return data.reshape(data.shape[0], -1)
