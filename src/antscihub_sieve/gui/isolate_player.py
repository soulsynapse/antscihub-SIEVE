from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from antscihub_sieve.application.working_grid import ResolvedWorkingGrid


GRID_MIN_DISPLAY_SPACING = 4.0


class IsolatePlayer(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(480, 300)
        self.image: QImage | None = None
        self._frame_bytes: bytes | None = None
        self.frame_size = (1, 1)
        self.working_grid: ResolvedWorkingGrid | None = None
        self.show_grid = False
        self.message = (
            "Open footage in Replicates or use File > Open to begin."
        )

    def set_frame(self, raw: bytes, width: int, height: int) -> None:
        image = QImage(
            raw, width, height, width * 3, QImage.Format.Format_RGB888
        )
        self._frame_bytes = raw
        self.image = image
        self.frame_size = (width, height)
        self.message = ""
        self.update()

    def clear(self, message: str = "Loading video...") -> None:
        self.image = None
        self._frame_bytes = None
        self.frame_size = (1, 1)
        self.working_grid = None
        self.message = message
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
