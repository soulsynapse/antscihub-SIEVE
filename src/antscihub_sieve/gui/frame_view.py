from __future__ import annotations

import math
from typing import Any

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QWidget


class FrameView(QWidget):
    region_created = pyqtSignal(list)
    region_moved = pyqtSignal(str, list)
    selection_changed = pyqtSignal(object)
    child_open_requested = pyqtSignal(int)
    back_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(480, 300); self.setMouseTracking(True); self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.image: QImage | None = None; self.frame_size = (1, 1)
        self.drafts: list[dict[str, Any]] = []; self.children: list[dict[str, Any]] = []
        self.selected_id: str | None = None; self.focus_box: list[int] | None = None
        self.draw_enabled = True; self.stamp_enabled = False; self.hide_overlays = False
        self._gesture: dict[str, Any] | None = None; self._preview_box: list[int] | None = None

    def set_frame(self, raw: bytes, width: int, height: int) -> None:
        self.image = QImage(raw, width, height, width * 3, QImage.Format.Format_RGB888).copy()
        self.frame_size = (width, height); self.update()

    def set_layout(self, drafts: list[dict[str, Any]], children: list[dict[str, Any]], selected_id: str | None = None) -> None:
        self.drafts, self.children = drafts, children; self.selected_id = selected_id; self.update()

    def select(self, region_id: str | None, *, focus: bool = False) -> None:
        self.selected_id = region_id
        region = next((r for r in self.drafts if r["region_id"] == region_id), None)
        if region is None:
            region = next((child["region_snapshot"] for child in self.children if child["region_snapshot"]["region_id"] == region_id), None)
        self.focus_box = list(region["box_xyxy"]) if focus and region else None
        self.selection_changed.emit(region_id); self.update()

    def exit_focus(self) -> None:
        self.focus_box = None; self.update()

    def _source_rect(self) -> QRectF:
        if self.focus_box:
            x0, y0, x1, y1 = self.focus_box; return QRectF(x0, y0, x1 - x0, y1 - y0)
        return QRectF(0, 0, self.frame_size[0], self.frame_size[1])

    def _image_rect(self) -> QRectF:
        source = self._source_rect(); available = QRectF(self.rect())
        scale = min(available.width() / source.width(), available.height() / source.height())
        width, height = source.width() * scale, source.height() * scale
        return QRectF((available.width() - width) / 2, (available.height() - height) / 2, width, height)

    def _to_source(self, position: QPointF) -> QPointF | None:
        position = QPointF(position)
        target = self._image_rect()
        if not target.contains(position): return None
        source = self._source_rect()
        return QPointF(source.x() + (position.x() - target.x()) * source.width() / target.width(),
                       source.y() + (position.y() - target.y()) * source.height() / target.height())

    def _to_source_clamped(self, position: QPointF) -> QPointF:
        target, source = self._image_rect(), self._source_rect(); position = QPointF(position)
        x = min(max(target.left(), position.x()), target.right()); y = min(max(target.top(), position.y()), target.bottom())
        return QPointF(source.x() + (x - target.x()) * source.width() / target.width(),
                       source.y() + (y - target.y()) * source.height() / target.height())

    def _to_view_rect(self, box: list[int]) -> QRectF:
        target, source = self._image_rect(), self._source_rect(); x0, y0, x1, y1 = box
        return QRectF(target.x() + (x0 - source.x()) * target.width() / source.width(),
                      target.y() + (y0 - source.y()) * target.height() / source.height(),
                      (x1 - x0) * target.width() / source.width(), (y1 - y0) * target.height() / source.height())

    def _resolve_drag(self, a: QPointF, b: QPointF) -> list[int]:
        width, height = self.frame_size
        x0 = max(0, min(width - 1, math.floor(min(a.x(), b.x())))); y0 = max(0, min(height - 1, math.floor(min(a.y(), b.y()))))
        x1 = max(x0 + 1, min(width, math.ceil(max(a.x(), b.x())))); y1 = max(y0 + 1, min(height, math.ceil(max(a.y(), b.y()))))
        return [x0, y0, x1, y1]

    @staticmethod
    def _drag_is_intentional(start: QPointF, current: QPointF) -> bool:
        return math.hypot(current.x() - start.x(), current.y() - start.y()) >= QApplication.startDragDistance()

    def _hit(self, point: QPointF) -> tuple[str, Any] | None:
        if self.hide_overlays: return None
        for region in reversed(self.drafts):
            x0, y0, x1, y1 = region["box_xyxy"]
            if x0 <= point.x() < x1 and y0 <= point.y() < y1: return "draft", region
        for index in range(len(self.children) - 1, -1, -1):
            x0, y0, x1, y1 = self.children[index]["region_snapshot"]["box_xyxy"]
            if x0 <= point.x() < x1 and y0 <= point.y() < y1: return "child", index
        return None

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self); painter.fillRect(self.rect(), QColor("#12151a"))
        if self.image is None:
            painter.setPen(QColor("#aab2bf")); painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Open source footage or an existing replicate."); return
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawImage(self._image_rect(), self.image, self._source_rect())
        if self.hide_overlays: return
        for child in self.children:
            snap = child["region_snapshot"]; pen = QPen(QColor(snap["color"]), 3 if snap["region_id"] == self.selected_id else 2, Qt.PenStyle.DashLine); painter.setPen(pen); painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self._to_view_rect(snap["box_xyxy"])); painter.drawText(self._to_view_rect(snap["box_xyxy"]).topLeft() + QPointF(4, 14), snap["label"])
        for region in self.drafts:
            box = self._preview_box if self._gesture and self._gesture.get("region_id") == region["region_id"] and self._preview_box else region["box_xyxy"]
            pen = QPen(QColor(region["color"]), 3 if region["region_id"] == self.selected_id else 2); painter.setPen(pen); painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self._to_view_rect(box)); painter.drawText(self._to_view_rect(box).topLeft() + QPointF(4, 14), region["label"])
        if self._gesture and self._gesture["kind"] == "draw" and self._preview_box:
            painter.setPen(QPen(QColor("#ffd24a"), 2)); painter.drawRect(self._to_view_rect(self._preview_box))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        point = self._to_source(event.position())
        if event.button() == Qt.MouseButton.RightButton:
            if self._gesture: self._gesture = None; self._preview_box = None; self.update(); return
            if self.focus_box: self.exit_focus()
            else: self.back_requested.emit()
            return
        if event.button() != Qt.MouseButton.LeftButton or point is None: return
        hit = self._hit(point)
        if hit and hit[0] == "child": self.child_open_requested.emit(hit[1]); return
        if hit and hit[0] == "draft":
            region = hit[1]; self.select(region["region_id"])
            if region.get("state") == "draft":
                self._gesture = {"kind": "move", "start": point, "region_id": region["region_id"], "original": list(region["box_xyxy"])}
            else:
                self.select(region["region_id"], focus=True)
            return
        selected = next((r for r in self.drafts if r["region_id"] == self.selected_id), None)
        if selected is None:
            selected = next((child["region_snapshot"] for child in self.children if child["region_snapshot"]["region_id"] == self.selected_id), None)
        if selected is None and self.drafts:
            selected = self.drafts[0]
        if selected is None and self.children:
            selected = self.children[0]["region_snapshot"]
        if self.stamp_enabled and selected:
            w = selected["box_xyxy"][2] - selected["box_xyxy"][0]; h = selected["box_xyxy"][3] - selected["box_xyxy"][1]
            x0 = min(max(0, round(point.x() - w / 2)), self.frame_size[0] - w); y0 = min(max(0, round(point.y() - h / 2)), self.frame_size[1] - h)
            self.region_created.emit([x0, y0, x0 + w, y0 + h]); return
        if self.draw_enabled: self._gesture = {"kind": "draw", "start": point, "view_start": QPointF(event.position())}; self._preview_box = None; self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self._gesture: return
        point = self._to_source(event.position())
        if point is None:
            point = self._to_source_clamped(event.position())
        if self._gesture["kind"] == "draw":
            self._preview_box = self._resolve_drag(self._gesture["start"], point) if self._drag_is_intentional(self._gesture["view_start"], event.position()) else None
        else:
            original = self._gesture["original"]; dx = round(point.x() - self._gesture["start"].x()); dy = round(point.y() - self._gesture["start"].y())
            w, h = original[2] - original[0], original[3] - original[1]; x0 = min(max(0, original[0] + dx), self.frame_size[0] - w); y0 = min(max(0, original[1] + dy), self.frame_size[1] - h)
            self._preview_box = [x0, y0, x0 + w, y0 + h]
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton or not self._gesture: return
        gesture, box = self._gesture, self._preview_box; self._gesture = None; self._preview_box = None
        if gesture["kind"] == "draw":
            if self._drag_is_intentional(gesture["view_start"], event.position()):
                point = self._to_source(event.position()) or self._to_source_clamped(event.position())
                self.region_created.emit(self._resolve_drag(gesture["start"], point))
        else:
            if box is None: return
            moved = max(abs(box[i] - gesture["original"][i]) for i in range(4)) >= 2
            if moved: self.region_moved.emit(gesture["region_id"], box)
            else: self.select(gesture["region_id"], focus=True)
        self.update()

    def keyPressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.key() == Qt.Key.Key_Shift: self.hide_overlays = True; self.update()
        else: super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.key() == Qt.Key.Key_Shift: self.hide_overlays = False; self.update()
        else: super().keyReleaseEvent(event)
