





































































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



DEFAULT_OPACITY = 65




GRID_STEPS = 5


DEFAULT_FILL_STEP = 3
DEFAULT_LINE_STEP = 1
DEFAULT_HEAT_STEP = 3






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



    solo_toggled = Signal(object)

    hover_changed = Signal(object)

    zoom_changed = Signal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.base: QImage | None = None
        self.over: QImage | None = None
        self.opacity = DEFAULT_OPACITY / 100.0
        self.notice = ""


        self.grid_on = False
        self.grid: tuple[int, int] = (1, 1)
        self.values: NDArray[np.float32] = np.zeros(1, np.float32)
        self.in_band: NDArray[np.bool_] = np.zeros(1, bool)
        self.solo: int | None = None
        self.hover: int | None = None



        self.latched: int | None = None
        self.fill_alpha = DEFAULT_FILL_STEP / GRID_STEPS
        self.line_alpha = DEFAULT_LINE_STEP / GRID_STEPS
        self.heat_alpha = DEFAULT_HEAT_STEP / GRID_STEPS

        self.scale_max = 1.0

        self.peek = False

        self.magnifier = Magnifier()
        self.setMouseTracking(True)
        self.setMinimumHeight(160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)



    def _content_rect(self) -> QRectF:
        image = self.base if self.base is not None else self.over
        available = QRectF(self.rect()).adjusted(_MARGIN, 2, -_MARGIN, -2)
        if image is not None and image.height() > 0:
            aspect = image.width() / image.height()
        elif self.grid_on:


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





        return self.magnifier.view_rect(self._content_rect())

    def grid_rect(self) -> QRectF:

        return self.view_rect()

    def grid_edges(self) -> tuple[list[int], list[int]]:















        g = self.grid_rect()
        ny, nx = self.grid
        xs = [round(g.left() + i * g.width() / nx) for i in range(nx + 1)]
        ys = [round(g.top() + j * g.height() / ny) for j in range(ny + 1)]
        return xs, ys

    def block_at(self, pos: QPointF) -> int | None:








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



    def wheelEvent(self, event: QWheelEvent) -> None:







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

        if self.magnifier.reset():
            self.zoom_changed.emit(self.magnifier.zoom)
            self.update()

    def _solo_now(self) -> int | None:

        return self.hover if self.hover is not None else self.latched

    def _emit_solo(self) -> None:








        solo = self._solo_now()
        if solo != self.solo:
            self.solo_toggled.emit(solo)

    def _set_hover(self, hover: int | None) -> None:







        if hover == self.hover:
            return
        self.hover = hover
        self.hover_changed.emit(hover)
        self._emit_solo()
        self.update()

    def clear_solo_gesture(self) -> None:






        self.latched = None
        if self.hover is not None:
            self.hover = None
            self.hover_changed.emit(None)
        self._emit_solo()
        self.update()

    def _refresh_hover(self, pos: QPointF) -> None:

        self._set_hover(self.block_at(pos))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._set_hover(self.block_at(event.position()))

    def leaveEvent(self, event: object) -> None:
        del event
        self._set_hover(None)

    def mousePressEvent(self, event: QMouseEvent) -> None:






        if event.button() is not Qt.MouseButton.LeftButton:
            return
        block = self.block_at(event.position())
        if block is None:
            return
        self.latched = None if block == self.latched else block
        self._emit_solo()



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

























        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        ny, nx = self.grid
        xs, ys = self.grid_edges()
        blocks = min(ny * nx, len(self.values), len(self.in_band))

        def cell_rect(b: int) -> QRect:
            row, col = divmod(b, nx)
            return QRect(xs[col], ys[row], xs[col + 1] - xs[col], ys[row + 1] - ys[row])

        def detected(row: int, col: int) -> bool:

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

                x0, x1 = xs[col], xs[col + 1] - 1
                y0, y1 = ys[row], ys[row + 1] - 1
                if x1 < x0 or y1 < y0:
                    continue



                right_wall = x1 > x0 and not detected(row, col + 1)
                bottom_wall = y1 > y0 and not detected(row + 1, col)
                if self.line_alpha > 0.0:
                    painter.fillRect(QRect(x0, y0, x1 - x0 + 1, 1), line)
                    if y1 > y0:
                        painter.fillRect(QRect(x0, y0 + 1, 1, y1 - y0), line)
                    if right_wall:
                        painter.fillRect(QRect(x1, y0 + 1, 1, y1 - y0), line)
                    if bottom_wall:


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



    solo_toggled = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._caption = ""
        self._grid_caption = ""
        self._pane = _CompositePane()
        self._pane.solo_toggled.connect(self.solo_toggled)
        self._pane.hover_changed.connect(self._on_hover)

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



    def set_frames(self, base: QImage | None, over: QImage | None) -> None:

        self._pane.base = base
        self._pane.over = over
        self._pane.update()

    def set_caption(self, text: str) -> None:

        if text != self._caption:
            self._caption = text
            self.update()

    def set_notice(self, text: str) -> None:

        self._pane.notice = text
        self._pane.update()

    def set_grid_visible(self, on: bool) -> None:

        if on == self._pane.grid_on:
            return
        self._pane.grid_on = on
        if not on:
            self._pane.clear_solo_gesture()
        self._show_grid_controls(on)
        self._update_tag()
        self._pane.update()

    def set_grid(self, ny: int, nx: int) -> None:

        self._pane.grid = (max(ny, 1), max(nx, 1))
        self._pane.update()

    def set_block_state(
        self,
        values: FloatArray,
        in_band: NDArray[np.bool_],
        solo: int | None,
    ) -> None:

        self._pane.values = np.asarray(values, np.float32)
        self._pane.in_band = np.asarray(in_band, bool)
        self._pane.solo = solo
        self._pane.update()

    def set_grid_caption(self, text: str) -> None:

        self._grid_caption = text
        self._update_tag()

    def set_scale_max(self, value: float) -> None:

        self._pane.scale_max = max(value, 1e-12)
        self._pane.update()

    def reset_zoom(self) -> None:

        self._pane.reset_zoom()
        self.update()



    @property
    def caption(self) -> str:

        return self._caption

    @property
    def opacity(self) -> float:

        return self._pane.opacity

    @property
    def slider(self) -> QSlider:

        return self._slider

    @property
    def pane(self) -> _CompositePane:

        return self._pane

    @property
    def fill_slider(self) -> QSlider:

        return self._fill_slider

    @property
    def line_slider(self) -> QSlider:

        return self._line_slider

    @property
    def heat_slider(self) -> QSlider:

        return self._heat_slider

    @property
    def zoom(self) -> float:

        return self._pane.magnifier.zoom

    @property
    def peeking(self) -> bool:

        return self._pane.peek

    def frames(self) -> tuple[QImage | None, QImage | None]:

        return self._pane.base, self._pane.over



    def eventFilter(self, watched: QObject, event: QEvent) -> bool:

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



        if self._pane.magnifier.magnified:
            title = f"{title} — {self._pane.magnifier.zoom:.1f}X"
        painter.drawText(QRect(10, 4, self.width() - 20, 14), 0, title)
        painter.end()
