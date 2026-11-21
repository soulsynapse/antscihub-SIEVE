"""The transport: a layer-1 box across the bottom, the control row over the full-width strip
(playhead + loop window), which is a layer-2 field inside it. The strip's x axis is the whole clip,
and under its handle it draws every series the plot shows at its rows, the selection in its colour
and the pinned in dimmed ink, each as the plot does over the window: a column covering more than
one row is their min and max, so nothing is hidden and nothing is added, and the rows the
selection's gate keeps are washed. A row absent, NaN, is drawn as nothing. A bar along its top edge is over the rows held, and along its
bottom edge each node that cuts in time has lanes of its own, its periods spans in its colour,
whichever node is the selection."""
import numpy as np
from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QDoubleSpinBox, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget

from typing import NamedTuple

from . import theme
from .theme import GAP, GLYPH, INK, INK_ALPHA, ROW_H, Layer, desc_label, glyph, gray, mono_font, qgray, readout


class Envelope(NamedTuple):
    """One stretch of a series as the strip draws it: the pixel columns its rows fall in and, a
    column each, the min and max of its rows and whether its gate keeps any of them, None with no
    gate; `top` is the value drawn at full height and `selected` whether it is drawn in colour."""
    selected: bool
    top: float
    cols: np.ndarray
    lo: np.ndarray
    hi: np.ndarray
    kept: np.ndarray | None


def present(values, start, gate):
    """[(values, start, gate)] of each run of `values`' rows that is not NaN, an absent row being in none."""
    edges = np.flatnonzero(np.diff(np.concatenate(([0], (~np.isnan(values)).astype(np.int8), [0]))))
    return [(values[a:b], start + a, None if gate is None else gate[a:b]) for a, b in zip(edges[0::2], edges[1::2])]


