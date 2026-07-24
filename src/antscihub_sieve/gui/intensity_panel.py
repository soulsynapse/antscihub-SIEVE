from __future__ import annotations

from typing import TypeAlias

import numpy as np
from PyQt6.QtCore import QPoint, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QMouseEvent, QPaintEvent, QPainter, QPen
from PyQt6.QtWidgets import QToolTip, QWidget

from antscihub_sieve.application.change_energy import ChangeEnergyResult
from antscihub_sieve.application.intensity import (
    IntensityResult,
    NormalizationMode,
)


OFF_PRESENTATION_ID = "sieve.presentation.intensity_0_1_grayscale.v1"
ZSCORE_PRESENTATION_ID = "sieve.presentation.zscore_minus3_plus3_diverging.v1"
CHANGE_OFF_PRESENTATION_ID = (
    "sieve.presentation.change_energy_0_1_sequential.v1"
)
CHANGE_ZSCORE_PRESENTATION_ID = (
    "sieve.presentation.change_energy_e_over_e_plus_1.v1"
)
DENSITY_BRIGHTNESS_ID = "sieve.presentation.area_weighted_density_log1p.v1"
SelectedResult: TypeAlias = IntensityResult | ChangeEnergyResult


class IntensityRaster(QWidget):
    """Selected-channel time-by-value density.

    The historical class name remains as a compatibility seam for the existing
    Isolate tests and callers; it no longer presents block identity as a value
    axis.
    """

    frame_selected = pyqtSignal(int)

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(180)
        self.setMouseTracking(True)
        self._result: SelectedResult | None = None
        self._image = QImage()
        self._density_mass: np.ndarray | None = None
        self._density_count: np.ndarray | None = None
        self._current_frame: int | None = None
        self._presentation_mapping_id: str | None = None
        self._raster_key: tuple[object, ...] | None = None

    @property
    def result(self) -> SelectedResult | None:
        return self._result

    @property
    def presentation_mapping_id(self) -> str | None:
        return self._presentation_mapping_id

    def set_result(self, result: SelectedResult | None) -> None:
        self._result = result
        self._presentation_mapping_id = _mapping_id(result)
        self._raster_key = None
        self._image = QImage()
        self._density_mass = None
        self._density_count = None
        self._ensure_raster()
        self.update()

    def set_current_frame(self, frame: int | None) -> None:
        if frame != self._current_frame:
            self._current_frame = frame
            self.update()

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self._raster_key = None
        self._ensure_raster()
        super().resizeEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        self._ensure_raster()
        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor("#171717"))
        target = self._target_rect()
        if self._image.isNull() or target.isEmpty():
            painter.setPen(QColor("#a0a0a0"))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Compute the selected channel to view time × value density.",
            )
            return
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.drawImage(target, self._image)
        painter.setPen(QPen(QColor("#777777"), 1))
        painter.drawRect(target)
        cursor_x = self._cursor_x(target)
        if cursor_x is not None:
            painter.setPen(QPen(QColor("#ff2dd2"), 2))
            painter.drawLine(
                int(round(cursor_x)),
                int(target.top()),
                int(round(cursor_x)),
                int(target.bottom()),
            )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() is Qt.MouseButton.LeftButton:
            location = self._cell_at(event.position())
            if location is not None and self._result is not None:
                self.frame_selected.emit(
                    self._result.processed_start + location[0]
                )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        location = self._cell_at(event.position())
        result = self._result
        if (
            location is None
            or result is None
            or self._density_mass is None
            or self._density_count is None
        ):
            QToolTip.hideText()
            return
        frame_offset, value_bin = location
        frame = result.processed_start + frame_offset
        valid = _frame_valid(result, frame_offset)
        low, high = _bin_interval(result, value_bin, self._density_mass.shape[0])
        pair = (
            "no predecessor"
            if isinstance(result, ChangeEnergyResult) and frame == 0
            else (
                f"pair ({frame - 1},{frame})"
                if isinstance(result, ChangeEnergyResult)
                else "single-frame intensity"
            )
        )
        QToolTip.showText(
            event.globalPosition().toPoint(),
            (
                f"Frame {frame} · "
                f"{frame * result.resolved_window.fps_den / result.resolved_window.fps_num:.6f} s\n"
                f"Value bin [{low:.6f}, {high:.6f}) {result.scientific_units}\n"
                f"Raw block count {int(self._density_count[value_bin, frame_offset])}\n"
                f"Area-weighted mass {self._density_mass[value_bin, frame_offset]:.6f}\n"
                f"Frame valid {'yes' if valid else 'no'}\n"
                f"{pair}\n"
                f"Presentation {self._presentation_mapping_id}\n"
                f"Brightness {DENSITY_BRIGHTNESS_ID}"
            ),
            self,
        )

    def leaveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        QToolTip.hideText()
        super().leaveEvent(event)

    def _ensure_raster(self) -> None:
        result = self._result
        if result is None or result.values.size == 0:
            return
        bins = max(32, min(256, self.height() - 2))
        key = (id(result), self._presentation_mapping_id, bins)
        if key == self._raster_key:
            return
        frames = result.values.shape[0]
        mass = np.zeros((bins, frames), dtype=np.float64)
        count = np.zeros((bins, frames), dtype=np.uint32)
        weights = np.asarray(result.partial_cell_weights, dtype=np.float64)
        for frame_offset in range(frames):
            if not _frame_valid(result, frame_offset):
                continue
            values = result.values[frame_offset].reshape(-1)
            positions = _display_position(result, values)
            indices = np.minimum(
                bins - 1, np.floor(positions * bins).astype(np.intp)
            )
            np.add.at(mass[:, frame_offset], indices, weights)
            np.add.at(count[:, frame_offset], indices, 1)
        brightness = np.log1p(mass)
        maximum = float(np.max(brightness))
        if maximum > 0:
            brightness /= maximum
        colors = _density_value_colors(result, bins)
        pixels = np.rint(
            brightness[..., None] * colors[:, None, :]
        ).astype(np.uint8)
        pixels = np.ascontiguousarray(np.flipud(pixels))
        self._image = QImage(
            pixels.tobytes(),
            frames,
            bins,
            pixels.strides[0],
            QImage.Format.Format_RGB888,
        ).copy()
        self._density_mass = mass
        self._density_count = count
        self._raster_key = key

    def _target_rect(self) -> QRectF:
        return QRectF(self.rect().adjusted(1, 1, -2, -2))

    def _cursor_x(self, target: QRectF) -> float | None:
        result = self._result
        frame = self._current_frame
        if (
            result is None
            or frame is None
            or not result.processed_start <= frame < result.processed_stop
        ):
            return None
        return target.left() + (
            (frame - result.processed_start + 0.5)
            * target.width()
            / result.values.shape[0]
        )

    def _cell_at(self, position: QPoint) -> tuple[int, int] | None:
        result = self._result
        target = self._target_rect()
        if (
            result is None
            or result.values.size == 0
            or self._density_mass is None
            or not target.contains(position)
        ):
            return None
        frames = result.values.shape[0]
        bins = self._density_mass.shape[0]
        frame_offset = min(
            frames - 1,
            int((position.x() - target.left()) * frames / target.width()),
        )
        display_bin = min(
            bins - 1,
            int((position.y() - target.top()) * bins / target.height()),
        )
        return frame_offset, bins - 1 - display_bin


