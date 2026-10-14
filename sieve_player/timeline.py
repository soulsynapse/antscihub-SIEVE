"""The transport: a layer-1 box across the bottom, the control row over the full-width strip
(playhead + loop window), which is a layer-2 field inside it."""
from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QDoubleSpinBox, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget

from . import theme
from .theme import GAP, ROW_H, Layer, desc_label, gray, mono_font, qgray, readout


def timecode(row, fps):
    s = row / fps if fps else 0.0
    return f"{int(s // 60):02d}:{s % 60:06.3f}"


class Strip(QWidget):
    """Paints what it's told, reports gestures. Owns neither the playhead nor the window."""
    pressed = Signal(int)
    dragged = Signal(int)
    released = Signal(int)
    windowChanged = Signal(int, int)  # start, length (rows): the handle moved it
    windowPlaced = Signal(int, int)   # start, length (rows): a click in the black put it here
    H, GRAB = 60, 10  # GRAB: height of the handle along the window's top edge

    def __init__(self, parent=None):
        super().__init__(parent)
        self.count, self.fps = 1, 30.0
        self.playhead, self.window = 0, (0, 0)
        self._mode = None        # "head" | "body" | "place"
        self._draft = None       # (start, length) while a window drag is live
        self._grab = 0           # row offset of the grab point inside the body
        self.setFixedHeight(self.H)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMouseTracking(True)
        self._bubble = QLabel(None, Qt.ToolTip | Qt.FramelessWindowHint)
        self._bubble.setFont(mono_font())
        self._bubble.setStyleSheet(
            f"background:{gray(theme.layer(2))};color:{gray(theme.INK)};padding:2px 6px;"
            f"border:1px solid {gray(theme.layer(2) + theme.LINE_LIFT)}")

    def set_count(self, count, fps):
        self.count, self.fps = max(1, count), fps
        self.update()

    def set_playhead(self, row):
        self.playhead = row
        self.update()

    def set_window(self, start, length):
        self.window = (start, length)
        self.update()

    def _x(self, row):
        return row / self.count * self.width()

    def _row(self, x):
        return max(0, min(self.count - 1, int(x / max(1, self.width()) * self.count)))

    def _hit(self, x, y):
        """The handle along the window's top moves it, the field outside it places it, the rest
        of the band is the playhead. Lengths are edited in the control row, not here."""
        s, n = self.window
        if n <= 0:
            return "head"
        if not self._x(s) <= x < self._x(s + n):
            return "place"
        return "body" if y <= self.GRAB else "head"

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QPen(qgray(theme.layer(2) + theme.LINE_LIFT), 1))
        p.setBrush(qgray(theme.layer(2)))
        p.drawRoundedRect(box, theme.RADIUS, theme.RADIUS)
        p.setRenderHint(QPainter.Antialiasing, False)
        s, n = self._draft or self.window
        if n > 0:
            x0, x1 = self._x(s), self._x(s + n)   # the viewed stretch: accent wash, accent handle
            a = theme.ACCENT
            p.fillRect(QRectF(x0, 1, x1 - x0, self.height() - 2), QColor(a.red(), a.green(), a.blue(), 40))
            p.fillRect(QRectF(x0, 1, x1 - x0, self.GRAB), a)
        p.setPen(QPen(qgray(theme.HEAD), 1.5))
        x = int(self._x(self.playhead))
        p.drawLine(x, 1, x, self.height() - 2)

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        row = self._row(e.position().x())
        self._mode = self._hit(e.position().x(), e.position().y())
        if self._mode == "head":
            self.pressed.emit(row)
        elif self._mode == "body":
            self._draft = self.window
            self._grab = row - self.window[0]
        else:  # the window's front jumps to the click and the press goes on as a drag
            n = self.window[1]
            self._draft, self._grab = (max(0, min(self.count - n, row)), n), 0
            self.update()
        self._show_bubble(e)

    def mouseMoveEvent(self, e):
        row = self._row(e.position().x())
        if self._mode is None:
            hit = self._hit(e.position().x(), e.position().y())
            self.setCursor(Qt.OpenHandCursor if hit == "body" else Qt.ArrowCursor)
            return
        if self._mode == "head":
            self.dragged.emit(row)
        else:
            n = self.window[1]
            self._draft = (max(0, min(self.count - n, row - self._grab)), n)
            self.update()
        self._show_bubble(e)

    def mouseReleaseEvent(self, e):
        if self._mode is None:
            return
        row = self._row(e.position().x())
        if self._mode == "head":
            self.released.emit(row)
        elif self._draft:
            (self.windowPlaced if self._mode == "place" else self.windowChanged).emit(*self._draft)
        self._mode, self._draft = None, None
        self._bubble.hide()
        self.update()

    def leaveEvent(self, _):
        if self._mode is None:
            self._bubble.hide()

    def _show_bubble(self, e):
        row = self._row(e.position().x())
        text = f"{row}  {timecode(row, self.fps)}"
        if self._draft:
            s, n = self._draft
            text = f"[{s} .. {s + n})  {timecode(s, self.fps)} + {n / self.fps:.2f}s"
        self._bubble.setText(text)
        self._bubble.adjustSize()
        g = self.mapToGlobal(QPoint(int(e.position().x()), 0))
        self._bubble.move(g.x() - self._bubble.width() // 2, g.y() - self._bubble.height() - 4)
        self._bubble.show()


class Controls(QWidget):
    playToggled = Signal()
    step = Signal(int)
    windowEdited = Signal(float, float)  # start s, length s

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fps = 30.0
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(GAP)
        self.play = QPushButton("Play")
        self.play.setFixedWidth(60)
        back, fwd = QPushButton("−1"), QPushButton("+1")
        for b in (back, fwd):
            b.setFixedWidth(36)
        self.start = QDoubleSpinBox(decimals=3, suffix=" s")
        self.length = QDoubleSpinBox(decimals=3, suffix=" s")
        for sb in (self.start, self.length):
            sb.setKeyboardTracking(False)
            sb.setFixedWidth(90)   # not a form: room for mmm.mmm s, no more
        self.readout = readout(mono=True, wrap=False)
        self.progress = readout(mono=True, wrap=False)
        for w in (self.play, back, fwd, desc_label("loop start"), self.start, desc_label("length"), self.length):
            w.setFixedHeight(ROW_H)
            lay.addWidget(w)
        lay.addStretch(1)
        lay.addWidget(self.progress)
        lay.addSpacing(GAP)
        lay.addWidget(self.readout)
        self.play.clicked.connect(self.playToggled)
        back.clicked.connect(lambda: self.step.emit(-1))
        fwd.clicked.connect(lambda: self.step.emit(1))
        self.start.valueChanged.connect(self._edited)
        self.length.valueChanged.connect(self._edited)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def _edited(self, _):
        self.windowEdited.emit(self.start.value(), self.length.value())

    def set_count(self, count, fps):
        self.fps = fps
        self.start.setRange(0, count / fps)
        self.length.setRange(1 / fps, count / fps)
        self.start.setSingleStep(1 / fps)
        self.length.setSingleStep(1 / fps)

    def set_window(self, start, length):
        for sb, v in ((self.start, start / self.fps), (self.length, length / self.fps)):
            sb.blockSignals(True)
            sb.setValue(v)
            sb.blockSignals(False)

    def set_playing(self, on):
        self.play.setText("Pause" if on else "Play")

    def set_readout(self, row):
        self.readout.setText(f"row {row}   {timecode(row, self.fps)}   {self.fps:.2f} fps")

    def set_progress(self, done, total):
        self.progress.setText(f"window {done}/{total}" if done < total else "")


class Timeline(Layer):
    """Controls over Strip in one unnamed layer-1 box. Fixed height; never negotiates with the
    layout above."""

    def __init__(self, parent=None):
        super().__init__(1, parent=parent)
        self.controls, self.strip = Controls(self), Strip(self)
        self.add(self.controls)
        self.add(self.strip)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
