"""The frame view: one frame as a pixmap in a scene whose units are plate pixels, zoomed about the
cursor with Ctrl and the wheel, never smaller than the whole frame fitting, and panned by the middle
button or by the left with space held. The left and right buttons are otherwise the `editor`'s, whose
shapes, handles and gesture under way are painted over the frame."""
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QImage, QPainterPath, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QFrame, QGraphicsPixmapItem, QGraphicsScene, QGraphicsView

from .editor import HANDLE_PX

ZOOM_STEP = 1.25    # scale per wheel notch
MAX_SCALE = 256.0   # screen pixels per plate pixel; past a few dozen a pixel fills the view, so no real floor
GROUND = QColor(31, 31, 31)
SHAPE = QColor(80, 220, 120)
CHOSEN = QColor(255, 200, 80)
DRAFT = QColor(120, 190, 255)
OUTSIDE = QColor(255, 90, 90)


def pixmap_of(bgr):
    h, w = bgr.shape[:2]
    return QPixmap.fromImage(QImage(bgr.data, w, h, bgr.strides[0], QImage.Format.Format_BGR888).copy())


class FrameView(QGraphicsView):
    """`moved` carries the cursor's position in plate pixels, or None off the frame; `zoomed` the
    scale, screen pixels per plate pixel, after each change of it."""
    moved = Signal(object)
    zoomed = Signal(float)

    def __init__(self, editor=None, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.setScene(QGraphicsScene(self))
        self._pix = QGraphicsPixmapItem()
        self._pix.setTransformationMode(Qt.TransformationMode.FastTransformation)   # a zoomed pixel stays one square
        self.scene().addItem(self._pix)
        self.setBackgroundBrush(GROUND)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)   # a scrollbar appearing would shrink fit's viewport
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._fitted = True
        self._space = False
        self._pan = None

    def show_frame(self, bgr):
        resized = self._pix.pixmap().size().toTuple() != (bgr.shape[1], bgr.shape[0])
        self._pix.setPixmap(pixmap_of(bgr))
        if resized:
            self.setSceneRect(self._pix.boundingRect())
            self.fit()

    def scale_now(self):
        return self.transform().m11()

    def fit_scale(self):
        w, h = self._pix.pixmap().size().toTuple()
        vp = self.viewport().size()
        return min(vp.width() / w, vp.height() / h) if w and h else 1.0

    def fit(self):
        self._set_scale(self.fit_scale())
        self.centerOn(self._pix.boundingRect().center())
        self._fitted = True

    def actual(self):
        """One plate pixel to one screen pixel, about the view's centre."""
        centre = self.mapToScene(self.viewport().rect().center())
        self._set_scale(1.0)
        self.centerOn(centre)
        self._fitted = False

    def zoom(self, factor):
        """Scales by `factor` about the cursor, out no further than fit; a frame shown smaller than fit,
        as 100% shows one smaller than the view, zooms out no further than it is."""
        target = min(self.scale_now() * factor, MAX_SCALE)
        if target <= self.fit_scale():
            if self.scale_now() >= self.fit_scale():
                self.fit()
        else:
            self.scale(target / self.scale_now(), target / self.scale_now())
            self._fitted = False
            self.zoomed.emit(self.scale_now())

    def _set_scale(self, s):
        self.resetTransform()
        self.scale(s, s)
        self.zoomed.emit(s)

    def wheelEvent(self, e):
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom(ZOOM_STEP ** (e.angleDelta().y() / 120))
            e.accept()
        else:
            super().wheelEvent(e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._fitted:
            self.fit()

    def keyPressEvent(self, e):
        if self.editor is not None and e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.editor.finish()
        elif self.editor is not None and e.key() == Qt.Key.Key_Escape:
            self.editor.cancel()
        elif self.editor is not None and e.key() == Qt.Key.Key_Shift:
            self.editor.set_squared(True)
        elif e.key() == Qt.Key.Key_Space and not e.isAutoRepeat():
            self._space = True
            self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        if self.editor is not None and e.key() == Qt.Key.Key_Shift:
            self.editor.set_squared(False)
        if e.key() == Qt.Key.Key_Space and not e.isAutoRepeat():
            self._space = False
            self.viewport().unsetCursor()
        super().keyReleaseEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.MiddleButton or (e.button() == Qt.MouseButton.LeftButton and self._space):
            self._pan = (e.button(), e.position())
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            e.accept()
            return
        button = {Qt.MouseButton.LeftButton: "left", Qt.MouseButton.RightButton: "right"}.get(e.button())
        if self.editor is not None and button is not None:
            self.editor.squared = bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            self.editor.press(self._at(e), 1 / self.scale_now(), button)
            e.accept()
            return
        super().mousePressEvent(e)

    def _at(self, e):
        p = self.mapToScene(e.position().toPoint())
        return (p.x(), p.y())

    def mouseMoveEvent(self, e):
        if self._pan is not None:
            d = e.position() - self._pan[1]
            self._pan = (self._pan[0], e.position())
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - round(d.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - round(d.y()))
            e.accept()
            return
        p = self.mapToScene(e.position().toPoint())
        self.moved.emit(p if self._pix.boundingRect().contains(p) else None)
        if self.editor is not None:
            self.editor.squared = bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            self.editor.move((p.x(), p.y()), 1 / self.scale_now())
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._pan is not None and e.button() == self._pan[0]:
            self._pan = None
            if self._space:
                self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.viewport().unsetCursor()
            e.accept()
            return
        if self.editor is not None and e.button() == Qt.MouseButton.LeftButton:
            self.editor.squared = bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            self.editor.release(self._at(e), 1 / self.scale_now())
            e.accept()
            return
        super().mouseReleaseEvent(e)

    def leaveEvent(self, e):
        self.moved.emit(None)
        super().leaveEvent(e)


    def drawForeground(self, painter, rect):
        ed = self.editor
        if ed is None:
            return
        px = 1 / self.scale_now()
        for s in ed.shapes:
            colour = OUTSIDE if not ed.within(s) else CHOSEN if s.name == ed.selected else SHAPE
            self._outline(painter, s, colour, 2 if s.name == ed.selected else 1)
        draft = ed.preview()
        if draft is not None:
            self._outline(painter, draft, DRAFT, 1)
        if ed.pending:
            pen = QPen(DRAFT, 1)
            pen.setCosmetic(True)
            painter.setPen(pen)
            pts = [QPointF(*q) for q in ed.pending] + ([QPointF(*ed.cursor)] if ed.mode == "polygon" and ed.cursor else [])
            if len(pts) > 1:
                painter.drawPolyline(QPolygonF(pts))
            for q in ed.pending:
                self._handle(painter, q, px, DRAFT)
        s = ed.current
        if s is None:
            return
        rot = ed.rotation_handle(px)
        if rot is not None:
            top, _ = s.top()
            pen = QPen(CHOSEN, 1)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.drawLine(QPointF(*top), QPointF(*rot))
            self._handle(painter, rot, px, CHOSEN, round_=True)
        for q in s.handles().values():
            self._handle(painter, q, px, CHOSEN, round_=s.kind == "circle")

    @staticmethod
    def _outline(painter, s, colour, width):
        pen = QPen(colour, width)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if s.kind == "circle":
            painter.drawEllipse(QPointF(s.cx, s.cy), s.r, s.r)
        else:
            path = QPainterPath()
            path.addPolygon(QPolygonF([QPointF(*v) for v in s.vertices()]))
            path.closeSubpath()
            painter.drawPath(path)

    @staticmethod
    def _handle(painter, q, px, colour, round_=False):
        pen = QPen(colour, 1)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(QBrush(GROUND))
        r = HANDLE_PX * px * (0.8 if round_ else 0.7)
        box = QRectF(q[0] - r, q[1] - r, 2 * r, 2 * r)
        painter.drawEllipse(box) if round_ else painter.drawRect(box)
