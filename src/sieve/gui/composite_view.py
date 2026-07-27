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

**The block grid lives here too, not in a second frame panel.** When the
composed step's output is a block grid, the pane draws v1's see-through
overlay instead of an image: every cell gets a 1 px border ring at one alpha,
and cells inside the value band right now get their interior filled at a
second, independent alpha — both in one slider-chosen signal color. Ring and
interior are disjoint pixel regions, so border alpha 0 reads as separated
blocks, and equal alphas read as one mass; that separation is the control
surface, not a rendering accident. All three grid sliders quantize to 0.2
steps so the two alphas can be matched by feel. Holding Shift peeks: every
overlay drops and the frame underneath is all there is.

**A grid click emits; it never applies.** `solo_toggled` carries the block
index (or None for un-solo) and the drawn solo marker moves only when
`set_block_state` says so — solo lives in the state model, and a widget that
painted its own click before the model confirmed it would disagree with the
density plot for a frame every time. That ordering is a tested claim,
inherited from the block-heat panel this view absorbed.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QEvent, QObject, QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QKeyEvent, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from sieve.gui.band_plot import DIM, PANEL, TEXT, plot_font

FloatArray = NDArray[np.floating[Any]]

#: Default overlay opacity. High enough that a binary mask is unmissable,
#: low enough that the input stays legible under it.
DEFAULT_OPACITY = 65

#: The grid sliders speak in 0.2 steps: 0..GRID_STEPS maps to 0.0..1.0. Coarse
#: on purpose — the separated-blocks/mass distinction needs the two alphas to
#: be *matchable*, and a continuous slider makes equal a pixel hunt.
GRID_STEPS = 5

#: Grid slider defaults, in steps: in-band fill 0.6, border 0.2, hue 0.4 —
#: the green of v1's in-band tint, which these sliders re-expose.
DEFAULT_FILL_STEP = 3
DEFAULT_LINE_STEP = 1
DEFAULT_HUE_STEP = 2

_HEADER = 22
_FOOTER = 26
_MARGIN = 6


def _signal_color(hue: float) -> QColor:
    """The overlay color for a hue slider position in [0, 1]."""
    return QColor.fromHsvF(min(max(hue, 0.0), 1.0), 0.85, 0.95)


