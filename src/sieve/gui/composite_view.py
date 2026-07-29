"""The step composite: the selected step's output over that step's input.

*Raw video* is not a mode — within a level the
source is what the first step's composite shows at full opacity. *Full
current state* is not a mode — with a stack that always has a selected step,
full state is the composite with the tail selected. What remains is the
contribution of the selected operation: which pixels it removed, kept, or
invented, which is spatial information no per-frame scalar plot can carry.

The widget is two images and one opacity control. `base` paints aspect-fit at
full opacity; `over` paints into the same rectangle at the slider's opacity.
It never renders anything itself: the tab hands it frames already produced.
Feeding display output back into the graph would create a second computation path.

**The block grid lives here too, not in a second frame panel.** When the
composed step's output is a block grid, the pane draws the grid itself
rather than compositing an image. Two layers, one quantity each. Under
everything sits the heatmap: every cell coloured cold-to-hot (v1's turbo
read) by its band power at the playhead against a fixed outside-set scale —
`set_scale_max`'s discipline, so a cell's colour means the same thing at
every playhead position — at one slider-set layer alpha. On top, cells
inside the value band right now get an interior fill at one alpha and a
1 px border ring at a second, independent alpha, both in `ACCENT`, the
palette's one in-band colour. The ring belongs to *detected* cells only; an
out-of-band cell is bare heat. One pixel is the width of every wall, the
shared ones included: two adjacent detected cells split a single line rather
than laying a ring each, so the interior of a detected region — the least
informative part of the picture — does not get the heaviest ink. Ring and
interior are disjoint pixel regions, so border alpha 0 reads as separated
blocks and equal alphas read as one mass; that separation is the control
surface, not a rendering accident. All
three grid sliders quantize to 0.2 steps so the two alphas can be matched by
feel. Holding Shift peeks: every overlay drops and the frame underneath is
all there is.

**The wheel magnifies, and the grid is magnified with the picture.** Blocks
are the size of the biology, so at a realistic block count a cell is a few
screen pixels and the overlay is unreadable at the fit. The magnifier is
`gui/zoom.Magnifier`, the same one the replicate tab's viewport uses, and the
reason it is shared is that the pane and that viewport now have one mapping
rule between them: `_content_rect` is the fit and only the floor the view is
clamped against, `view_rect` is where everything paints. *Everything* — the
two images and the grid go into the same rectangle, so registration between
cell and pixel is not maintained at every zoom so much as unable to come
apart. Hit-testing reads that rectangle too, and additionally refuses points
outside the fit: a magnified grid extends under the letterbox, where nothing
is painted, and a click on bare panel must not solo the cell that would have
been there.

**Hover solos, click pins.** The block under the pointer is soloed as the
pointer moves, and a click *latches* one so it survives the pointer leaving
the grid — `leaveEvent` reverts to the latched block, or to none. The reason
hover is enough is that the point of soloing is to look at the *trace*, which
is drawn in the density plot rather than here: a rule where solo is strictly
the block under the pointer would destroy the thing it was asked for at the
instant the user looked at it, and a rule that needed a click per block makes
comparing two of them two gestures.

**A grid gesture emits; it never applies.** `solo_toggled` carries the block
index (or None for un-solo) and the drawn solo marker moves only when
`set_block_state` says so — solo lives in the state model, and a widget that
painted its own gesture before the model confirmed it would disagree with the
density plot for a frame every time. That ordering is a tested claim,
inherited from the block-heat panel this view absorbed. The latch is the one
piece of gesture state that does live here, and it is not the solo: it says
what the pointer leaving reverts *to*, and it is compared against `self.solo`
— what the model last applied — so a request the model dropped is asked again
on the next crossing rather than deduplicated into silence.
"""

from __future__ import annotations

from bisect import bisect_right
from typing import Any

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QEvent, QObject, QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QImage,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from sieve.gui.band_plot import ACCENT, DIM, PANEL, TEXT, plot_font
from sieve.gui.zoom import Magnifier

