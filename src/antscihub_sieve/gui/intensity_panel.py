from __future__ import annotations

from typing import TypeAlias

import numpy as np
from PyQt6.QtCore import QPoint, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QMouseEvent, QPaintEvent, QPainter, QPen
from PyQt6.QtWidgets import QToolTip, QWidget

from antscihub_sieve.application.channel_progress import ChannelFrame
from antscihub_sieve.application.change_energy import (
    ChangeEnergyRequest,
    ChangeEnergyResult,
)
from antscihub_sieve.application.intensity import (
    IntensityRequest,
    IntensityResult,
    NormalizationMode,
)


OFF_PRESENTATION_ID = "sieve.presentation.intensity_0_1_grayscale.v1"
ZSCORE_PRESENTATION_ID = "sieve.presentation.zscore_minus3_plus3_diverging.v1"
CHANGE_OFF_PRESENTATION_ID = (
    "sieve.presentation.change_energy_turbo_percentile99.v1"
)
CHANGE_ZSCORE_PRESENTATION_ID = (
    "sieve.presentation.change_energy_turbo_percentile99.v1"
)
DENSITY_BRIGHTNESS_ID = "sieve.presentation.block_density_log1p.v1"
SelectedRequest: TypeAlias = IntensityRequest | ChangeEnergyRequest
SelectedResult: TypeAlias = IntensityResult | ChangeEnergyResult