class _CompositePane(QWidget):
    """The paint surface: base full, over at the owner's opacity, grid on top."""

    #: A block index to solo, or None to un-solo. Emitted, never self-applied.
    solo_toggled = Signal(object)
    #: The hovered block index, or None off the grid. The view's footer reads it.
    hover_changed = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.base: QImage | None = None
        self.over: QImage | None = None
        self.opacity = DEFAULT_OPACITY / 100.0
        self.notice = ""
        # The block grid overlay. `grid_on` is whether the composed step's
        # output is a block grid; the rest is the playhead's row of state.
        self.grid_on = False
        self.grid: tuple[int, int] = (1, 1)  # (ny, nx)
        self.values: NDArray[np.float32] = np.zeros(1, np.float32)
        self.in_band: NDArray[np.bool_] = np.zeros(1, bool)
        self.solo: int | None = None
        self.hover: int | None = None
        self.fill_alpha = DEFAULT_FILL_STEP / GRID_STEPS
        self.line_alpha = DEFAULT_LINE_STEP / GRID_STEPS
        self.hue = DEFAULT_HUE_STEP / GRID_STEPS
        #: Shift is held: every overlay drops so the frame can be read bare.
        self.peek = False
        self.setMouseTracking(True)
        self.setMinimumHeight(160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    # ---- geometry --------------------------------------------------------

    def _content_rect(self) -> QRectF:
        image = self.base if self.base is not None else self.over
        available = QRectF(self.rect()).adjusted(_MARGIN, 2, -_MARGIN, -2)
        if image is not None and image.height() > 0:
            aspect = image.width() / image.height()
        elif self.grid_on:
            # No frame yet but a grid to draw: letterbox at the grid's own
            # aspect so the cells stay square-ish rather than stretching.
            aspect = self.grid[1] / self.grid[0]
        else:
            return available
        width = min(available.width(), available.height() * aspect)
        height = width / aspect
        return QRectF(
            available.center().x() - width / 2.0,
            available.center().y() - height / 2.0,
            width,
            height,
        )

    def grid_rect(self) -> QRectF:
        """Where the grid paints: the same rectangle the images fill."""
        return self._content_rect()

    def block_at(self, pos: QPointF) -> int | None:
        """The block under `pos`, or None outside the grid (or with none on)."""
        if not self.grid_on:
            return None
        g = self.grid_rect()
        if not g.contains(pos) or g.isEmpty():
            return None
        ny, nx = self.grid
        col = min(int((pos.x() - g.left()) / g.width() * nx), nx - 1)
        row = min(int((pos.y() - g.top()) / g.height() * ny), ny - 1)
        return row * nx + col

    # ---- input -----------------------------------------------------------

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        hover = self.block_at(event.position())
        if hover != self.hover:
            self.hover = hover
            self.hover_changed.emit(hover)
            self.update()

    def leaveEvent(self, event: object) -> None:
        del event
        if self.hover is not None:
            self.hover = None
            self.hover_changed.emit(None)
            self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Emit the toggle; the state model decides, `set_block_state` applies."""
        if event.button() is not Qt.MouseButton.LeftButton:
            return
        block = self.block_at(event.position())
        if block is None:
            return
        self.solo_toggled.emit(None if block == self.solo else block)

    # ---- painting --------------------------------------------------------

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), PANEL)
        content = self._content_rect()
        if self.base is None and self.over is None and not self.grid_on:
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
        if self.over is not None and not self.peek:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            painter.setOpacity(self.opacity)
            painter.drawImage(content, self.over)
            painter.setOpacity(1.0)
        if self.grid_on and not self.peek:
            self._paint_grid(painter, content)
        painter.end()

    def _paint_grid(self, painter: QPainter, g: QRectF) -> None:
        """The see-through overlay: 1 px rings on every cell, fills in band.

        Ring and interior are disjoint pixel regions — the ring is the cell's
        outer pixel, the fill starts one pixel in — so the two alphas never
        composite over each other: border alpha 0 leaves 2 px of bare frame
        between neighbouring fills (separated blocks), equal alphas tile the
        in-band region seamlessly (a mass). Antialiasing stays off so a ring
        is a square ring, not a rounded smear.
        """
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        ny, nx = self.grid
        cell_w, cell_h = g.width() / nx, g.height() / ny
        color = _signal_color(self.hue)
        blocks = min(ny * nx, len(self.values), len(self.in_band))

        if self.fill_alpha > 0.0:
            fill = QColor(color)
            fill.setAlphaF(self.fill_alpha)
            for b in range(blocks):
                if not bool(self.in_band[b]):
                    continue
                row, col = divmod(b, nx)
                cell = QRectF(g.left() + col * cell_w, g.top() + row * cell_h, cell_w, cell_h)
                painter.fillRect(cell.adjusted(1.0, 1.0, -1.0, -1.0), fill)

        if self.line_alpha > 0.0:
            line = QColor(color)
            line.setAlphaF(self.line_alpha)
            painter.setPen(QPen(line, 1.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for b in range(ny * nx):
                row, col = divmod(b, nx)
                cell = QRectF(g.left() + col * cell_w, g.top() + row * cell_h, cell_w, cell_h)
                painter.drawRect(cell.adjusted(0.5, 0.5, -0.5, -0.5))

        if self.solo is not None and self.solo < ny * nx:
            row, col = divmod(self.solo, nx)
            cell = QRectF(g.left() + col * cell_w, g.top() + row * cell_h, cell_w, cell_h)
            painter.setPen(QPen(TEXT, 1.8))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(cell.adjusted(1.0, 1.0, -1.0, -1.0))


class StepCompositeView(QWidget):
    """Header, paint surface, the opacity control, and the grid controls."""

    #: A block index to solo, or None to un-solo — re-emitted from the pane.
    solo_toggled = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._caption = ""
        self._grid_caption = ""
        self._pane = _CompositePane()
        self._pane.solo_toggled.connect(self.solo_toggled)
        self._pane.hover_changed.connect(self._on_hover)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 100)
        self._slider.setValue(DEFAULT_OPACITY)
        self._slider.setFixedWidth(120)
        self._slider.setToolTip("Output opacity over the step's input")
        self._slider.valueChanged.connect(self._on_opacity)

        self._readout = QLabel(f"{DEFAULT_OPACITY}%")
        self._readout.setFont(plot_font(8))
        self._readout.setStyleSheet(f"color: {DIM.name()};")

        # The three grid controls, visible only while the grid is. Coarse
        # 0.2-step ranges on purpose — see GRID_STEPS.
        self._fill_slider = self._grid_slider(DEFAULT_FILL_STEP, "In-band fill alpha")
        self._fill_slider.valueChanged.connect(self._on_fill_alpha)
        self._line_slider = self._grid_slider(DEFAULT_LINE_STEP, "Block border alpha")
        self._line_slider.valueChanged.connect(self._on_line_alpha)
        self._hue_slider = self._grid_slider(DEFAULT_HUE_STEP, "Signal color")
        self._hue_slider.valueChanged.connect(self._on_hue)
        self._grid_tags = tuple(self._tag_label(text) for text in ("fill", "border", "color"))

        self._tag = self._tag_label("input · output")

        footer = QHBoxLayout()
        footer.setContentsMargins(_MARGIN, 0, _MARGIN, 4)
        footer.addWidget(self._tag)
        footer.addStretch(1)
        for tag, slider in zip(
            self._grid_tags,
            (self._fill_slider, self._line_slider, self._hue_slider),
            strict=True,
        ):
            footer.addWidget(tag)
            footer.addWidget(slider)
        footer.addWidget(self._slider)
        footer.addWidget(self._readout)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, _HEADER, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self._pane, 1)
        layout.addLayout(footer)
        self.setMinimumHeight(_HEADER + 160 + _FOOTER)
        self.setAutoFillBackground(False)
        self._show_grid_controls(False)

        # Shift-to-peek listens at the application so it works wherever the
        # keyboard focus happens to sit; Qt drops the filter with this object.
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def _grid_slider(self, step: int, tip: str) -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, GRID_STEPS)
        slider.setValue(step)
        slider.setFixedWidth(64)
        slider.setToolTip(f"{tip} (0 to 1 in 0.2 steps)")
        return slider

    def _tag_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setFont(plot_font(8))
        label.setStyleSheet(f"color: {DIM.name()};")
        return label

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

    def set_grid_visible(self, on: bool) -> None:
        """Whether the composed output is a block grid (draw it, arm the mouse)."""
        if on == self._pane.grid_on:
            return
        self._pane.grid_on = on
        self._show_grid_controls(on)
        self._update_tag()
        self._pane.update()

    def set_grid(self, ny: int, nx: int) -> None:
        """The block grid's shape. Cell b sits at (b // nx, b % nx)."""
        self._pane.grid = (max(ny, 1), max(nx, 1))
        self._pane.update()

    def set_block_state(
        self,
        values: FloatArray,
        in_band: NDArray[np.bool_],
        solo: int | None,
    ) -> None:
        """This playhead's `(B,)` band power, in-band mask, and the solo block."""
        self._pane.values = np.asarray(values, np.float32)
        self._pane.in_band = np.asarray(in_band, bool)
        self._pane.solo = solo
        self._pane.update()

    def set_grid_caption(self, text: str) -> None:
        """The grid footer's idle line (the hover readout replaces it)."""
        self._grid_caption = text
        self._update_tag()

    # ---- reading (for the tab and for tests) -----------------------------

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

    @property
    def pane(self) -> _CompositePane:
        """The paint surface, for tests driving grid clicks and pixels."""
        return self._pane

    @property
    def fill_slider(self) -> QSlider:
        """The in-band fill alpha control."""
        return self._fill_slider

    @property
    def line_slider(self) -> QSlider:
        """The block border alpha control — independent of the fill's."""
        return self._line_slider

    @property
    def hue_slider(self) -> QSlider:
        """The signal color control."""
        return self._hue_slider

    @property
    def peeking(self) -> bool:
        """Whether Shift currently hides every overlay."""
        return self._pane.peek

    def frames(self) -> tuple[QImage | None, QImage | None]:
        """The pair on screen, for tests asserting what arrived."""
        return self._pane.base, self._pane.over

    # ---- internals -------------------------------------------------------

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Shift-to-peek, pressed anywhere: overlays off while it is held."""
        kind = event.type()
        if (
            kind in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease)
            and isinstance(event, QKeyEvent)
            and event.key() == Qt.Key.Key_Shift
            and not event.isAutoRepeat()
        ):
            self._pane.peek = kind is QEvent.Type.KeyPress
            self._pane.update()
        return super().eventFilter(watched, event)

    def _show_grid_controls(self, on: bool) -> None:
        for tag in self._grid_tags:
            tag.setVisible(on)
        for slider in (self._fill_slider, self._line_slider, self._hue_slider):
            slider.setVisible(on)
        self._slider.setVisible(not on)
        self._readout.setVisible(not on)

    def _update_tag(self) -> None:
        if not self._pane.grid_on:
            self._tag.setText("input · output")
            return
        hover = self._pane.hover
        blocks = min(
            self._pane.grid[0] * self._pane.grid[1],
            len(self._pane.values),
            len(self._pane.in_band),
        )
        if hover is not None and hover < blocks:
            row, col = divmod(hover, self._pane.grid[1])
            state = "in band" if self._pane.in_band[hover] else "out"
            value = float(self._pane.values[hover])
            self._tag.setText(f"block ({row},{col}) — {value:.0f} — {state}")
        else:
            self._tag.setText(self._grid_caption)

    def _on_hover(self, block: object) -> None:
        del block
        self._update_tag()

    def _on_opacity(self, value: int) -> None:
        self._pane.opacity = value / 100.0
        self._readout.setText(f"{value}%")
        self._pane.update()

    def _on_fill_alpha(self, step: int) -> None:
        self._pane.fill_alpha = step / GRID_STEPS
        self._pane.update()

    def _on_line_alpha(self, step: int) -> None:
        self._pane.line_alpha = step / GRID_STEPS
        self._pane.update()

    def _on_hue(self, step: int) -> None:
        self._pane.hue = step / GRID_STEPS
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
        if self._pane.grid_on:
            title = f"{title} — CLICK TO SOLO · SHIFT PEEKS"
        painter.drawText(QRect(10, 4, self.width() - 20, 14), 0, title)
        painter.end()
