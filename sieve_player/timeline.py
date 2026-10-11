"""Full-width strip (playhead + loop window) and the control row above it."""
from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QDoubleSpinBox, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
                               QVBoxLayout, QWidget)


def timecode(row, fps):
    s = row / fps if fps else 0.0
    return f"{int(s // 60):02d}:{s % 60:06.3f}"


class Strip(QWidget):
    """Paints what it's told, reports gestures. Owns neither the playhead nor the window."""
    pressed = Signal(int)
    dragged = Signal(int)
    released = Signal(int)
    windowChanged = Signal(int, int)  # start, length (rows)
    H, GRAB = 60, 6

    def __init__(self, parent=None):
        super().__init__(parent)
        self.count, self.fps = 1, 30.0
        self.playhead, self.window = 0, (0, 0)
        self._mode = None        # "head" | "left" | "right" | "body"
        self._draft = None       # (start, length) while a window drag is live
        self._grab = 0           # row offset of the grab point inside the body
        self.setFixedHeight(self.H)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMouseTracking(True)
        self._bubble = QLabel(None, Qt.ToolTip | Qt.FramelessWindowHint)
        self._bubble.setStyleSheet("background:#222;color:#eee;padding:2px 6px;border:1px solid #666")

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

    def _hit(self, x):
        s, n = self.window
        if n <= 0:
            return "head"
        if abs(x - self._x(s)) <= self.GRAB:
            return "left"
        if abs(x - self._x(s + n)) <= self.GRAB:
            return "right"
        if self._x(s) < x < self._x(s + n):
            return "body"
        return "head"

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(40, 40, 40))
        s, n = self._draft or self.window
        if n > 0:
            p.fillRect(QRectF(self._x(s), 0, self._x(s + n) - self._x(s), self.height()), QColor(70, 110, 160))
            p.setPen(QPen(QColor(120, 170, 230), 2))
            for r in (s, s + n):
                p.drawLine(int(self._x(r)), 0, int(self._x(r)), self.height())
        p.setPen(QPen(QColor(255, 200, 60), 2))
        x = int(self._x(self.playhead))
        p.drawLine(x, 0, x, self.height())

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        x, row = e.position().x(), self._row(e.position().x())
        self._mode = self._hit(x)
        if self._mode == "head":
            self.pressed.emit(row)
        else:
            self._draft = self.window
            self._grab = row - self.window[0]
        self._show_bubble(e)

    def mouseMoveEvent(self, e):
        x, row = e.position().x(), self._row(e.position().x())
        if self._mode is None:
            hit = self._hit(x)
            self.setCursor({"left": Qt.SizeHorCursor, "right": Qt.SizeHorCursor,
                            "body": Qt.OpenHandCursor}.get(hit, Qt.ArrowCursor))
            return
        if self._mode == "head":
            self.dragged.emit(row)
        else:
            s, n = self.window
            end = s + n
            if self._mode == "left":
                s = min(row, end - 1)
            elif self._mode == "right":
                end = max(row + 1, s + 1)
            else:
                s = max(0, min(self.count - n, row - self._grab))
                end = s + n
            self._draft = (s, end - s)
            self.update()
        self._show_bubble(e)

    def mouseReleaseEvent(self, e):
        if self._mode is None:
            return
        row = self._row(e.position().x())
        if self._mode == "head":
            self.released.emit(row)
        elif self._draft:
            self.windowChanged.emit(*self._draft)
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
        lay.setContentsMargins(4, 2, 4, 2)
        self.play = QPushButton("Play")
        self.play.setFixedWidth(60)
        back, fwd = QPushButton("−1"), QPushButton("+1")
        for b in (back, fwd):
            b.setFixedWidth(36)
        self.start = QDoubleSpinBox(decimals=3, suffix=" s")
        self.length = QDoubleSpinBox(decimals=3, suffix=" s")
        for sb in (self.start, self.length):
            sb.setKeyboardTracking(False)
        self.readout = QLabel("")
        self.progress = QLabel("")
        for w, t in ((self.play, None), (back, None), (fwd, None), (QLabel("loop start"), None),
                     (self.start, None), (QLabel("length"), None), (self.length, None)):
            lay.addWidget(w)
        lay.addStretch(1)
        lay.addWidget(self.progress)
        lay.addSpacing(12)
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


class Timeline(QWidget):
    """Controls over Strip. Fixed height; never negotiates with the layout above."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.controls, self.strip = Controls(self), Strip(self)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.controls)
        lay.addWidget(self.strip)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