def envelope(values, start, gate, width, count, selected, top):
    """The Envelope of `values`, rows from `start` of a clip of `count`, over `width` pixel
    columns: row r is in column r * width // count."""
    n = len(values)
    c = np.arange(start * width // count, (start + n - 1) * width // count + 2, dtype=np.int64)
    first = -(-(c * count) // width)       # the first row of each column, and of the one past the last
    a, b = np.maximum(first[:-1], start), np.minimum(first[1:], start + n)
    has = b > a
    starts = (a - start)[has]
    kept = None if gate is None else np.maximum.reduceat(gate[:n].astype(np.uint8), starts) > 0
    return Envelope(selected, top, c[:-1][has], np.minimum.reduceat(values, starts), np.maximum.reduceat(values, starts), kept)


def _differ(a, b):
    return ~((a == b) | ((a != a) & (b != b)))


BACK = 3        # columns of an Envelope before its first altered one that are drawn anew: a line's end drawn on as a join antialiases two columns back
BEYOND = 4      # columns either side of the span drawn that are handed to the painter, so the ends it makes up lie that far outside it


def changed(old, new, width):
    """The pixel columns, (first, one past the last), over which Envelopes `new` draw other than
    `old` did, None where they draw the same: a stretch grown by rows changes from BACK columns
    before its first new or altered one, and a stretch added, gone or drawn another way changes
    the whole."""
    if len(old) != len(new) or any(o.selected != n.selected or (o.kept is None) != (n.kept is None) for o, n in zip(old, new)):
        return (0, width) if old or new else None
    spans = []
    for o, n in zip(old, new):
        m = min(len(o.cols), len(n.cols))
        if o.top != n.top:
            i = 0
        else:
            d = (o.cols[:m] != n.cols[:m]) | _differ(o.lo[:m], n.lo[:m]) | _differ(o.hi[:m], n.hi[:m])
            if o.kept is not None:
                d |= o.kept[:m] != n.kept[:m]
            i = int(np.argmax(d)) if d.any() else m if len(o.cols) != len(n.cols) else None
        if i is not None:
            j = max(i - BACK, 0)
            spans.append((int(min(o.cols[j], n.cols[j])) - 1, int(max(o.cols[-1], n.cols[-1])) + 2))
    return (max(0, min(a for a, _ in spans)), min(width, max(b for _, b in spans))) if spans else None


def lanes(spans):
    """[(node, [(first, end), ...]), ...] of `spans`, {node: [(first, end), ...]}: each node's
    spans laid on the fewest lanes on which none overlaps another, nodes in their order and a
    span on the first lane it fits, one that touches another sharing its lane."""
    out = []
    for nid, ss in spans.items():
        mine = []
        for first, end in sorted(ss):
            lane = next((lane for lane in mine if lane[-1][1] <= first), None)
            if lane is None:
                mine.append(lane := [])
            lane.append((first, end))
        out += [(nid, lane) for lane in mine]
    return out


def timecode(row, fps, places=3):
    s = round(row / fps, places) if fps else 0.0
    return f"{int(s // 60):02d}:{s % 60:0{places + 3}.{places}f}"


class Strip(QWidget):
    """Paints what it's told, reports gestures. Owns neither the playhead nor the window."""
    pressed = Signal(int)
    dragged = Signal(int)
    released = Signal(int)
    windowChanged = Signal(int, int)  # start, length (rows): the handle moved it
    windowPlaced = Signal(int, int)   # start, length (rows): a click in the black put it here
    hovered = Signal(int)             # the row under the cursor, -1 on leave
    H, GRAB = 60, 10  # GRAB: height of the handle along the window's top edge
    HELD = 3          # height of the bar along the top edge over the rows held, drawn over the handle where they meet
    LANE = 3          # height of a lane of periods along the bottom edge, one pixel between lanes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.count, self.fps = 1, 30.0
        self.playhead, self.window = 0, (0, 0)
        self.hover = -1
        self.series, self.selection = {}, None   # node -> (values, start, gate) drawn; the selection's in colour, the rest in ink
        self.more = {}           # node -> its further stretches, see set_series
        self.held = []           # (start, rows) spans drawn along the top edge, see set_held
        self.lanes = []          # (node, [(first, end), ...]) drawn along the bottom edge, see set_periods
        self._lanes = None       # (the size and lanes it was painted for, the pixmap of the lanes alone)
        self._mode = None        # "head" | "body" | "place"
        self._draft = None       # (start, length) while a window drag is live
        self._grab = 0           # row offset of the grab point inside the body
        self._still = None       # (the size it was painted for, the pixmap of the series alone, the Envelopes drawn on it), or None before a paint
        self._asked = True       # the series or the clip's count changed since the pixmap was drawn
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
        self._redraw()

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
        self._redraw()

    def set_held(self, spans):
        """The stretches of the clip, (start, rows) each, a window placed wholly inside one of which
        costs the series chain nothing; drawn as a bar along the top edge."""
        self.held = [(int(s), int(n)) for s, n in spans]
        self.update()

    def set_periods(self, spans):
        """{node: [(first, end), ...]}, the rows of each period a node cuts, drawn along the bottom
        edge in the node's colour, on as many lanes of its own as its periods overlap."""
        was = len(self.lanes)
        self.lanes = lanes({nid: [(int(a), int(b)) for a, b in ss] for nid, ss in spans.items() if ss})
        if len(self.lanes) != was:
            self._still = None      # the series' floor moved, so every column of them is drawn again
        self.update()

    def lane_rect(self, k, first, end):
        """Where lane `k`, counted up from the bottom edge, draws the rows [first, end)."""
        x0 = self._x(first)
        return QRectF(x0, self.height() - 1 - (k + 1) * (self.LANE + 1) + 1, max(1.0, self._x(end) - x0), self.LANE)

    def _lanes_pixmap(self, key):
        if self._lanes is None or self._lanes[0] != (key, self.lanes):
            pix = QPixmap(self.size() * key[1])
            pix.setDevicePixelRatio(key[1])
            pix.fill(Qt.transparent)
            p = QPainter(pix)
            for k, (nid, spans) in enumerate(self.lanes):
                colour = QColor.fromHsv(theme.hashed_hue(nid), *theme.TYPE_SV)
                for first, end in spans:
                    p.fillRect(self.lane_rect(k, first, end), colour)
            p.end()
            self._lanes = ((key, self.lanes), pix)
        return self._lanes[1]

    def _redraw(self):
        """The series or the axis they are drawn on changed: the next paint draws what of them is other than it drew."""
        self._asked = True
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
        # a playhead, a hover or a window that moves must draw no row of any series: the series are a pixmap of their own
        key = (self.size(), self.devicePixelRatioF())
        if self._still is None or self._still[0] != key:
            still = QPixmap(self.size() * key[1])
            still.setDevicePixelRatio(key[1])
            still.fill(Qt.transparent)
            self._still, self._asked = (key, still, []), True
        if self._asked:
            _, still, drawn = self._still
            now = self._envelopes()
            if (span := changed(drawn, now, self.width())) is not None:
                self._paint_series(still, now, span)
            self._still, self._asked = (key, still, now), False
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
        p.drawPixmap(0, 0, self._still[1])
        if self.lanes:
            p.drawPixmap(0, 0, self._lanes_pixmap(key))
        for s, n in self.held:
            x0 = self._x(s)
            p.fillRect(QRectF(x0, 1, max(1.0, self._x(s + n) - x0), self.HELD), qgray(theme.INK_2))
        if self.hover >= 0:
            p.setPen(QPen(qgray(theme.INK_2), 1))
            x = int(self._x(self.hover))
            p.drawLine(x, 1, x, self.height() - 2)
        p.setPen(QPen(qgray(theme.HEAD), 1.5))
        x = int(self._x(self.playhead))
        p.drawLine(x, 1, x, self.height() - 2)

    def _envelopes(self):
        """Every stretch drawn, in the order drawn: the pinned in ink first, the selection over
        them in its colour with its gate's wash; a node's stretches share its largest value."""
        out, w = [], max(1, self.width())
        for nid in [n for n in self.series if n != self.selection] + [n for n in self.series if n == self.selection]:
            segs = [run for seg in [self.series[nid], *self.more.get(nid, [])] for run in present(*seg)]
            top = max((float(values.max()) for values, _, _ in segs if len(values)), default=0.0)
            out += [envelope(values, start, gate if nid == self.selection else None, w, self.count, nid == self.selection, top)
                    for values, start, gate in segs if len(values)]
        return out

    def _paint_series(self, onto, envelopes, span):
        """Draws `envelopes` on `onto` over the pixel columns of `span` alone, cleared first."""
        p = QPainter(onto)
        clip = QRect(span[0], 0, span[1] - span[0], self.height())
        p.setClipRect(clip)
        p.setCompositionMode(QPainter.CompositionMode_Source)
        p.fillRect(clip, Qt.transparent)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        p.setRenderHint(QPainter.Antialiasing, True)
        for e in envelopes:
            self._paint_one(p, e, span)
        p.end()

    def _paint_one(self, p, e, span):
        """The columns of `e` that reach `span`, and BEYOND more either side so what is drawn
        inside is what the whole would draw there: the min and max of each as one polygon scaled to
        its top, the columns its gate keeps washed first. A column that stands alone is a line."""
        a = max(int(np.searchsorted(e.cols, span[0])) - BEYOND, 0)
        b = min(int(np.searchsorted(e.cols, span[1], "right")) + BEYOND, len(e.cols))
        floor = len(self.lanes) * (self.LANE + 1)      # the series end above the lanes, which would hide their lowest values
        inner = QRectF(1, self.GRAB + 2, self.width() - 2, self.height() - self.GRAB - 4 - floor)
        xs = e.cols[a:b] + 0.5
        y = lambda v: inner.bottom() - inner.height() * np.minimum(v[a:b].astype(np.float64) / max(e.top, 1e-6), 1.0)
        lo, hi = y(e.lo), y(e.hi)
        line = qgray(theme.INK, INK_ALPHA) if not e.selected else theme.GATE if e.kept is not None else theme.SERIES
        p.setPen(Qt.NoPen)
        if e.kept is not None:
            edges = np.flatnonzero(np.diff(np.concatenate(([0], e.kept[a:b].astype(np.int8), [0]))))
            p.setBrush(theme.GATED)
            for i, j in zip(edges[0::2], edges[1::2] - 1):
                p.drawRect(QRectF(xs[i] - 0.5, inner.top(), xs[j] - xs[i] + 1, inner.height()))
        p.setPen(QPen(line, 1))
        p.setBrush(line)
        if len(xs) == 1:   # one column: a polygon of one x has no area and no length, so its span is a line
            p.drawLine(QPointF(xs[0], hi[0]), QPointF(xs[0], max(lo[0], hi[0] + 1)))
        else:   # the fill has no outline, which would add a pixel to every column's span; the line along the maxima is what shows where a column's span is nothing
            upper = [QPointF(x, v) for x, v in zip(xs.tolist(), hi.tolist())]
            p.setPen(Qt.NoPen)
            p.drawPolygon(QPolygonF(upper + [QPointF(x, v) for x, v in zip(xs[::-1].tolist(), lo[::-1].tolist())]))
            p.setPen(QPen(line, 1))
            p.setBrush(Qt.NoBrush)
            p.drawPolyline(QPolygonF(upper))

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
            text = timecode(self._draft[0], self.fps, places=1)
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
        self.play = QPushButton()
        self.play.setIconSize(QSize(GLYPH, GLYPH))
        self.set_playing(False)
        back, fwd = QPushButton("−1"), QPushButton("+1")
        for b in (self.play, back, fwd):
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
        self.play.setIcon(QIcon(glyph("player-pause" if on else "player-play", INK, GLYPH, self.devicePixelRatioF())))
        self.play.setToolTip("Pause  (Space)" if on else "Play  (Space)")

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
