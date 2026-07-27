"""The step composite: the selected step's output over that step's input.

This is VISION step 4's three-way overlay after REFINED-VISION collapsed it
to one view (TODO 2026.07.26). *Raw video* is not a mode — within a level the
source is what the first step's composite shows at full opacity. *Full
current state* is not a mode — with a stack that always has a selected step,
full state is the composite with the tail selected. What remains is the
contribution of the selected operation: which pixels it removed, kept, or
invented, which is spatial information no per-frame scalar plot can carry.

The widget is two images and one opacity control. `base` paints aspect-fit at
full opacity; `over` paints into the same rectangle at the slider's opacity.
It never renders anything itself: the tab hands it frames a render already
produced (`docs/findings/2026.07.25-the-crop-belongs-in-the-graph.md` — the
display path never feeds the graph).

**A block grid draws as heat with per-cell alpha, nearest-neighbour.** An
extraction step's output is a `(ny, nx)` grid, not an image; `grid_to_qimage`
colours it with the same warm stop the heat panel uses so cell heat reads as
the same quantity, and the paint keeps its edges crisp — a smoothed grid
would invent gradients between blocks that the data does not contain. The
alpha scale comes from outside (`the tab passes a percentile of the window's
series`) for the heat panel's reason: normalizing to the frame would make
every cell pulse with the loudest one.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QImage, QPainter, QPaintEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QSlider, QVBoxLayout, QWidget

from sieve.gui.band_plot import DIM, PANEL, plot_font
from sieve.gui.block_heat import HEAT

FloatArray = NDArray[np.floating[Any]]

#: Default overlay opacity. High enough that a binary mask is unmissable,
#: low enough that the input stays legible under it.
DEFAULT_OPACITY = 65

#: An overlay narrower than this is a block grid, not an image, and paints
#: nearest-neighbour so its cells stay cells.
_GRID_WIDTH_PX = 128

_HEADER = 22
_FOOTER = 26
_MARGIN = 6


def grid_to_qimage(grid: FloatArray, scale_max: float) -> QImage:
    """A `(ny, nx)` block grid as heat-coloured ARGB with per-cell alpha.

    Alpha is the cell's value against `scale_max`, clamped — the same
    fixed-scale discipline as `BlockHeatPanel.set_scale_max`, so a cell's
    visibility means the same thing at every playhead position.
    """
    values = np.asarray(grid, np.float32)
    alpha = np.clip(values / max(scale_max, 1e-12), 0.0, 1.0)
    ny, nx = values.shape
    rgba = np.empty((ny, nx, 4), np.uint8)
    rgba[..., 0] = HEAT.blue()
    rgba[..., 1] = HEAT.green()
    rgba[..., 2] = HEAT.red()
    rgba[..., 3] = (alpha * 255.0).astype(np.uint8)
    return QImage(
        np.ascontiguousarray(rgba).tobytes(), nx, ny, nx * 4, QImage.Format.Format_ARGB32
    ).copy()


class _CompositePane(QWidget):
    """The paint surface: base full, over at the owner's opacity."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.base: QImage | None = None
        self.over: QImage | None = None
        self.opacity = DEFAULT_OPACITY / 100.0
        self.notice = ""
        self.setMinimumHeight(160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def _content_rect(self) -> QRectF:
        image = self.base if self.base is not None else self.over
        available = QRectF(self.rect()).adjusted(_MARGIN, 2, -_MARGIN, -2)
        if image is None or image.height() <= 0:
            return available
        aspect = image.width() / image.height()
        width = min(available.width(), available.height() * aspect)
        height = width / aspect
        return QRectF(
            available.center().x() - width / 2.0,
            available.center().y() - height / 2.0,
            width,
            height,
        )

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), PANEL)
        content = self._content_rect()
        if self.base is None and self.over is None:
            painter.setPen(DIM)
            painter.setFont(plot_font(8))
            painter.drawText(
                self.rect(), Qt.AlignmentFlag.AlignCenter, self.notice or "no frame yet"
            )
            painter.end()
            return
        if self.base is not None:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            painter.drawImage(content, self.base)
        if self.over is not None:
            painter.setRenderHint(
                QPainter.RenderHint.SmoothPixmapTransform,
                self.over.width() >= _GRID_WIDTH_PX,
            )
            painter.setOpacity(self.opacity)
            painter.drawImage(content, self.over)
            painter.setOpacity(1.0)
        painter.end()


class StepCompositeView(QWidget):
    """Header, paint surface, and the one opacity control."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._caption = ""
        self._pane = _CompositePane()

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 100)
        self._slider.setValue(DEFAULT_OPACITY)
        self._slider.setFixedWidth(120)
        self._slider.setToolTip("Output opacity over the step's input")
        self._slider.valueChanged.connect(self._on_opacity)

        self._readout = QLabel(f"{DEFAULT_OPACITY}%")
        self._readout.setFont(plot_font(8))
        self._readout.setStyleSheet(f"color: {DIM.name()};")

        footer = QHBoxLayout()
        footer.setContentsMargins(_MARGIN, 0, _MARGIN, 4)
        tag = QLabel("input · output")
        tag.setFont(plot_font(8))
        tag.setStyleSheet(f"color: {DIM.name()};")
        footer.addWidget(tag)
        footer.addStretch(1)
        footer.addWidget(self._slider)
        footer.addWidget(self._readout)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, _HEADER, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self._pane, 1)
        layout.addLayout(footer)
        self.setMinimumHeight(_HEADER + 160 + _FOOTER)
        self.setAutoFillBackground(False)

    # ---- what it is told -------------------------------------------------

    def set_frames(self, base: QImage | None, over: QImage | None) -> None:
        """The composed pair: the step's input under, its output over."""
        self._pane.base = base
        self._pane.over = over
        self._pane.update()

    def set_caption(self, text: str) -> None:
        """The selected step's name, as the header states it."""
        if text != self._caption:
            self._caption = text
            self.update()

    def set_notice(self, text: str) -> None:
        """Why there is nothing to compose, shown only while there is nothing."""
        self._pane.notice = text
        self._pane.update()

    @property
    def caption(self) -> str:
        """The step name the header states, for tests asserting the target."""
        return self._caption

    @property
    def opacity(self) -> float:
        """The overlay opacity in [0, 1], for tests and the curious."""
        return self._pane.opacity

    @property
    def slider(self) -> QSlider:
        """The one opacity control."""
        return self._slider

    def frames(self) -> tuple[QImage | None, QImage | None]:
        """The pair on screen, for tests asserting what arrived."""
        return self._pane.base, self._pane.over

    # ---- internals -------------------------------------------------------

    def _on_opacity(self, value: int) -> None:
        self._pane.opacity = value / 100.0
        self._readout.setText(f"{value}%")
        self._pane.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), PANEL)
        painter.setPen(DIM)
        painter.setFont(plot_font(8, bold=True, spaced=True))
        title = "STEP COMPOSITE"
        if self._caption:
            title = f"{title} — {self._caption.upper()}"
        painter.drawText(QRect(10, 4, self.width() - 20, 14), 0, title)
        painter.end()
