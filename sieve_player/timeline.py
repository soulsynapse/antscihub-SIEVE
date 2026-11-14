"""The transport: a layer-1 box across the bottom, the control row over the full-width strip
(playhead + loop window), which is a layer-2 field inside it. The strip's x axis is the whole clip,
and under its handle it draws every series the plot shows at its rows, the selection in its colour
and the pinned in dimmed ink, each as the plot does over the window: a column covering more than
one row is their min and max, so nothing is hidden and nothing is added, and the rows the
selection's gate keeps are washed. A bar along its bottom edge is over the rows held."""
import numpy as np
from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QDoubleSpinBox, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget

from . import theme
from .theme import GAP, INK_ALPHA, ROW_H, Layer, desc_label, gray, mono_font, qgray, readout


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
    hovered = Signal(int)             # the row under the cursor, -1 on leave
    H, GRAB = 60, 10  # GRAB: height of the handle along the window's top edge
    HELD = 3          # height of the bar along the bottom edge over the rows held

    def __init__(self, parent=None):
        super().__init__(parent)
        self.count, self.fps = 1, 30.0
        self.playhead, self.window = 0, (0, 0)
        self.hover = -1
        self.series, self.selection = {}, None   # node -> (values, start, gate) drawn; the selection's in colour, the rest in ink
        self.more = {}           # node -> its further stretches, see set_series
        self.held = []           # (start, rows) spans drawn along the bottom edge, see set_held
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

    def set_hover(self, row):
        self.hover = row
        self.update()

    def set_series(self, series, selection=None, more=None):
        """The signals drawn under the handle, {node: (values, start, gate)}, each from its own row
        `start`; `selection` names the one drawn in the series colour, the rest are dimmed ink. {}
        draws none. `more` is {node: [(values, start, gate), ...]}, the same node's signal over
        other stretches of the clip, drawn as its first is; a node's stretches share one scale,
        the largest value among them."""
        cast = lambda v, start, g: (np.asarray(v, np.float32), int(start), None if g is None else np.asarray(g, bool))
        self.series = {nid: cast(*seg) for nid, seg in series.items()}
        self.more = {nid: [cast(*seg) for seg in segs] for nid, segs in (more or {}).items() if nid in self.series}
        self.selection = selection
        self.update()

    def set_held(self, spans):
        """The stretches of the clip, (start, rows) each, a window placed wholly inside one of which
        costs the series chain nothing; drawn as a bar along the bottom edge."""
        self.held = [(int(s), int(n)) for s, n in spans]
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
        self._paint_series(p)
        for s, n in self.held:
            x0 = self._x(s)
            p.fillRect(QRectF(x0, self.height() - 1 - self.HELD, max(1.0, self._x(s + n) - x0), self.HELD), qgray(theme.INK_2))
        if self.hover >= 0:
            p.setPen(QPen(qgray(theme.INK_2), 1))
            x = int(self._x(self.hover))
            p.drawLine(x, 1, x, self.height() - 2)
        p.setPen(QPen(qgray(theme.HEAD), 1.5))
        x = int(self._x(self.playhead))
        p.drawLine(x, 1, x, self.height() - 2)

    def _paint_series(self, p):
        """The pinned in ink first, the selection over them in its colour with its gate's wash."""
        p.setRenderHint(QPainter.Antialiasing, True)
        for nid in [n for n in self.series if n != self.selection] + [n for n in self.series if n == self.selection]:
            segs = [self.series[nid], *self.more.get(nid, [])]
            top = max((float(values.max()) for values, _, _ in segs if len(values)), default=0.0)
            for values, start, gate in segs:
                if nid == self.selection:
                    self._paint_one(p, values, start, gate, theme.GATE if gate is not None else theme.SERIES, top)
                else:
                    self._paint_one(p, values, start, None, qgray(theme.INK, INK_ALPHA), top)
        p.setRenderHint(QPainter.Antialiasing, False)

    def _paint_one(self, p, values, start, gate, line, top):
        """Each pixel column the values cover: the min and max of its rows, as one polygon scaled
        to `top`; the columns whose gate keeps any row, washed first. A row that stands alone in
        its column is a point of the line."""
        if not len(values):
            return
        inner = QRectF(1, self.GRAB + 2, self.width() - 2, self.height() - self.GRAB - 4)
        n, w = len(values), max(1, self.width())
        col = (start + np.arange(n)) * w // self.count
        starts = np.flatnonzero(np.diff(col, prepend=-1))
        xs = col[starts] + 0.5
        top = max(top, 1e-6)
        y = lambda v: inner.bottom() - inner.height() * min(float(v) / top, 1.0)
        p.setPen(Qt.NoPen)
        if gate is not None:
            kept = np.maximum.reduceat(gate[:n].astype(np.uint8), starts) > 0
            edges = np.flatnonzero(np.diff(np.concatenate(([0], kept.astype(np.int8), [0]))))
            p.setBrush(theme.GATED)
            for a, b in zip(edges[0::2], edges[1::2] - 1):
                p.drawRect(QRectF(xs[a] - 0.5, inner.top(), xs[b] - xs[a] + 1, inner.height()))
        lo, hi = np.minimum.reduceat(values, starts), np.maximum.reduceat(values, starts)
        p.setPen(QPen(line, 1))
        p.setBrush(line)
        if len(xs) == 1:   # one column: a polygon of one x has no area and no length, so its span is a line
            p.drawLine(QPointF(xs[0], y(hi[0])), QPointF(xs[0], max(y(lo[0]), y(hi[0]) + 1)))
        else:
            p.drawPolygon(QPolygonF([QPointF(x, y(v)) for x, v in zip(xs, hi)]
                                    + [QPointF(x, y(v)) for x, v in zip(xs[::-1], lo[::-1])]))

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
            if row != self.hover:
                self.hover = row
                self.update()
                self.hovered.emit(row)
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
        if self.hover != -1:
            self.hover = -1
            self.update()
            self.hovered.emit(-1)

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
        lay.addSpacing(GAP)
        lay.addWidget(self.readout)
        lay.addStretch(1)
        lay.addWidget(self.progress)
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
        self.readout.setText(f"{timecode(row, self.fps)}   {self.fps:.2f} fps   row {row}")

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
