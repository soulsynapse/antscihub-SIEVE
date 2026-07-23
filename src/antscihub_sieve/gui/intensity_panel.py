from __future__ import annotations

import numpy as np
from PyQt6.QtCore import QPoint, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QMouseEvent, QPaintEvent, QPainter, QPen
from PyQt6.QtWidgets import QToolTip, QWidget

from antscihub_sieve.application.intensity import (
    IntensityResult,
    NormalizationMode,
)


OFF_PRESENTATION_ID = "sieve.presentation.intensity_0_1_grayscale.v1"
ZSCORE_PRESENTATION_ID = "sieve.presentation.zscore_minus3_plus3_diverging.v1"


class IntensityRaster(QWidget):
    frame_selected = pyqtSignal(int)

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(180)
        self.setMouseTracking(True)
        self._result: IntensityResult | None = None
        self._image = QImage()
        self._current_frame: int | None = None
        self._presentation_mapping_id: str | None = None

    @property
    def result(self) -> IntensityResult | None:
        return self._result

    @property
    def presentation_mapping_id(self) -> str | None:
        return self._presentation_mapping_id

    def set_result(self, result: IntensityResult | None) -> None:
        self._result = result
        self._image = QImage()
        self._presentation_mapping_id = None
        if result is not None and result.values.size:
            time_by_block = result.values.reshape(
                result.values.shape[0], -1
            )
            if (
                result.request.normalization.mode
                is NormalizationMode.PER_FRAME_ZSCORE
            ):
                pixels = _zscore_diverging_pixels(time_by_block.T)
                height, width, _ = pixels.shape
                self._image = QImage(
                    pixels.data,
                    width,
                    height,
                    pixels.strides[0],
                    QImage.Format.Format_RGB888,
                ).copy()
                self._presentation_mapping_id = ZSCORE_PRESENTATION_ID
            else:
                pixels = np.ascontiguousarray(
                    np.clip(
                        np.rint(time_by_block.T * 255.0),
                        0,
                        255,
                    ).astype(np.uint8)
                )
                height, width = pixels.shape
                self._image = QImage(
                    pixels.data,
                    width,
                    height,
                    pixels.strides[0],
                    QImage.Format.Format_Grayscale8,
                ).copy()
                self._presentation_mapping_id = OFF_PRESENTATION_ID
        self.update()

    def set_current_frame(self, frame: int | None) -> None:
        if frame != self._current_frame:
            self._current_frame = frame
            self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor("#171717"))
        target = self._target_rect()
        if self._image.isNull() or target.isEmpty():
            painter.setPen(QColor("#a0a0a0"))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Compute intensity to view time × block values.",
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
                frame_offset, _ = location
                self.frame_selected.emit(
                    self._result.processed_start + frame_offset
                )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        location = self._cell_at(event.position())
        result = self._result
        if location is None or result is None:
            QToolTip.hideText()
            return
        frame_offset, block_index = location
        row, column = divmod(block_index, result.request.grid.columns)
        bounds = result.request.grid.block_bounds(row, column)
        value = float(
            result.values[frame_offset, row, column]
        )
        degenerate = bool(result.degenerate_flags[frame_offset])
        mode = result.request.normalization.mode.value
        mapping = self._presentation_mapping_id or "none"
        QToolTip.showText(
            event.globalPosition().toPoint(),
            (
                f"Frame {result.processed_start + frame_offset}\n"
                f"Block ({row}, {column})\n"
                f"Value {value:.6f} {result.scientific_units}\n"
                f"Normalization {mode}\n"
                f"Degenerate {'yes' if degenerate else 'no'}\n"
                f"Presentation {mapping}\n"
                f"Bounds x[{bounds.x0},{bounds.x1}) "
                f"y[{bounds.y0},{bounds.y1})\n"
                f"Partial-cell weight "
                f"{result.request.grid.block_area_weight(row, column):.6f}"
            ),
            self,
        )

    def leaveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        QToolTip.hideText()
        super().leaveEvent(event)

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
            or not target.contains(position)
        ):
            return None
        frames = result.values.shape[0]
        blocks = result.request.grid.rows * result.request.grid.columns
        frame_offset = min(
            frames - 1,
            int((position.x() - target.left()) * frames / target.width()),
        )
        block_index = min(
            blocks - 1,
            int((position.y() - target.top()) * blocks / target.height()),
        )
        return frame_offset, block_index


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
