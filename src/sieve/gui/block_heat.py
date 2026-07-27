"""The block-heat panel: the frame with the grid over it, saying *where*.

On the live tab the picture's job is not to be watched — it is to say where
the signal is (parity plan § 2). So the frame draws dimmed, as context, and
the data sits on top: each cell's fill is its band power at the playhead
against a fixed scale, its outline says it is inside the value band right
now, and clicking it solos its trace in the density plot.

**The click emits; it never applies.** `solo_toggled` carries the block index
(or None for un-solo), and this widget's own solo marker moves only when
`set_state` says so — solo lives in the state model, and a widget that
painted its own click before the model confirmed it would disagree with the
density plot for a frame every time. That ordering is a tested claim.

**The fill scale is set from outside and holds still.** Normalizing to the
current frame's max would make every cell pulse with the loudest one;
`set_scale_max` (the tab passes a high percentile of the whole window's band
power) keeps a cell's brightness meaning the same thing at every playhead
position.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from sieve.gui.band_plot import ACCENT, DIM, PANEL, TEXT, plot_font

FloatArray = NDArray[np.floating[Any]]

#: The fill color at full heat — the warm ramp's bright stop, so cell heat and
#: the scalogram's surface read as the same quantity. Public because the step
#: composite colours block grids with it for the same read-as-one-quantity
#: reason.
HEAT = QColor(226, 130, 56)

#: Opacity the context frame draws at. Low: it locates, it does not compete.
_FRAME_OPACITY = 0.42

_MARGIN = 10
_HEADER = 22
_FOOTER = 22


class BlockHeatPanel(QWidget):
    """Frame + grid; fill = band power now, outline = in band, click = solo."""

    #: A block index to solo, or None to un-solo. The panel's own display
    #: does not change until `set_state` confirms it.
    solo_toggled = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._frame: QImage | None = None
        self._grid = (1, 1)  # (ny, nx)
        self._values: NDArray[np.float32] = np.zeros(1, np.float32)
        self._in_band: NDArray[np.bool_] = np.zeros(1, bool)
        self._solo: int | None = None
        self._scale_max = 1.0
        self._hover: int | None = None
        self._caption = ""
        self.setMouseTracking(True)
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    # ---- what it is told -------------------------------------------------

    def set_frame(self, frame: QImage | None) -> None:
        """The context frame at the playhead, or None before one exists."""
        self._frame = frame
        self.update()

    def set_grid(self, ny: int, nx: int) -> None:
        """The block grid's shape. Cell b sits at (b // nx, b % nx)."""
        self._grid = (max(ny, 1), max(nx, 1))
        self.update()

    def set_scale_max(self, value: float) -> None:
        """The band power that reads as full heat, fixed across the window."""
        self._scale_max = max(value, 1e-12)
        self.update()

    def set_state(
        self,
        values: FloatArray,
        in_band: NDArray[np.bool_],
        solo: int | None,
    ) -> None:
        """This playhead's `(B,)` band power, in-band mask, and the solo block."""
        self._values = np.asarray(values, np.float32)
        self._in_band = np.asarray(in_band, bool)
        self._solo = solo
        self.update()

    def set_caption(self, text: str) -> None:
        """The idle footer line (the hover readout replaces it under the mouse)."""
        self._caption = text
        self.update()

    # ---- geometry ----------------------------------------------------------

    def grid_rect(self) -> QRectF:
        """Where the grid (and frame) paints: letterboxed at the frame's aspect.

        With no frame yet, the grid's own aspect letterboxes instead — the
        cells stay square-ish rather than stretching to the widget.
        """
        available = QRectF(self.rect()).adjusted(_MARGIN, _HEADER, -_MARGIN, -_FOOTER)
        if self._frame is not None and self._frame.height() > 0:
            aspect = self._frame.width() / self._frame.height()
        else:
            aspect = self._grid[1] / self._grid[0]
        width = min(available.width(), available.height() * aspect)
        height = width / aspect
        return QRectF(
            available.center().x() - width / 2.0,
            available.center().y() - height / 2.0,
            width,
            height,
        )

    def block_at(self, pos: QPointF) -> int | None:
        """The block under `pos`, or None outside the grid."""
        g = self.grid_rect()
        if not g.contains(pos) or g.isEmpty():
            return None
        ny, nx = self._grid
        col = min(int((pos.x() - g.left()) / g.width() * nx), nx - 1)
        row = min(int((pos.y() - g.top()) / g.height() * ny), ny - 1)
        return row * nx + col

    # ---- input -------------------------------------------------------------

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._hover = self.block_at(event.position())
        self.update()

    def leaveEvent(self, event: object) -> None:
        del event
        self._hover = None
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Emit the toggle; the state model decides, `set_state` applies."""
        if event.button() is not Qt.MouseButton.LeftButton:
            return
        block = self.block_at(event.position())
        if block is None:
            return
        self.solo_toggled.emit(None if block == self._solo else block)

    # ---- painting ----------------------------------------------------------

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), PANEL)
        painter.setPen(DIM)
        painter.setFont(plot_font(8, bold=True, spaced=True))
        painter.drawText(QRect(10, 4, self.width() - 20, 14), 0, "BLOCK HEAT — CLICK TO SOLO")

        g = self.grid_rect()
        if self._frame is not None:
            painter.setOpacity(_FRAME_OPACITY)
            painter.drawImage(g, self._frame)
            painter.setOpacity(1.0)

        ny, nx = self._grid
        cell_w, cell_h = g.width() / nx, g.height() / ny
        blocks = min(ny * nx, len(self._values), len(self._in_band))
        for b in range(blocks):
            row, col = divmod(b, nx)
            cell = QRectF(g.left() + col * cell_w, g.top() + row * cell_h, cell_w, cell_h)
            heat = min(float(self._values[b]) / self._scale_max, 1.0)
            fill = QColor(HEAT)
            fill.setAlpha(int(150 * heat))
            painter.fillRect(cell.adjusted(1.0, 1.0, -1.0, -1.0), fill)
            if bool(self._in_band[b]):
                painter.setPen(QPen(ACCENT, 1.4))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(cell.adjusted(1.5, 1.5, -1.5, -1.5))
            if self._solo == b:
                painter.setPen(QPen(TEXT, 1.8))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(cell.adjusted(1.5, 1.5, -1.5, -1.5))

        painter.setPen(DIM)
        painter.setFont(plot_font(8))
        if self._hover is not None and self._hover < blocks:
            row, col = divmod(self._hover, nx)
            state = "in band" if self._in_band[self._hover] else "out"
            note = f"block ({row},{col}) — {float(self._values[self._hover]):.0f} — {state}"
        else:
            note = self._caption
        painter.drawText(QRect(10, self.height() - 18, self.width() - 20, 14), 0, note)
        painter.end()
