from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF


MIN_ZOOM = 1.0
MAX_ZOOM = 16.0

ZOOM_STEP = 1.25


class Magnifier:
    __slots__ = ("_centre", "zoom")

    def __init__(self) -> None:
        self.zoom = MIN_ZOOM
        self._centre = QPointF(0.5, 0.5)

    @property
    def magnified(self) -> bool:
        return self.zoom > MIN_ZOOM

    def reset(self) -> bool:
        self._centre = QPointF(0.5, 0.5)
        if self.zoom == MIN_ZOOM:
            return False
        self.zoom = MIN_ZOOM
        return True

    def view_rect(self, fit: QRectF) -> QRectF:
        if self.zoom <= MIN_ZOOM:
            return fit
        width = fit.width() * self.zoom
        height = fit.height() * self.zoom
        x = min(
            max(fit.center().x() - self._centre.x() * width, fit.right() - width),
            fit.left(),
        )
        y = min(
            max(fit.center().y() - self._centre.y() * height, fit.bottom() - height),
            fit.top(),
        )
        return QRectF(x, y, width, height)

    def at(self, point: QPointF, fit: QRectF) -> QPointF:
        view = self.view_rect(fit)
        if view.width() <= 0 or view.height() <= 0:
            return QPointF()
        return QPointF(
            (point.x() - view.x()) / view.width(),
            (point.y() - view.y()) / view.height(),
        )

    def wheel(self, detents: float, anchor: QPointF, fit: QRectF) -> bool:
        target = self.at(anchor, fit)
        zoom = min(max(self.zoom * (ZOOM_STEP**detents), MIN_ZOOM), MAX_ZOOM)
        if zoom == self.zoom:
            return False
        self.zoom = zoom
        self._recentre_on(target, anchor, fit)
        return True

    def _recentre_on(self, target: QPointF, anchor: QPointF, fit: QRectF) -> None:
        width = fit.width() * self.zoom
        height = fit.height() * self.zoom
        if width <= 0 or height <= 0:
            return
        self._centre = QPointF(
            (fit.center().x() - anchor.x()) / width + target.x(),
            (fit.center().y() - anchor.y()) / height + target.y(),
        )