def _mapping_id(result: SelectedResult | None) -> str | None:
    if result is None:
        return None
    zscore = (
        result.request.normalization.mode is NormalizationMode.PER_FRAME_ZSCORE
    )
    if isinstance(result, ChangeEnergyResult):
        return CHANGE_ZSCORE_PRESENTATION_ID if zscore else CHANGE_OFF_PRESENTATION_ID
    return ZSCORE_PRESENTATION_ID if zscore else OFF_PRESENTATION_ID


def _frame_valid(result: SelectedResult, offset: int) -> bool:
    if isinstance(result, ChangeEnergyResult):
        return bool(result.temporal_valid[offset])
    return offset < result.values.shape[0]


def _display_position(
    result: SelectedResult, values: np.ndarray
) -> np.ndarray:
    work = values.astype(np.float64, copy=False)
    if isinstance(result, ChangeEnergyResult):
        if result.request.normalization.mode is NormalizationMode.PER_FRAME_ZSCORE:
            return np.clip(work / (work + 1.0), 0.0, np.nextafter(1.0, 0.0))
        return np.clip(work, 0.0, np.nextafter(1.0, 0.0))
    if result.request.normalization.mode is NormalizationMode.PER_FRAME_ZSCORE:
        return np.clip((work + 3.0) / 6.0, 0.0, np.nextafter(1.0, 0.0))
    return np.clip(work, 0.0, np.nextafter(1.0, 0.0))


def _bin_interval(
    result: SelectedResult, index: int, bins: int
) -> tuple[float, float]:
    low = index / bins
    high = (index + 1) / bins
    if isinstance(result, ChangeEnergyResult):
        if result.request.normalization.mode is NormalizationMode.PER_FRAME_ZSCORE:
            def inverse(value: float) -> float:
                return value / (1.0 - value) if value < 1.0 else float("inf")
            return inverse(low), inverse(high)
        return low, high
    if result.request.normalization.mode is NormalizationMode.PER_FRAME_ZSCORE:
        return low * 6.0 - 3.0, high * 6.0 - 3.0
    return low, high


def _density_value_colors(
    result: SelectedResult, bins: int
) -> np.ndarray:
    positions = (np.arange(bins, dtype=np.float64) + 0.5) / bins
    if isinstance(result, ChangeEnergyResult):
        red = np.full(bins, 255.0)
        green = positions * 184.0
        blue = positions * 32.0
        return np.stack((red, green, blue), axis=-1)
    if result.request.normalization.mode is NormalizationMode.PER_FRAME_ZSCORE:
        values = positions * 6.0 - 3.0
        return _zscore_diverging_pixels(values).astype(np.float64)
    gray = positions * 255.0
    return np.stack((gray, gray, gray), axis=-1)


def _zscore_diverging_pixels(values: np.ndarray) -> np.ndarray:
    scaled = np.clip((values.astype(np.float64) + 3.0) / 6.0, 0.0, 1.0)
    low = np.array((33.0, 102.0, 172.0), dtype=np.float64)
    center = np.array((255.0, 255.0, 255.0), dtype=np.float64)
    high = np.array((178.0, 24.0, 43.0), dtype=np.float64)
    lower_fraction = np.minimum(scaled * 2.0, 1.0)[..., None]
    upper_fraction = np.maximum((scaled - 0.5) * 2.0, 0.0)[..., None]
    lower_colors = low + (center - low) * lower_fraction
    colors = lower_colors + (high - center) * upper_fraction
    return np.ascontiguousarray(np.rint(colors).astype(np.uint8))