FloatArray = NDArray[np.floating[Any]]

#: Default overlay opacity. High enough that a binary mask is unmissable,
#: low enough that the input stays legible under it.
DEFAULT_OPACITY = 65

#: The grid sliders speak in 0.2 steps: 0..GRID_STEPS maps to 0.0..1.0. Coarse
#: on purpose — the separated-blocks/mass distinction needs the two alphas to
#: be *matchable*, and a continuous slider makes equal a pixel hunt.
GRID_STEPS = 5

#: Grid slider defaults, in steps: in-band fill 0.6, border 0.2, heat 0.6.
DEFAULT_FILL_STEP = 3
DEFAULT_LINE_STEP = 1
DEFAULT_HEAT_STEP = 3

#: The heatmap's cold-to-hot stops — an approximation of the turbo ramp v1
#: blended over the footage, so low power reads cool blue and high power
#: reads hot red. Distinct from the scalogram's warm ramp on purpose: the
#: scalogram is a dark surface its ramp must stay legible against; this layer
#: sits over footage, where cold-to-hot is what v1 taught the eye.
HEAT_STOPS: tuple[tuple[int, int, int], ...] = (
    (48, 18, 59),
    (69, 91, 205),
    (62, 155, 254),
    (24, 214, 203),
    (72, 248, 130),
    (164, 252, 60),
    (226, 220, 56),
    (254, 163, 49),
    (239, 89, 17),
    (194, 36, 3),
    (122, 4, 3),
)

_HEADER = 22
_FOOTER = 26
_MARGIN = 6


def heat_color(t: float) -> QColor:
    """The heatmap color for a normalized value in [0, 1], cold to hot."""
    t = min(max(t, 0.0), 1.0) * (len(HEAT_STOPS) - 1)
    low = min(int(t), len(HEAT_STOPS) - 2)
    frac = t - low
    a, b = HEAT_STOPS[low], HEAT_STOPS[low + 1]
    return QColor(
        round(a[0] + (b[0] - a[0]) * frac),
        round(a[1] + (b[1] - a[1]) * frac),
        round(a[2] + (b[2] - a[2]) * frac),
    )


