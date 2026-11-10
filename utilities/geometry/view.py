"""The frame view: one frame as a pixmap in a scene whose units are plate pixels, zoomed about the
cursor with Ctrl and the wheel, never smaller than the whole frame fitting, and panned by the middle
button or by the left with space held, the left button alone being the drawing's."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import QFrame, QGraphicsPixmapItem, QGraphicsScene, QGraphicsView

ZOOM_STEP = 1.25    # scale per wheel notch
MAX_SCALE = 256.0   # screen pixels per plate pixel; past a few dozen a pixel fills the view, so no real floor
GROUND = QColor(31, 31, 31)


def pixmap_of(bgr):
    h, w = bgr.shape[:2]
    return QPixmap.fromImage(QImage(bgr.data, w, h, bgr.strides[0], QImage.Format.Format_BGR888).copy())


class FrameView(QGraphicsView):
    """`moved` carries the cursor's position in plate pixels, or None off the frame."""
    moved = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
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

    def _set_scale(self, s):
        self.resetTransform()
        self.scale(s, s)

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
        if e.key() == Qt.Key.Key_Space and not e.isAutoRepeat():
            self._space = True
            self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e):
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
        super().mousePressEvent(e)

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
        super().mouseReleaseEvent(e)

    def leaveEvent(self, e):
        self.moved.emit(None)
        super().leaveEvent(e)