class IntensityRaster(QWidget):
    """The pre-rewrite time × value density instrument for one channel.

    The historical class name remains as a compatibility seam. Scientific
    values stay in their immutable result; this widget owns only a progressively
    filled presentation buffer while a run is active.
    """

    frame_selected = pyqtSignal(int)
    _RAMP = np.array(
        [
            [12, 12, 12],
            [20, 60, 90],
            [30, 120, 170],
            [90, 210, 255],
            [230, 250, 255],
        ],
        dtype=np.float64,
    )

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(220)
        self.setMouseTracking(True)
        self._result: SelectedResult | None = None
        self._request: SelectedRequest | None = None
        self._values: np.ndarray | None = None
        self._valid: np.ndarray | None = None
        self._preview_frames: dict[int, ChannelFrame] = {}
        self._total_frames = 0
        self._processed_start = 0
        self._covered_frames = 0
        self._image = QImage()
        self._density_mass: np.ndarray | None = None
        self._density_count: np.ndarray | None = None
        self._current_frame: int | None = None
        self._presentation_mapping_id: str | None = None
        self._raster_key: tuple[object, ...] | None = None
        self._data_range = (0.0, 1.0)
        self._channel_label = "Selected channel"
        self._scientific_units = ""

    @property
    def result(self) -> SelectedResult | None:
        return self._result

    @property
    def presentation_mapping_id(self) -> str | None:
        return self._presentation_mapping_id

    @property
    def covered_frames(self) -> int:
        return self._covered_frames

    def begin_preview(
        self,
        request: SelectedRequest,
        *,
        channel_label: str,
        scientific_units: str,
    ) -> None:
        total = (
            request.working_window.stop_frame
            - request.working_window.start_frame
        )
        self._result = None
        self._request = request
        self._values = None
        self._valid = np.zeros(total, dtype=np.uint8)
        self._preview_frames = {}
        self._total_frames = total
        self._processed_start = request.working_window.start_frame
        self._covered_frames = 0
        self._channel_label = channel_label
        self._scientific_units = scientific_units
        self._presentation_mapping_id = _mapping_id_from_request(request)
        self._invalidate_raster()

    def append_preview(
        self,
        frames: tuple[ChannelFrame, ...],
    ) -> None:
        if self._request is None or self._valid is None or not frames:
            return
        offset = frames[0].absolute_frame - self._processed_start
        stop = offset + len(frames)
        expected_shape = (
            self._request.grid.rows,
            self._request.grid.columns,
        )
        if offset < 0 or stop > self._total_frames:
            return
        for index, frame in enumerate(frames):
            if (
                frame.absolute_frame != frames[0].absolute_frame + index
                or frame.values.shape != expected_shape
            ):
                return
        for frame in frames:
            frame_offset = frame.absolute_frame - self._processed_start
            self._preview_frames[frame_offset] = frame
            self._valid[frame_offset] = int(frame.valid)
        if offset <= self._covered_frames:
            self._covered_frames = max(self._covered_frames, stop)
        self._invalidate_raster()

    def preview_frame(self, absolute_frame: int) -> ChannelFrame | None:
        return self._preview_frames.get(
            absolute_frame - self._processed_start
        )

    def set_result(self, result: SelectedResult | None) -> None:
        self._result = result
        if result is None:
            self._request = None
            self._values = None
            self._valid = None
            self._preview_frames = {}
            self._total_frames = 0
            self._processed_start = 0
            self._covered_frames = 0
            self._presentation_mapping_id = None
            self._channel_label = "Selected channel"
            self._scientific_units = ""
            self._invalidate_raster()
            return
        self._request = result.request
        self._values = result.values
        self._preview_frames = {}
        self._total_frames = result.values.shape[0]
        self._valid = (
            result.temporal_valid
            if isinstance(result, ChangeEnergyResult)
            else np.ones(result.values.shape[0], dtype=np.uint8)
        )
        self._processed_start = result.processed_start
        self._covered_frames = result.values.shape[0]
        self._presentation_mapping_id = _mapping_id(result)
        self._channel_label = (
            "Change energy" if isinstance(result, ChangeEnergyResult)
            else "Intensity"
        )
        self._scientific_units = result.scientific_units
        self._invalidate_raster()

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
        painter.fillRect(event.rect(), QColor("#121212"))
        target = self._target_rect()
        self._paint_header(painter, target)
        if self._image.isNull() or target.isEmpty():
            painter.setPen(QColor("#8a929c"))
            painter.drawText(
                target,
                Qt.AlignmentFlag.AlignCenter,
                "Compute the selected channel to view its distribution.",
            )
            return
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.drawImage(target, self._image)
        painter.setPen(QPen(QColor("#343b43"), 1))
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
        painter.setPen(QColor("#68717b"))
        painter.drawText(
            int(target.left()),
            int(target.bottom()) + 11,
            self._axis_label(),
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() is Qt.MouseButton.LeftButton:
            location = self._cell_at(event.position())
            if location is not None:
                self.frame_selected.emit(self._processed_start + location[0])
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        location = self._cell_at(event.position())
        if (
            location is None
            or self._density_mass is None
            or self._density_count is None
        ):
            QToolTip.hideText()
            return
        frame_offset, value_bin = location
        frame = self._processed_start + frame_offset
        valid = bool(
            self._valid is not None
            and frame_offset < self._valid.size
            and self._valid[frame_offset]
        )
        low, high = self._bin_interval(
            value_bin, self._density_mass.shape[0]
        )
        QToolTip.showText(
            event.globalPosition().toPoint(),
            (
                f"Frame {frame}\n"
                f"Value bin [{low:.6g}, {high:.6g}) "
                f"{self._scientific_units}\n"
                f"Blocks {int(self._density_count[value_bin, frame_offset])}\n"
                f"Owned-area mass "
                f"{self._density_mass[value_bin, frame_offset]:.6f}\n"
                f"Frame {'valid' if valid else 'not yet computed or invalid'}"
            ),
            self,
        )

    def leaveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        QToolTip.hideText()
        super().leaveEvent(event)

    def _invalidate_raster(self) -> None:
        self._raster_key = None
        self._image = QImage()
        self._density_mass = None
        self._density_count = None
        self._ensure_raster()
        self.update()

    def _ensure_raster(self) -> None:
        values = self._values
        valid = self._valid
        target = self._target_rect()
        if (
            valid is None
            or self._total_frames == 0
            or target.width() < 1
            or target.height() < 1
        ):
            return
        width = max(1, int(round(target.width())))
        bins = max(32, min(256, int(round(target.height()))))
        key = (
            id(values) if values is not None else id(self._preview_frames),
            self._covered_frames,
            width,
            bins,
            self._presentation_mapping_id,
        )
        if key == self._raster_key:
            return

        frames = self._total_frames
        covered = min(self._covered_frames, frames)
        source_valid = valid[:covered].astype(bool, copy=False)
        if values is not None:
            blocks = values.shape[1] * values.shape[2]
            source = values[:covered].reshape((covered, blocks))
            finite = (
                source[source_valid]
                if source_valid.any()
                else np.empty(0)
            )
            finite = finite[np.isfinite(finite)]
            if finite.size:
                low = float(np.min(finite))
                high = float(np.max(finite))
            else:
                low, high = 0.0, 1.0
        else:
            blocks = (
                self._request.grid.rows * self._request.grid.columns
                if self._request is not None
                else 0
            )
            finite_frames = [
                frame.values
                for offset, frame in self._preview_frames.items()
                if offset < covered and frame.valid
            ]
            if finite_frames:
                low = min(float(np.min(field)) for field in finite_frames)
                high = max(float(np.max(field)) for field in finite_frames)
            else:
                low, high = 0.0, 1.0
        if high <= low:
            high = low + 1.0
        self._data_range = (low, high)

        mass = np.zeros((bins, frames), dtype=np.float64)
        count = np.zeros((bins, frames), dtype=np.uint32)
        weights = self._block_weights()
        valid_offsets = np.flatnonzero(source_valid)
        if valid_offsets.size:
            if values is not None:
                selected = source[valid_offsets]
                positions = self._value_positions(selected, low, high)
                indices = np.minimum(
                    bins - 1, np.floor(positions * bins).astype(np.intp)
                )
                frame_indices = np.repeat(valid_offsets, blocks)
                np.add.at(
                    mass,
                    (indices.ravel(), frame_indices),
                    np.tile(weights, valid_offsets.size),
                )
                np.add.at(
                    count,
                    (indices.ravel(), frame_indices),
                    1,
                )
            else:
                for frame_offset in valid_offsets:
                    frame = self._preview_frames.get(int(frame_offset))
                    if frame is None:
                        continue
                    positions = self._value_positions(
                        frame.values.reshape(-1), low, high
                    )
                    indices = np.minimum(
                        bins - 1,
                        np.floor(positions * bins).astype(np.intp),
                    )
                    np.add.at(mass[:, frame_offset], indices, weights)
                    np.add.at(count[:, frame_offset], indices, 1)

        columns = np.clip(
            (np.arange(frames, dtype=np.int64) * width) // max(1, frames),
            0,
            width - 1,
        )
        pixel_mass = np.zeros((bins, width), dtype=np.float64)
        if valid_offsets.size:
            bin_indices = np.tile(np.arange(bins), valid_offsets.size)
            column_indices = np.repeat(columns[valid_offsets], bins)
            np.add.at(
                pixel_mass,
                (bin_indices, column_indices),
                mass[:, valid_offsets].T.ravel(),
            )
        peak = float(pixel_mass.max())
        brightness = (
            np.log1p(pixel_mass) / np.log1p(peak)
            if peak > 0
            else pixel_mass
        )
        ramp_position = np.clip(brightness, 0.0, 1.0) * (
            len(self._RAMP) - 1
        )
        ramp_index = np.clip(
            ramp_position.astype(np.intp), 0, len(self._RAMP) - 2
        )
        fraction = (ramp_position - ramp_index)[..., None]
        rgb = (
            self._RAMP[ramp_index] * (1.0 - fraction)
            + self._RAMP[ramp_index + 1] * fraction
        )
        rgb = np.ascontiguousarray(np.flipud(rgb).astype(np.uint8))
        self._hatch_uncomputed(rgb, covered, frames)
        self._image = QImage(
            rgb.tobytes(),
            width,
            bins,
            rgb.strides[0],
            QImage.Format.Format_RGB888,
        ).copy()
        self._density_mass = mass
        self._density_count = count
        self._raster_key = key

    def _block_weights(self) -> np.ndarray:
        request = self._request
        if request is None:
            return np.empty(0, dtype=np.float64)
        return np.fromiter(
            (
                request.grid.block_area_weight(row, column)
                for row in range(request.grid.rows)
                for column in range(request.grid.columns)
            ),
            dtype=np.float64,
            count=request.grid.rows * request.grid.columns,
        )

    def _value_positions(
        self, values: np.ndarray, low: float, high: float
    ) -> np.ndarray:
        request = self._request
        use_log = (
            isinstance(request, ChangeEnergyRequest)
            or (
                isinstance(request, IntensityRequest)
                and request.normalization.mode is NormalizationMode.OFF
            )
        )
        if use_log and low >= 0.0:
            return np.clip(
                (np.log1p(values) - np.log1p(low))
                / max(1e-12, np.log1p(high) - np.log1p(low)),
                0.0,
                np.nextafter(1.0, 0.0),
            )
        return np.clip(
            (values - low) / max(1e-12, high - low),
            0.0,
            np.nextafter(1.0, 0.0),
        )

    def _hatch_uncomputed(
        self, rgb: np.ndarray, covered: int, total: int
    ) -> None:
        if covered >= total:
            return
        height, width = rgb.shape[:2]
        frontier = min(width, (covered * width + total - 1) // max(1, total))
        if frontier >= width:
            return
        x = np.arange(width - frontier)[None, :]
        y = np.arange(height)[:, None]
        stripe = ((x + y) % 8) < 2
        region = rgb[:, frontier:]
        region[:] = (24, 28, 33)
        region[stripe] = (52, 61, 70)

    def _paint_header(self, painter: QPainter, target: QRectF) -> None:
        painter.setPen(QColor("#d8dde4"))
        painter.drawText(4, 13, f"{self._channel_label} · block density")
        current = self._current_value()
        if current is not None:
            text = f"max {current:.4g} {self._scientific_units}".strip()
            painter.setPen(QColor("#7fd7ff"))
            painter.drawText(
                max(4, self.width() - 7 * len(text) - 4),
                13,
                text,
            )

    def _current_value(self) -> float | None:
        if self._valid is None or self._current_frame is None:
            return None
        offset = self._current_frame - self._processed_start
        if (
            offset < 0
            or offset >= self._covered_frames
            or not self._valid[offset]
        ):
            return None
        if self._values is not None:
            return float(np.max(self._values[offset]))
        frame = self._preview_frames.get(offset)
        return None if frame is None else float(np.max(frame.values))

    def _axis_label(self) -> str:
        low, high = self._data_range
        mode = (
            "log value axis"
            if isinstance(self._request, ChangeEnergyRequest)
            or (
                isinstance(self._request, IntensityRequest)
                and self._request.normalization.mode is NormalizationMode.OFF
            )
            else "linear value axis"
        )
        return f"{low:.3g} … {high:.3g} · {mode}"

    def _target_rect(self) -> QRectF:
        return QRectF(self.rect().adjusted(1, 20, -2, -14))

    def _cursor_x(self, target: QRectF) -> float | None:
        if self._total_frames == 0 or self._current_frame is None:
            return None
        offset = self._current_frame - self._processed_start
        if not 0 <= offset < self._total_frames:
            return None
        return target.left() + (
            (offset + 0.5) * target.width() / self._total_frames
        )

    def _cell_at(self, position: QPoint) -> tuple[int, int] | None:
        target = self._target_rect()
        if (
            self._total_frames == 0
            or self._density_mass is None
            or not target.contains(position)
        ):
            return None
        frames = self._total_frames
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

    def _bin_interval(self, index: int, bins: int) -> tuple[float, float]:
        low, high = self._data_range
        request = self._request
        use_log = (
            isinstance(request, ChangeEnergyRequest)
            or (
                isinstance(request, IntensityRequest)
                and request.normalization.mode is NormalizationMode.OFF
            )
        )
        a, b = index / bins, (index + 1) / bins
        if use_log and low >= 0.0:
            lo = np.expm1(np.log1p(low) + a * (np.log1p(high) - np.log1p(low)))
            hi = np.expm1(np.log1p(low) + b * (np.log1p(high) - np.log1p(low)))
            return float(lo), float(hi)
        return low + a * (high - low), low + b * (high - low)


def _mapping_id(result: SelectedResult | None) -> str | None:
    return None if result is None else _mapping_id_from_request(result.request)


def _mapping_id_from_request(request: SelectedRequest) -> str:
    zscore = request.normalization.mode is NormalizationMode.PER_FRAME_ZSCORE
    if isinstance(request, ChangeEnergyRequest):
        return (
            CHANGE_ZSCORE_PRESENTATION_ID
            if zscore
            else CHANGE_OFF_PRESENTATION_ID
        )
    return ZSCORE_PRESENTATION_ID if zscore else OFF_PRESENTATION_ID


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