class _CompositePane(QWidget):
    """The paint surface: base full, over at the owner's opacity, grid on top."""

    #: A block index to solo, or None to un-solo. Emitted, never self-applied.
    solo_toggled = Signal(object)
    #: The hovered block index, or None off the grid. The view's footer reads it.
    hover_changed = Signal(object)
    #: The magnification changed, as a multiple of the fit scale.
    zoom_changed = Signal(float)

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
        #: The block a click pinned. Gesture state, not the solo: it decides
        #: what the pointer leaving the grid reverts to, and what is *drawn*
        #: still moves only when `set_block_state` says so.
        self.latched: int | None = None
        self.fill_alpha = DEFAULT_FILL_STEP / GRID_STEPS
        self.line_alpha = DEFAULT_LINE_STEP / GRID_STEPS
        self.heat_alpha = DEFAULT_HEAT_STEP / GRID_STEPS
        #: The band power that reads as full heat, fixed across the window.
        self.scale_max = 1.0
        #: Shift is held: every overlay drops so the frame can be read bare.
        self.peek = False
        #: Zoom and pan, shared with the replicate tab's viewport.
        self.magnifier = Magnifier()
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

    def view_rect(self) -> QRectF:
        """Where everything paints: the fit magnified and panned.

        The one rectangle the images, the grid, and the hit test all read, so
        the overlay cannot drift off the pixels it describes.
        """
        return self.magnifier.view_rect(self._content_rect())

    def grid_rect(self) -> QRectF:
        """Where the grid paints: the same rectangle the images fill."""
        return self.view_rect()

    def grid_edges(self) -> tuple[list[int], list[int]]:
        """The integer pixel columns and rows the grid lines fall on.

        `(xs, ys)`, each `n + 1` long: cell `(row, col)` owns the pixels
        `xs[col] .. xs[col + 1] - 1` across and `ys[row] .. ys[row + 1] - 1`
        down. Rounding the *line* rather than each cell's own origin and
        extent is what closes the seam: neighbouring cells cannot round apart
        when they read the same number, whereas `left + i*w` and
        `left + (i-1)*w + w` are the same real and need not be the same float,
        and one ULP either side of a half-pixel is a row of unblended footage
        across the heatmap.

        Both the paint and `block_at` read this, so the cell under the pointer
        is the cell the pointer is over — registration between the two is not
        maintained so much as unable to come apart.
        """
        g = self.grid_rect()
        ny, nx = self.grid
        xs = [round(g.left() + i * g.width() / nx) for i in range(nx + 1)]
        ys = [round(g.top() + j * g.height() / ny) for j in range(ny + 1)]
        return xs, ys

    def block_at(self, pos: QPointF) -> int | None:
        """The block under `pos`, or None outside the grid (or with none on).

        Two containment tests, not one. A magnified grid runs off under the
        letterbox, and the cells out there are clipped away at paint time — so
        a point the fit does not contain is over bare panel whatever the grid
        rect says, and answering with the cell that would have been there
        would solo a block the user cannot see.
        """
        if not self.grid_on:
            return None
        g = self.grid_rect()
        if not g.contains(pos) or g.isEmpty() or not self._content_rect().contains(pos):
            return None
        ny, nx = self.grid
        xs, ys = self.grid_edges()
        col = min(max(bisect_right(xs, int(pos.x())) - 1, 0), nx - 1)
        row = min(max(bisect_right(ys, int(pos.y())) - 1, 0), ny - 1)
        return row * nx + col

    # ---- input -----------------------------------------------------------

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Magnify about the cursor, never below the fit.

        Nothing scrollable encloses this pane — the card column that made a
        wheel ambiguous is the other half of the tab — so the gesture is free
        here and needs no focus first. See `gui/wheel_steps.py` for the rule
        that decides which knobs yield the wheel and why this one does not.
        """
        detents = event.angleDelta().y() / 120.0
        if detents == 0.0:
            super().wheelEvent(event)
            return
        if self.magnifier.wheel(detents, event.position(), self._content_rect()):
            self.zoom_changed.emit(self.magnifier.zoom)
            self._refresh_hover(event.position())
            self.update()
        event.accept()

    def reset_zoom(self) -> None:
        """Return to the fitted view."""
        if self.magnifier.reset():
            self.zoom_changed.emit(self.magnifier.zoom)
            self.update()

    def _solo_now(self) -> int | None:
        """What the gesture currently means: the hovered block, else the pinned one."""
        return self.hover if self.hover is not None else self.latched

    def _emit_solo(self) -> None:
        """Ask for the gesture's solo, unless the model already holds it.

        Compared against `self.solo` rather than against a private record of
        what was last emitted: the model's value is the one that is drawn, so
        a request it dropped is worth asking again, and a request it already
        satisfied is worth not asking twice — a redundant one costs a repaint
        of every graph at pointer speed.
        """
        solo = self._solo_now()
        if solo != self.solo:
            self.solo_toggled.emit(solo)

    def _set_hover(self, hover: int | None) -> None:
        """One funnel for every change of the block under the pointer.

        Hover moves the solo as well as the footer readout — the pane asks,
        the model decides — and it fires per *block crossing* rather than per
        mouse sample, which is what makes driving something as involuntary as
        pointer position affordable at all.
        """
        if hover == self.hover:
            return
        self.hover = hover
        self.hover_changed.emit(hover)
        self._emit_solo()
        self.update()

    def clear_solo_gesture(self) -> None:
        """Forget hover and pin — what a grid going away means for the gesture.

        Emitted, not silent: a pin left standing over a grid that is no longer
        drawn would keep a block soloed in the density plot with nothing on
        screen saying which, which is rule 6's mirror direction.
        """
        self.latched = None
        if self.hover is not None:
            self.hover = None
            self.hover_changed.emit(None)
        self._emit_solo()
        self.update()

    def _refresh_hover(self, pos: QPointF) -> None:
        """Re-read the block under a stationary cursor after the map moved."""
        self._set_hover(self.block_at(pos))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._set_hover(self.block_at(event.position()))

    def leaveEvent(self, event: object) -> None:
        del event
        self._set_hover(None)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Pin the block under the cursor, or unpin it; the model still decides.

        Unpinning while the pointer is still on the block asks for nothing new
        — hover is soloing it either way — and that is the whole difference the
        click makes: what leaving the grid reverts to.
        """
        if event.button() is not Qt.MouseButton.LeftButton:
            return
        block = self.block_at(event.position())
        if block is None:
            return
        self.latched = None if block == self.latched else block
        self._emit_solo()

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
        # Everything after this is clipped to the fitted box, so a magnified
        # view spills into the letterbox no more than a fitted one does — and
        # `block_at`'s second containment test is the same boundary read from
        # the input side.
        painter.setClipRect(content)
        view = self.view_rect()
        if self.base is not None:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            painter.drawImage(view, self.base)
        if self.over is not None and not self.peek:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            painter.setOpacity(self.opacity)
            painter.drawImage(view, self.over)
            painter.setOpacity(1.0)
        if self.grid_on and not self.peek:
            self._paint_grid(painter)
        painter.end()

    def _paint_grid(self, painter: QPainter) -> None:
        """Heatmap under, detected squares over — three independent alphas.

        The heatmap tiles every cell edge to edge, coloured cold-to-hot by
        value, at the layer's own alpha: a contiguous surface, the way v1
        blended its colormap over the footage. Edge to edge means
        `grid_edges`' integer lines — cells that share a number cannot leave a
        gap between them, which is the seam this used to draw.

        The detected overlay sits on top, and only on in-band cells. A wall is
        one pixel wide *everywhere*, whether it separates a detected cell from
        bare heat or from another detected cell — so the interior lines of a
        detected region, which carry the least information, no longer get the
        heaviest ink. That costs an asymmetry: every cell owns its top and
        left pixel lines and gives up its bottom and right ones to the
        neighbour below and to the right, unless there is no detected
        neighbour there to give them to. The reward is that every wall pixel
        is painted exactly once, by exactly one cell, so the ring alpha means
        one thing on screen rather than two.

        Ring and interior stay disjoint pixel regions, and the fill takes
        whatever the walls leave: border alpha 0 bares the seam between
        neighbouring fills (separated blocks), equal alphas tile the in-band
        region seamlessly (a mass). Antialiasing stays off so a ring is a
        square ring, not a rounded smear.
        """
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        ny, nx = self.grid
        xs, ys = self.grid_edges()
        blocks = min(ny * nx, len(self.values), len(self.in_band))

        def cell_rect(b: int) -> QRect:
            row, col = divmod(b, nx)
            return QRect(xs[col], ys[row], xs[col + 1] - xs[col], ys[row + 1] - ys[row])

        def detected(row: int, col: int) -> bool:
            """Whether the cell at `(row, col)` is in band — False off the grid."""
            if not (0 <= row < ny and 0 <= col < nx):
                return False
            b = row * nx + col
            return b < blocks and bool(self.in_band[b])

        if self.heat_alpha > 0.0:
            for b in range(blocks):
                heat = heat_color(float(self.values[b]) / max(self.scale_max, 1e-12))
                heat.setAlphaF(self.heat_alpha)
                painter.fillRect(cell_rect(b), heat)

        if self.fill_alpha > 0.0 or self.line_alpha > 0.0:
            fill = QColor(ACCENT)
            fill.setAlphaF(self.fill_alpha)
            line = QColor(ACCENT)
            line.setAlphaF(self.line_alpha)
            for b in range(blocks):
                if not bool(self.in_band[b]):
                    continue
                row, col = divmod(b, nx)
                # The cell's first and last pixel, in each axis.
                x0, x1 = xs[col], xs[col + 1] - 1
                y0, y1 = ys[row], ys[row + 1] - 1
                if x1 < x0 or y1 < y0:  # a cell too small to hold a pixel
                    continue
                # Which of the four walls this cell owns. Top and left always;
                # bottom and right only where there is no detected neighbour to
                # own them instead.
                right_wall = x1 > x0 and not detected(row, col + 1)
                bottom_wall = y1 > y0 and not detected(row + 1, col)
                if self.line_alpha > 0.0:
                    painter.fillRect(QRect(x0, y0, x1 - x0 + 1, 1), line)
                    if y1 > y0:
                        painter.fillRect(QRect(x0, y0 + 1, 1, y1 - y0), line)
                    if right_wall:
                        painter.fillRect(QRect(x1, y0 + 1, 1, y1 - y0), line)
                    if bottom_wall:
                        # The left wall already holds this row's first pixel,
                        # and the right wall its last one if it was drawn.
                        bx1 = x1 - 1 if right_wall else x1
                        if bx1 >= x0 + 1:
                            painter.fillRect(QRect(x0 + 1, y1, bx1 - x0, 1), line)
                if self.fill_alpha > 0.0:
                    right = x1 - 1 if right_wall else x1
                    bottom = y1 - 1 if bottom_wall else y1
                    if right >= x0 + 1 and bottom >= y0 + 1:
                        painter.fillRect(QRect(x0 + 1, y0 + 1, right - x0, bottom - y0), fill)

        if self.solo is not None and self.solo < ny * nx:
            painter.setPen(QPen(TEXT, 1.8))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(cell_rect(self.solo).adjusted(1, 1, -1, -1))


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
        # The header states the magnification, so it repaints when it moves.
        self._pane.zoom_changed.connect(self._on_zoom)

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
        self._line_slider = self._grid_slider(DEFAULT_LINE_STEP, "Detected border alpha")
        self._line_slider.valueChanged.connect(self._on_line_alpha)
        self._heat_slider = self._grid_slider(DEFAULT_HEAT_STEP, "Heatmap alpha")
        self._heat_slider.valueChanged.connect(self._on_heat_alpha)
        self._grid_tags = tuple(self._tag_label(text) for text in ("fill", "border", "heat"))

        self._tag = self._tag_label("input · output")

        footer = QHBoxLayout()
        footer.setContentsMargins(_MARGIN, 0, _MARGIN, 4)
        footer.addWidget(self._tag)
        footer.addStretch(1)
        for tag, slider in zip(
            self._grid_tags,
            (self._fill_slider, self._line_slider, self._heat_slider),
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
        if not on:
            self._pane.clear_solo_gesture()
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

    def set_scale_max(self, value: float) -> None:
        """The band power that reads as full heat, fixed across the window."""
        self._pane.scale_max = max(value, 1e-12)
        self._pane.update()

    def reset_zoom(self) -> None:
        """Return to the fitted view — a new source is a new picture."""
        self._pane.reset_zoom()
        self.update()

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
    def heat_slider(self) -> QSlider:
        """The heatmap layer's alpha control."""
        return self._heat_slider

    @property
    def zoom(self) -> float:
        """Magnification as a multiple of the fit scale. 1.0 is fitted."""
        return self._pane.magnifier.zoom

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
        for slider in (self._fill_slider, self._line_slider, self._heat_slider):
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

    def _on_zoom(self, zoom: float) -> None:
        """The header states the magnification, so it repaints when it moves."""
        del zoom
        self.update()

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

    def _on_heat_alpha(self, step: int) -> None:
        self._pane.heat_alpha = step / GRID_STEPS
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
            title = f"{title} — HOVER SOLOS · CLICK PINS · SHIFT PEEKS"
        # Magnified is a state a user can forget they are in, and at 8x a grid
        # shows a handful of cells that look like the whole thing. The header
        # says so; scrolling out returns exactly to the fit.
        if self._pane.magnifier.magnified:
            title = f"{title} — {self._pane.magnifier.zoom:.1f}X"
        painter.drawText(QRect(10, 4, self.width() - 20, 14), 0, title)
        painter.end()
