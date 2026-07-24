from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import QToolTip, QWidget

from antscihub_sieve.application.working_grid import ResolvedWorkingGrid


GRID_MIN_DISPLAY_SPACING = 4.0
CHANNEL_OVERLAY_OPACITY = 0.55


@dataclass(frozen=True, slots=True)
class ChannelOverlay:
    publication_token: int
    absolute_frame: int
    grid: ResolvedWorkingGrid
    values: np.ndarray
    presentation_mapping_id: str
    channel_label: str
    scientific_units: str
    detail: str
    display_scale: float = 1.0


class IsolatePlayer(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(480, 300)
        self.image: QImage | None = None
        self._frame_bytes: bytes | None = None
        self.displayed_frame: int | None = None
        self.frame_size = (1, 1)
        self.working_grid: ResolvedWorkingGrid | None = None
        self.show_grid = False
        self.channel_overlay: ChannelOverlay | None = None
        self.show_channel_overlay = True
        self._overlay_image = QImage()
        self._overlay_cache_key: tuple[object, ...] | None = None
        self.setMouseTracking(True)
        self.message = (
            "Open footage in Replicates or use File > Open to begin."
        )

    def set_frame(
        self,
        raw: bytes,
        width: int,
        height: int,
        absolute_frame: int | None = None,
    ) -> None:
        image = QImage(
            raw, width, height, width * 3, QImage.Format.Format_RGB888
        )
        self._frame_bytes = raw
        self.image = image
        self.frame_size = (width, height)
        self.displayed_frame = absolute_frame
        if (
            self.channel_overlay is not None
            and self.channel_overlay.absolute_frame != absolute_frame
        ):
            self.set_channel_overlay(None)
        self.message = ""
        self.update()

    def clear(self, message: str = "Loading video...") -> None:
        self.image = None
        self._frame_bytes = None
        self.frame_size = (1, 1)
        self.displayed_frame = None
        self.working_grid = None
        self.set_channel_overlay(None)
        self.message = message
        self.update()

    def set_channel_overlay(
        self, overlay: ChannelOverlay | None, *, visible: bool | None = None
    ) -> None:
        self.channel_overlay = overlay
        if visible is not None:
            self.show_channel_overlay = visible
        self._overlay_image = QImage()
        self._overlay_cache_key = None
        self.update()

    def set_channel_overlay_visible(self, visible: bool) -> None:
        self.show_channel_overlay = visible
        self.update()

    def set_working_grid(
        self,
        grid: ResolvedWorkingGrid | None,
        *,
        visible: bool,
    ) -> None:
        self.working_grid = grid
        self.show_grid = visible
        self.update()

    def image_rect(self) -> QRectF:
        available = QRectF(self.rect())
        width, height = self.frame_size
        scale = min(available.width() / width, available.height() / height)
        drawn_width, drawn_height = width * scale, height * scale
        return QRectF(
            (available.width() - drawn_width) / 2,
            (available.height() - drawn_height) / 2,
            drawn_width,
            drawn_height,
        )

    def grid_overlay_geometry(
        self,
    ) -> tuple[tuple[float, ...], tuple[float, ...], bool]:
        grid = self.working_grid
        if self.image is None or grid is None or not self.show_grid:
            return (), (), False
        rect = self.image_rect()
        block = grid.resolved_block_size
        spacing_x = rect.width() * block / grid.work_width
        spacing_y = rect.height() * block / grid.work_height
        dense = (
            grid.columns > 1 and spacing_x < GRID_MIN_DISPLAY_SPACING
        ) or (grid.rows > 1 and spacing_y < GRID_MIN_DISPLAY_SPACING)
        if dense:
            return (), (), True
        vertical = tuple(
            rect.left()
            + (column * block / grid.work_width) * rect.width()
            for column in range(1, grid.columns)
        )
        horizontal = tuple(
            rect.top() + (row * block / grid.work_height) * rect.height()
            for row in range(1, grid.rows)
        )
        return vertical, horizontal, False

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#12151a"))
        if self.image is None:
            painter.setPen(QColor("#aab2bf"))
            painter.drawText(
                self.rect(), Qt.AlignmentFlag.AlignCenter, self.message
            )
            return
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        image_rect = self.image_rect()
        painter.drawImage(image_rect, self.image)
        overlay = self.channel_overlay
        if (
            overlay is not None
            and self.show_channel_overlay
            and overlay.absolute_frame == self.displayed_frame
        ):
            overlay_image = self._channel_overlay_image(image_rect)
            if not overlay_image.isNull():
                painter.setOpacity(CHANNEL_OVERLAY_OPACITY)
                painter.drawImage(image_rect, overlay_image)
                painter.setOpacity(1.0)
        if self.working_grid is None or not self.show_grid:
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        pen = QPen(QColor(224, 229, 236, 190))
        pen.setCosmetic(True)
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.drawRect(image_rect)
        vertical, horizontal, dense = self.grid_overlay_geometry()
        if dense:
            painter.drawText(
                image_rect.adjusted(8, 6, -8, -6),
                Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                "Grid too dense at this zoom",
            )
            return
        for x in vertical:
            painter.drawLine(
                int(round(x)),
                int(round(image_rect.top())),
                int(round(x)),
                int(round(image_rect.bottom())),
            )
        for y in horizontal:
            painter.drawLine(
                int(round(image_rect.left())),
                int(round(y)),
                int(round(image_rect.right())),
                int(round(y)),
            )

    def _channel_overlay_image(self, rect: QRectF) -> QImage:
        overlay = self.channel_overlay
        if overlay is None:
            return QImage()
        width = max(1, int(round(rect.width())))
        height = max(1, int(round(rect.height())))
        key = (
            overlay.publication_token,
            overlay.absolute_frame,
            overlay.presentation_mapping_id,
            overlay.display_scale,
            width,
            height,
        )
        if key == self._overlay_cache_key:
            return self._overlay_image
        grid = overlay.grid
        x_work = (
            (np.arange(width, dtype=np.float64) + 0.5)
            * grid.work_width
            / width
        )
        y_work = (
            (np.arange(height, dtype=np.float64) + 0.5)
            * grid.work_height
            / height
        )
        columns = np.minimum(
            (x_work // grid.resolved_block_size).astype(np.intp),
            grid.columns - 1,
        )
        rows = np.minimum(
            (y_work // grid.resolved_block_size).astype(np.intp),
            grid.rows - 1,
        )
        block_pixels = _mapped_rgb(
            overlay.values,
            overlay.presentation_mapping_id,
            overlay.display_scale,
        )
        pixels = np.ascontiguousarray(block_pixels[rows[:, None], columns])
        self._overlay_image = QImage(
            pixels.tobytes(),
            width,
            height,
            pixels.strides[0],
            QImage.Format.Format_RGB888,
        ).copy()
        self._overlay_cache_key = key
        return self._overlay_image

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        overlay = self.channel_overlay
        rect = self.image_rect()
        if (
            overlay is None
            or not self.show_channel_overlay
            or overlay.absolute_frame != self.displayed_frame
            or not rect.contains(event.position())
        ):
            QToolTip.hideText()
            return super().mouseMoveEvent(event)
        grid = overlay.grid
        work_x = (event.position().x() - rect.left()) * grid.work_width / rect.width()
        work_y = (event.position().y() - rect.top()) * grid.work_height / rect.height()
        column = min(grid.columns - 1, int(work_x) // grid.resolved_block_size)
        row = min(grid.rows - 1, int(work_y) // grid.resolved_block_size)
        bounds = grid.block_bounds(row, column)
        QToolTip.showText(
            event.globalPosition().toPoint(),
            (
                f"Frame {overlay.absolute_frame}\n"
                f"{overlay.channel_label}\n"
                f"Block ({row}, {column})\n"
                f"Value {float(overlay.values[row, column]):.6f} "
                f"{overlay.scientific_units}\n"
                f"Bounds x[{bounds.x0},{bounds.x1}) "
                f"y[{bounds.y0},{bounds.y1})\n"
                f"Partial-cell weight "
                f"{grid.block_area_weight(row, column):.6f}\n"
                f"{overlay.detail}"
            ),
            self,
        )
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        QToolTip.hideText()
        super().leaveEvent(event)


def _mapped_rgb(
    values: np.ndarray,
    mapping_id: str,
    display_scale: float = 1.0,
) -> np.ndarray:
    from antscihub_sieve.gui.intensity_panel import (
        CHANGE_OFF_PRESENTATION_ID,
        CHANGE_ZSCORE_PRESENTATION_ID,
        OFF_PRESENTATION_ID,
        ZSCORE_PRESENTATION_ID,
        _zscore_diverging_pixels,
    )

    if mapping_id == ZSCORE_PRESENTATION_ID:
        return _zscore_diverging_pixels(values)
    if mapping_id in (CHANGE_OFF_PRESENTATION_ID, CHANGE_ZSCORE_PRESENTATION_ID):
        scaled = np.clip(
            np.asarray(values, dtype=np.float64)
            / max(float(display_scale), np.finfo(np.float32).eps),
            0.0,
            1.0,
        )
        return _turbo_pixels(scaled)
    assert mapping_id == OFF_PRESENTATION_ID
    scaled = np.clip(np.asarray(values, dtype=np.float64), 0.0, 1.0)
    gray = np.rint(scaled * 255.0).astype(np.uint8)
    return np.ascontiguousarray(np.repeat(gray[..., None], 3, axis=-1))


def _turbo_pixels(scaled: np.ndarray) -> np.ndarray:
    """Lookup-table equivalent of the old OpenCV TURBO change overlay."""
    indices = np.rint(
        np.clip(np.asarray(scaled, dtype=np.float64), 0.0, 1.0) * 255.0
    ).astype(np.uint8)
    return np.ascontiguousarray(_TURBO_LUT[indices])


def _build_turbo_lut() -> np.ndarray:
    x = np.linspace(0.0, 1.0, 256, dtype=np.float64)
    coefficients = np.array(
        [
            [0.13572138, 4.61539260, -42.66032258, 132.13108234, -152.94239396, 59.28637943],
            [0.09140261, 2.19418839, 4.84296658, -14.18503333, 4.27729857, 2.82956604],
            [0.10667330, 12.64194608, -60.58204836, 110.36276771, -89.90310912, 27.34824973],
        ],
        dtype=np.float64,
    )
    powers = np.stack([np.ones_like(x), x, x**2, x**3, x**4, x**5], axis=-1)
    rgb = np.clip(powers @ coefficients.T, 0.0, 1.0)
    lut = np.ascontiguousarray(np.rint(rgb * 255.0).astype(np.uint8))
    lut.setflags(write=False)
    return lut


_TURBO_LUT = _build_turbo_lut()
