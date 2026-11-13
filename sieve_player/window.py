"""The window: the header across the top, the frame over the plot left, the canvas over the
parameter pane right, the transport across the bottom.

The document is the one source of truth. The canvas and the pane read and write it and say what
changed; the window carries the change to the runtime, built on every load of a video and
re-synced on every change, and carries the runtime's results and standings back to the widgets.
The display reads the memo and never waits on the decoder. It opens on whatever the document names, or empty, and never prompts.
"""
import os
import sys
import time
import traceback

import cv2
import numpy as np
from PySide6.QtCore import QFileSystemWatcher, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QFontMetrics, QImage, QKeySequence, QPainter, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import QAbstractButton, QFileDialog, QHBoxLayout, QMainWindow, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from . import dev, document, store, theme
from .canvas import Canvas
from .decoder import Decoder
from .graph import Graph
from .ledger import Ledger
from .pace import Pace, clock
from .pane import Pane
from .registry import CATEGORIES, Entry, category, description, signature
from .theme import GAP, PAD, ROW_H, readout
from .timeline import Timeline
from .trace import Dump
from .plot import Plot, Stage
from .worker import Worker

DUMP_ENV = "SIEVE_DUMP"     # names the file every video opened in this process dumps its stream to
MEMO_ENV, CACHE_ENV = "SIEVE_MEMO_GB", "SIEVE_CACHE_GB"   # the memo's and the decoder cache's limits; unset, each class's default


def _gb(env):
    """The limit in bytes the variable names, or None for the default; a value that is not a number reads as unset."""
    try:
        return int(float(os.environ[env]) * 2**30)
    except (KeyError, ValueError):
        return None


class Lateness(QTimer):
    """Samples how late the GUI thread's timer fires, to `sample(name, value, t)`: a tick that lands
    long after it was due says the main thread was blocked that long, by what the stream's "slot"
    and "paint" spans may show. It lives here and not in the probe since the probe carries what its
    site knows and measures nothing. It draws nothing."""

    def __init__(self, sample, interval_ms=100, parent=None):
        super().__init__(parent)
        self.sample, self._due = sample, None
        self.setTimerType(Qt.PreciseTimer)
        self.timeout.connect(self._fired)
        self.start(interval_ms)

    def _fired(self):
        now = time.perf_counter()
        if self._due is not None:
            self.sample("late", max(0.0, (now - self._due) * 1000), now)
        self._due = now + self.interval() / 1000

DOCUMENT_FILTER = "SIEVE document (*.json);;All (*)"


def _same(a, b):
    """Whether two paths name one file, as far as their text says."""
    return os.path.normcase(os.path.abspath(str(a))) == os.path.normcase(os.path.abspath(str(b)))


def flow_top(a):
    """The largest magnitude in a flow field, or of a plane; what a non-uint8 array is shown against."""
    a = np.asarray(a)
    if not a.size:
        return 0.0
    return float(np.hypot(a[..., 0], a[..., 1]).max()) if a.ndim == 3 and a.shape[2] == 2 else float(a.max())


def imageable(a):
    """Whether `to_qimage` can show `a`: a plane, a BGR image or a flow field, never a table."""
    a = np.asarray(a)
    return a.dtype.fields is None and (a.ndim == 2 or (a.ndim == 3 and a.shape[2] in (2, 3)))


def to_qimage(a, top=None):
    """`a` as an image. uint8 and bool are shown as they are; any other plane is shown over `top`, its
    own maximum when not given. A flow field, (H, W, 2), is the colour wheel: hue is direction and
    brightness magnitude over `top`."""
    a = np.asarray(a)
    if a.dtype == bool:
        a = a.astype(np.uint8) * 255
    elif a.ndim == 3 and a.shape[2] == 2:
        mag = np.hypot(a[..., 0], a[..., 1])
        top = max(flow_top(a) if top is None else float(top), 1e-6)
        hsv = np.dstack([(np.degrees(np.arctan2(a[..., 1], a[..., 0])) % 360.0) / 2.0,
                         np.full(mag.shape, 255.0), np.clip(mag * (255.0 / top), 0, 255)]).astype(np.uint8)
        a = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    elif a.dtype != np.uint8:
        a = over(a, flow_top(a) if top is None else top)
    a = np.ascontiguousarray(a)
    if a.ndim == 2:
        fmt = QImage.Format_Grayscale8
    elif a.ndim == 3 and a.shape[2] == 3:
        fmt = QImage.Format_BGR888
    else:
        raise ValueError(f"cannot display array of shape {a.shape}")
    return QImage(a.data, a.shape[1], a.shape[0], a.strides[0], fmt).copy()


def over(a, top):
    """`a`, a measured plane, as uint8 over `top`: 0 at or below zero, 255 at `top` and above."""
    a = np.asarray(a).astype(np.float32, copy=False)
    return cv2.convertScaleAbs(cv2.max(a, 0.0), alpha=255.0 / max(float(top), 1e-6))   # abs, so zero the negatives first


# BGRA LUT over theme.HEAT: the colour by value, alpha with it up to theme.HEAT_ALPHA. One cv2.LUT
# over a four-channel index, in place of numpy fancy indexing and a dstack, which cost ~6x.
_HEAT = np.dstack([np.stack([np.interp(np.linspace(0, 1, 256), np.linspace(0, 1, len(theme.HEAT)), [c[k] for c in theme.HEAT])
                             for k in (2, 1, 0)], axis=1).reshape(256, 1, 3),
                   (np.arange(256) * theme.HEAT_ALPHA).reshape(256, 1, 1)]).astype(np.uint8)


def heat(a, top):
    """`a`, one plane, as a BGRA image: colour from _HEAT by value over `top`, alpha with it up to
    theme.HEAT_ALPHA, so what is zero is clear. A bool plane is a mask: full heat where set."""
    a = np.asarray(a)
    if a.ndim != 2:
        raise ValueError(f"cannot overlay array of shape {a.shape}")
    v = a.view(np.uint8) * np.uint8(255) if a.dtype == bool else over(a, top)
    bgra = cv2.LUT(cv2.merge((v, v, v, v)), _HEAT)   # GRAY2BGRA would fix alpha at 255, so merge
    return QImage(bgra.data, a.shape[1], a.shape[0], bgra.strides[0], QImage.Format_ARGB32).copy()


RELOAD_SETTLE_MS = 150   # a loader re-reads a changed file this long after the last write seen


class Display(QWidget):
    drawFailed = Signal(str, str)   # a tool's draw() or pick() raised: the node, the line
    picked = Signal(str, dict)      # a drawer claimed a left click: the node, the params to merge
    back = Signal()                 # a right click: show the node shown before this one

    """The frame, the overlay heated over it, the gate border, and each drawing node's draw() on
    top, in node order, each handed its own node's result: a series node's over the window, a
    frame node's at the row. A left click is offered to the drawers whose pick() claims it, the
    one drawn last first; a right click asks for the node shown before."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pix, self.gate, self.reason = None, False, ""
        self._over, self._over_key, self._top = None, None, 0.0   # the overlay image, whose node's key, its running max
        self._frame_key, self._frame_top = None, 0.0               # the shown node's key and running max, for a measured plane
        self.drawers, self.row, self.results, self.start = [], 0, {}, 0   # drawers: [(node id, tool, node)]
        self.dropped = set()                                       # id() of each tool whose draw() or pick() raised; the window keeps them out of drawers
        self.frame_results = {}                                    # node id -> a drawing frame node's output at the row
        self.setMinimumSize(160, 120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_state(self, row, results, start):
        self.row, self.results, self.start = row, results, start
        self.update()

    def set_frame(self, a, key=None):
        """`a` is the shown node's output at the row. `key` names the node and its params: a plane that
        is a measure rather than an image is shown over a running maximum that restarts when it changes,
        as the overlay is heated, so brightness means the same thing from one row to the next."""
        if key != self._frame_key:
            self._frame_key, self._frame_top = key, 0.0
        a = np.asarray(a)
        top = None
        if a.dtype not in (np.uint8, bool):
            self._frame_top = top = max(self._frame_top, flow_top(a))
        self._pix, self.reason = QPixmap.fromImage(to_qimage(a, top)), ""
        self.update()

    def clear(self, reason=""):
        """No frame; `reason` is the one line that says why, so an empty frame never reads as a stall."""
        self._pix, self.reason = None, reason
        self.set_overlay(None, None)

    def set_overlay(self, a, key):
        """`a` is the overlay node's plane at the shown row, or None for no overlay. `key` names the
        node and its params: the running maximum a gray plane is heated against restarts when it changes."""
        if key != self._over_key:
            self._over_key, self._top = key, 0.0
        if a is None:
            self._over = None
        else:
            a = np.asarray(a)
            if a.dtype != bool:
                self._top = max(self._top, float(a.max()) if a.size else 0.0)
            self._over = heat(a, self._top)
        self.update()

    def set_gate(self, on):
        if on != self.gate:
            self.gate = on
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), theme.qgray(theme.GROUND))
        if self._pix is None:
            if self.reason:
                p.setPen(theme.qgray(theme.INK_2))
                p.drawText(self.rect(), Qt.AlignCenter, self.reason)
            return
        shrinking = self._pix.width() > self.width() or self._pix.height() > self.height()
        # nearest-neighbour drops rows and columns when shrinking, which reads as stripes; grown, it shows each pixel as it is
        x, y, w, h = self.frame_rect()
        pix = self._pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation if shrinking else Qt.FastTransformation)
        p.drawPixmap(x, y, pix)
        if self._over is not None:
            p.drawImage(QRectF(x, y, pix.width(), pix.height()), self._over)   # stretched to the frame, as draw() is
        if self.gate:
            p.setPen(QPen(theme.GATE, 4))
            p.drawRect(x + 2, y + 2, pix.width() - 4, pix.height() - 4)
        if not self.drawers:
            return
        p.save()
        # Window/viewport rather than translate/scale: the same mapping, and a drawer can read the
        # frame's rect back from painter.window() when its own data is another resolution.
        p.setViewport(x, y, pix.width(), pix.height())
        p.setWindow(0, 0, self._pix.width(), self._pix.height())
        for nid, tool, node in self.drawers:
            try:
                tool.draw(p, self.row, self.frame_results.get(nid, self.results.get(nid)), self.start, node.params)
            except Exception as e:
                traceback.print_exc()
                self.drop(tool)
                self.drawFailed.emit(nid, f"draw() raised: {type(e).__name__}: {e}")
        p.restore()

    def drop(self, tool):
        """A tool whose draw() or pick() raised is out of the drawers for the session, through every
        rebuild of the list."""
        self.dropped.add(id(tool))
        self.drawers = [d for d in self.drawers if d[1] is not tool]

    def frame_rect(self):
        """Where the frame sits in the widget, (x, y, width, height): fit inside, centred, or None with no frame."""
        if self._pix is None:
            return None
        scaled = self._pix.size().scaled(self.size(), Qt.KeepAspectRatio)
        return (self.width() - scaled.width()) // 2, (self.height() - scaled.height()) // 2, scaled.width(), scaled.height()

    def to_frame(self, pos):
        """A widget point as (x, y) in the frame's pixels, or None off the frame."""
        r = self.frame_rect()
        if r is None:
            return None
        x, y, w, h = r
        fx, fy = (pos.x() - x) * self._pix.width() / w, (pos.y() - y) * self._pix.height() / h
        return (fx, fy) if 0 <= fx < self._pix.width() and 0 <= fy < self._pix.height() else None

    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton:
            self.back.emit()
            return
        if e.button() != Qt.LeftButton or (point := self.to_frame(e.position())) is None:
            return
        shape = (self._pix.height(), self._pix.width())
        for nid, tool, node in reversed(self.drawers):
            pick, result = getattr(tool, "pick", None), self.frame_results.get(nid, self.results.get(nid))
            if pick is None or result is None:
                continue
            try:
                answer = pick(point, shape, self.row, result, node.params)
            except Exception as exc:
                traceback.print_exc()
                self.drop(tool)
                self.drawFailed.emit(nid, f"pick() raised: {type(exc).__name__}: {exc}")
                continue
            if answer is not None:
                self.picked.emit(nid, dict(answer))
                return


def catalogue(items):
    """`items` are tool modules or registry entries. Returns (modules, name to module, name to
    error): the tools, the catalogue the document's names index, and the tools the registry listed
    but could not import, which the canvas's menu shows greyed."""
    modules, broken = [], {}
    for t in items:
        if isinstance(t, Entry):
            if t.ok:
                modules.append(t.module)
            else:
                broken[t.name] = t.error
        else:
            modules.append(t)
    return modules, {t.NAME: t for t in modules}, broken


class PaceControl(QAbstractButton):
    """A pace.Figure as one control, drawn and not written: the lane's glyph, the rate as a multiple
    of realtime, a bar and a time. The bar's width is the range and its filled part the rows done,
    cut by what they were: those a store held dim, those that ran bright, those that read a bake
    hatched, in that order and not at the rows' places, the figure holding counts. The time is under
    the glyph of what it is, the clip at this rate, the clip walk's rest or what it took, and a dash
    where the figure gives none. The tooltip is the figure's words. Its width never follows its text."""
    BAR_W, BAR_H, EDGE = 140, 8, 6
    LANES = {"window": "brackets-contain", "clip": "movie"}
    TIMES = {"takes": "clock", "left": "hourglass", "took": "circle-check"}
    HELD = 105      # a held row's gray, between the bar's ground and a row that ran

    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = None
        self.setFont(theme.mono_font())
        fm = QFontMetrics(self.font())
        self._rate_w, self._time_w = fm.horizontalAdvance("00.0×"), fm.horizontalAdvance("0:00:00")
        self.setFixedSize(3 * self.EDGE + 2 * theme.GLYPH + self._rate_w + self.BAR_W + 2 * GAP + 4 + self._time_w, ROW_H)
        self.setAttribute(Qt.WA_Hover, True)
        self.setCursor(Qt.PointingHandCursor)

    def set_figure(self, figure):
        """`figure`, a pace.Figure, or None for no walk to show."""
        self.figure = figure
        self.setToolTip("" if figure is None else figure.words() + "\nclick for the monitor")
        self.update()

    def paintEvent(self, event):
        del event
        f = self.figure
        if f is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        base = theme.layer(theme.depth_of(self) + 1)
        if self.underMouse() and self.isEnabled():
            p.setPen(QPen(theme.qgray(base + theme.LINE_LIFT).lighter(theme.HOVER_EDGE), 1))
            p.setBrush(theme.qgray(base + theme.HOVER_LIFT))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), theme.RADIUS, theme.RADIUS)
        ratio, h, top = self.devicePixelRatioF(), self.height(), (self.height() - theme.GLYPH) / 2
        dim = theme.INK_2 - 50
        x = self.EDGE
        p.drawPixmap(QPointF(x, top), theme.glyph(self.LANES[f.lane], theme.INK_2, theme.GLYPH, ratio))
        x += theme.GLYPH + self.EDGE
        p.setFont(self.font())
        p.setPen(theme.qgray(theme.INK if f.multiple is not None else dim))
        rate = "–" if f.multiple is None else f"{f.multiple:.1f}×" if f.multiple < 100 else f"{f.multiple:.0f}×"
        p.drawText(QRectF(x, 0, self._rate_w, h), Qt.AlignRight | Qt.AlignVCenter, rate)
        x += self._rate_w + GAP
        bar = QRectF(x, (h - self.BAR_H) / 2, self.BAR_W, self.BAR_H)
        p.setRenderHint(QPainter.Antialiasing, False)
        p.fillRect(bar, theme.qgray(theme.GROUND - theme.STEP))
        at = bar.left()
        for rows, brush in ((f.held, theme.qgray(self.HELD)), (f.ran, theme.qgray(theme.INK)), (f.served, None)):
            w = self.BAR_W * rows / f.total if f.total else 0
            if brush is None:
                p.fillRect(QRectF(at, bar.top(), w, self.BAR_H), theme.qgray(self.HELD - 45))
                brush = QBrush(theme.qgray(theme.INK), Qt.BDiagPattern)
            p.fillRect(QRectF(at, bar.top(), w, self.BAR_H), brush)
            at += w
        p.setPen(QPen(theme.qgray(base + theme.LINE_LIFT), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(bar.adjusted(0, 0, -1, -1))
        p.setRenderHint(QPainter.Antialiasing, True)
        x += self.BAR_W + GAP
        name = self.TIMES.get(f.what, "clock" if f.lane == "window" else "hourglass")
        p.drawPixmap(QPointF(x, top), theme.glyph(name, theme.INK_2 if f.what else dim, theme.GLYPH, ratio))
        x += theme.GLYPH + 4
        p.setPen(theme.qgray(theme.INK if f.what else dim))
        p.drawText(QRectF(x, 0, self._time_w, h), Qt.AlignLeft | Qt.AlignVCenter, clock(f.seconds) if f.what else "–")
        p.end()

    def event(self, e):
        if e.type() in (e.Type.HoverEnter, e.Type.HoverLeave):
            self.update()
        return super().event(e)


class Header(QWidget):
    """The row across the top: the store's folder, what it holds and what the disk has free with the
    button that changes it, at the left; the walk's figure, what the clip walk has to say and its
    button, at the right."""

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(GAP)
        self.store_note = readout(mono=True, wrap=False)
        self.store = QPushButton("Store…")
        self.store.setFixedSize(80, ROW_H)
        self.note = readout(mono=True, wrap=False)
        self.note.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.figure = PaceControl()
        self.walk = QPushButton("Walk clip")
        self.walk.setFixedSize(80, ROW_H)
        lay.addWidget(self.store)
        lay.addWidget(self.store_note)
        lay.addStretch(1)
        lay.addWidget(self.note)
        lay.addWidget(self.figure)
        lay.addWidget(self.walk)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def show_store(self, st, refused=""):
        """`st`, the Store the player writes to, as its line reads it; `refused` is why a choice was not taken."""
        held, free = st.status()
        n, stray = st.strays()
        line = f"{st.folder}  holds {store.fmt_bytes(held)}, {store.fmt_bytes(free)} free"
        if n:
            line += f"; {n} part file{'s' if n > 1 else ''} of a bake that died with its process, {store.fmt_bytes(stray)}"
        self.store_note.setText(f"{refused}; {line}" if refused else line)
        self.store_note.setToolTip(st.folder)

    def set_walking(self, on):
        self.walk.setText("Stop walk" if on else "Walk clip")

    def clear_note(self):
        self.note.setText("")


class Column(QWidget):
    """The right side: the canvas over the pane. The pane takes the height its content asks for, up
    to `SHARE` of the column, and the canvas the rest; nothing is dragged between them."""
    SHARE = 0.5

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(GAP)
        self.capped = None

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.capped is not None:
            self.capped.setMaximumHeight(int(self.height() * self.SHARE))


class PlayerWindow(QMainWindow):
    def __init__(self, source, title="SIEVE", tools=(), log=None):
        """`source` is a list of tools, which become the document, or the path of a saved document.
        The catalogue the Tab menu offers and the document's names index is `tools`, plus the list
        when `source` is one. Either list holds tool modules or registry entries; see `catalogue`.
        `log` names where stderr also goes, for a line that sends the user there."""
        super().__init__()
        self.title, self.log = title, log or "stderr"
        self.setStyleSheet(theme.sheet())
        from_file = isinstance(source, (str, os.PathLike))
        modules, self.tools, broken = catalogue(list(tools) if from_file else [*source, *tools])
        if not from_file:
            modules = catalogue(source)[0]
        self.doc = None
        self.decoder = self.graph = self.worker = None
        self.ledger = self.lateness = None        # the open video's stream kept over time, and the GUI thread's sampler into it
        self.pace = None                          # the open video's walks as the header's figure reads them
        self.dump = None                          # the stream's file, while DUMP_ENV names one
        self.fps, self.count = 30.0, 0
        self.row, self.playing, self.window_ = 0, False, (0, 0)
        self._resume = False  # playback to restore when a playhead drag ends
        self.results, self.result_start = {}, 0   # node id -> the series chain's results, and the row they start at
        self.clip_results = {}                    # the same over the clip walk's rows, from row 0; {} when there are none
        self._clip_asked = False                  # a clip walk was asked for and has not finished or been stopped
        self._taken = {}      # (node id, path input) -> (the file last handed to its loader, its mtime)
        self._watch = QFileSystemWatcher(self)
        self._watch.fileChanged.connect(self._path_changed)
        self._watch.directoryChanged.connect(self._path_changed)
        self._reload = QTimer(self)      # a save is often several writes; the loaders run once they settle
        self._reload.setSingleShot(True)
        self._reload.setInterval(RELOAD_SETTLE_MS)
        self._reload.timeout.connect(self._pick_paths)
        self._driven = {}      # (node id, path input) -> (the keys its loader set, the selector's id)
        self._gone = {}        # node -> why its bake could not be read when the document opened, for the graph's notes
        self.store = store.current()   # where bakes land and are read from; Store… replaces it

        self.display = Display()
        self.plot = Plot()
        self.canvas = Canvas(self.tools, broken, {n: (category(t), description(t), signature(t)) for n, t in self.tools.items()}, CATEGORIES)
        self.pane = Pane(self.tools)
        self.timeline = Timeline()
        for part, w in (("frame", self.display), ("plot", self.plot), ("strip", self.timeline.strip), ("canvas", self.canvas)):
            w.paintEvent = self._timed("paint", part, w.paintEvent)
        # an empty selection leaves the pane and the plot on their last node, so a click on empty canvas never blanks them
        self.canvas.selectionChanged.connect(lambda ids: ids and self._select(ids[-1]))
        self.canvas.changed.connect(self.sync)
        self.canvas.flagged.connect(self.reflag)
        self.pane.paramsChanged.connect(self._params_changed)
        self.pane.videoPicked.connect(self.load)
        self.plot.pressed.connect(self._scrub_begin)
        self.plot.dragged.connect(lambda r: self.seek(r, commit=False))
        self.plot.released.connect(self._scrub_end)
        self.plot.hovered.connect(self._hover)
        self.plot.bandDragged.connect(self._band_dragged)
        self.plot.bandReleased.connect(self._band_released)
        self.plot.chipClicked.connect(lambda nid: self.canvas.select([nid]))
        self.plot.pinToggled.connect(self._toggle_pin)
        self.pane.bakeAsked.connect(lambda nid: self.worker is not None
                                    and self.worker.bake(nid, os.path.basename(self.doc.path or "")))
        self.pane.bakeCancelled.connect(lambda nid: self.worker is not None and self.worker.cancel_bake())
        self.pane.modeToggled.connect(self._toggle_mode)
        self.display.drawFailed.connect(self._draw_failed)
        self.display.picked.connect(self._picked)
        self.display.back.connect(self._back)
        self._shown_before = []    # the display flag's past, most recent last, for a right click; the document's session
        self._shown_last = None
        self.selection = None      # the node the canvas last selected, whose settings the pane shows and whose axis the plot draws
        self.header = Header()
        self.header.show_store(self.store)
        self.header.store.clicked.connect(self._choose_store)
        self.header.walk.clicked.connect(self._toggle_clip)
        self.header.figure.clicked.connect(lambda: dev.show(self, "monitor"))
        self.header.setEnabled(False)

        right = Column()
        right.lay.addWidget(self.canvas, 1)
        right.lay.addWidget(self.pane, 0)
        right.capped = self.pane
        self.stage = Stage(self.display, self.plot)
        split = theme.Splitter(Qt.Horizontal)
        split.setHandleWidth(GAP)
        split.addWidget(self.stage)
        split.addWidget(right)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 1)
        self.split = split
        self._split_moved = False
        split.splitterMoved.connect(lambda *_: setattr(self, "_split_moved", True))
        central = QWidget()
        lay = QVBoxLayout(central)
        lay.setContentsMargins(PAD, PAD, PAD, PAD)
        lay.setSpacing(GAP)
        lay.addWidget(self.header, 0)
        lay.addWidget(split, 1)
        lay.addWidget(self.timeline, 0)
        self.setCentralWidget(central)

        menu = self.menuBar().addMenu("File")
        menu.addAction("Open…", QKeySequence.Open, self._open_dialog)
        menu.addAction("Save", QKeySequence.Save, self.save_document)
        menu.addAction("Save As…", QKeySequence.SaveAs, self._save_as)
        dev.install(self)

        st, ct = self.timeline.strip, self.timeline.controls
        st.pressed.connect(self._scrub_begin)
        st.dragged.connect(lambda r: self.seek(r, commit=False))
        st.released.connect(self._scrub_end)
        st.windowChanged.connect(self.set_window)
        st.windowPlaced.connect(lambda s, n: self.set_window(s, n, playhead=s))
        st.hovered.connect(self._hover)
        ct.playToggled.connect(self.toggle_play)
        ct.step.connect(lambda d: self.seek(self.row + d, commit=True))
        ct.windowEdited.connect(lambda s, n: self.set_window(round(s * self.fps), round(n * self.fps)))
        QShortcut(QKeySequence(Qt.Key_Space), self, self.toggle_play)
        QShortcut(QKeySequence(Qt.Key_Left), self, lambda: self.seek(self.row - 1, commit=True))
        QShortcut(QKeySequence(Qt.Key_Right), self, lambda: self.seek(self.row + 1, commit=True))

        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self._tick)
        self.timeline.setEnabled(False)
        ct.progress.setText("no video")
        if from_file:
            self.open_document(source)
        else:
            self.set_document(document.from_tools(modules))

    # -- the document ----------------------------------------------------
    def set_document(self, doc):
        """Make `doc` the document: the canvas, the pane and the runtime follow, and the video it
        names, if any, is opened."""
        self._unload()
        self.doc = doc
        self._taken, self._driven = {}, {}     # the loaders' memory is the document's: its files are read anew
        self._shown_before, self._shown_last = [], doc.display
        doc.resolve(self.tools)
        self._gone = self.store.missing(doc)    # asked here, where the document opens; said on the graph once there is one
        for nid in self._gone:
            doc.node(nid).mode = document.LIVE
        self.canvas.set_document(doc)
        self.pane.set_document(doc)
        self.selection = None
        self.plot.set_selection(None)
        self._show_plot()
        self._retitle()
        self._pick_video()

    def open_document(self, path):
        """Open a saved document; a file that will not read is reported in the transport and leaves
        the current document alone."""
        try:
            doc = document.load(path, self.tools)
        except (OSError, ValueError, KeyError) as e:   # FormatError and json's errors are ValueErrors
            self.timeline.controls.progress.setText(f"could not open {os.path.basename(str(path))}: {e}")
            return False
        self.set_document(doc)
        return True

    def save_document(self, path=None):
        """Save to `path`, else to where the document lives, else ask."""
        path = path or self.doc.path
        if not path:
            return self._save_as()
        try:
            document.save(self.doc, path)
        except OSError as e:
            self.timeline.controls.progress.setText(f"could not save {os.path.basename(str(path))}: {e}")
            return False
        self._retitle()
        return True

    def _open_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open document", "", DOCUMENT_FILTER)
        if path:
            self.open_document(path)

    def _save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save document", self.doc.path or "", DOCUMENT_FILTER)
        return bool(path) and self.save_document(path)

    def _retitle(self):
        parts = [self.title]
        if self.doc is not None and self.doc.path:
            parts.append(os.path.basename(self.doc.path))
        if self.decoder is not None:
            parts.append(os.path.basename(self.decoder.path))
        self.setWindowTitle(" — ".join(parts))

    def _select(self, nid):
        self.selection = nid
        self.pane.select(nid)
        self.plot.set_selection(nid)
        self._show_pinned()

    def _show_plot(self):
        """The plot and the strip follow the document's pinned set and bands."""
        self.plot.set_pinned(self.doc.pinned)
        self._show_bands()
        self._show_pinned()

    def _show_bands(self):
        self.plot.set_bands({n.id: n.band for n in self.doc.nodes})

    def _toggle_pin(self, nid):
        if nid in self.doc.pinned:
            self.doc.unpin(nid)
        else:
            self.doc.pin(nid, self.tools)
        self._show_plot()

    def _band_dragged(self, nid, levels):
        """A handle on the plot proposes a band: it is the node's, written and handed back, and a
        chain node's chain reruns on the stack already walked, cheap enough to follow the drag; a
        frame node's walk restarts only once the handle is let go."""
        self.doc.node(nid).band = tuple(levels)
        self._show_bands()
        if self.graph is not None and nid in self.graph.chain:
            self._params_changed(nid)

    def _band_released(self, nid, levels):
        self.doc.node(nid).band = tuple(levels)
        self._show_bands()
        self._params_changed(nid)

    # -- the graph changed ------------------------------------------------
    def sync(self):
        """The document's wiring, nodes or flag changed: the pane, the plot, the runtime, the canvas
        and the frame follow, and the video, if a selector now picks a different file."""
        self.pane.sync()
        self._show_plot()
        self._pick_video()
        self.display.drawers = [(n.id, self.tools[n.tool], n) for n in self.doc.nodes
                                if n.tool in self.tools and hasattr(self.tools[n.tool], "draw")
                                and id(self.tools[n.tool]) not in self.display.dropped]
        self.canvas.update()
        if self.graph is None:
            return
        was = self._axis()
        self.graph.sync()
        self._restate()
        self._invalidate()
        self._follow_axis(was)
        self.goto(self.row, commit=True)

    def reflag(self):
        """A flag moved: the runtime's plan follows and the frame shows the new node at the same row.
        The memo and the walk stand; nothing a flag names is computed differently, unless the
        display flag crossed a bake, which moves the document into the other row space."""
        if self.doc.display != self._shown_last:
            if self._shown_last is not None:
                self._shown_before.append(self._shown_last)
            self._shown_last = self.doc.display
        self.canvas.update()
        if self.graph is None:
            return
        was = self._axis()
        self.graph.sync()
        self._restate()
        if self._follow_axis(was):
            self._invalidate()
        self.goto(self.row, commit=True)

    def _back(self):
        """A right click on the frame: the display flag returns to the node it showed before, skipping
        any since removed; nothing with nothing before."""
        ids = {n.id for n in self.doc.nodes} if self.doc is not None else set()
        while self._shown_before:
            nid = self._shown_before.pop()
            if nid in ids and nid != self.doc.display:
                self.doc.display = self._shown_last = nid
                self.reflag()
                return

    def _picked(self, nid, params):
        """A drawer answered a click: its params land in the document as a card's change does, through
        the node's widget when it has one, so the key, the pane and the frame follow."""
        node = self.doc.node(nid)
        node.params = {**node.params, **params}
        w = self.pane.widget(nid)
        if w is not None:
            w.set_params(node.params)       # moves the knobs; each move is a change the pane reports
        else:
            self._params_changed(nid)

    def _axis(self):
        return (self.graph.axis, self.graph.plate)

    def _follow_axis(self, was):
        """The document's row space changed with the display flag: the count and fps are the new
        space's, the playhead and window map across through the plate, and the traces, which were of
        the other clip, clear. Returns whether it changed."""
        if self._axis() == was:
            return False
        old, new = was[1] or document.Plate(0, 1), self.graph.plate or document.Plate(0, 1)
        across = lambda r: new.from_plate(old.to_plate(r))
        row, (s, n) = across(self.row), self.window_
        self.fps, self.count = self.graph.fps, self.graph.count
        self.timeline.strip.set_count(self.count, self.fps)
        self.timeline.controls.set_count(self.count, self.fps)
        self.results, self.clip_results = {}, {}
        self.pane.set_source(self.decoder.path, self.fps)
        if self.playing:
            self.timer.start(max(1, int(round(1000 / self.fps))))
        self.set_window(across(s), max(1, round(n * old.increment / new.increment)), playhead=row)
        return True

    def _toggle_mode(self, nid):
        node = self.doc.node(nid)
        node.mode = document.LIVE if document.served(node) else document.BAKED
        gone = self.store.missing(self.doc).get(nid)
        if gone:
            node.mode = document.LIVE
        self.sync()
        if gone:
            self.graph.note(nid, gone)
            self._restate()

    def _choose_store(self):
        path = QFileDialog.getExistingDirectory(self, "Store folder", self.store.folder)
        if not path:
            return
        refused = store.choose(path)
        if not refused:
            self.store = store.current()
            if self.worker is not None:
                self.worker.store = self.store      # the next bake's; one running lands where it began
        self.header.show_store(self.store, refused)

    def _restate(self):
        if self.graph is None:
            return
        self.canvas.grayed, self.canvas.stale = set(self.graph.off), set(self.graph.stale)
        self.pane.show_modes(self.graph.stale)
        for n in self.doc.nodes:
            text = self.graph.standing(n.id)
            self.pane.set_standing(n.id, text)
            if text:
                self.canvas.standings[n.id] = text
            else:
                self.canvas.standings.pop(n.id, None)

    def _failed(self, row, nid):
        self._restate()
        self.timeline.controls.progress.setText(f"{nid} {self.graph.standing(nid)}" if nid else f"a tool raised at row {row}, see {self.log}")

    def _worker_ended(self, worker):
        """The worker thread exited other than through `_unload`, so nothing will answer the display
        again until the video is reopened; the traceback is on stderr."""
        if worker is self.worker:
            self.timeline.controls.progress.setText(f"the worker stopped, see {self.log}; reopen the video")

    def _shortened(self, count):
        """The stream ended short of its container's claim: everything sized by the count follows
        the decoder's, and a playhead past the end lands on the last row there is."""
        if self.graph is None or count == self.count:
            return
        self.count = count
        self.timeline.strip.set_count(count, self.fps)
        self.timeline.controls.set_count(count, self.fps)
        if self.pane.video is not None:
            self.pane.video.show_source(self.decoder.path, (self.decoder.width, self.decoder.height, self.fps, count))
        s, n = self.window_
        if s + n > count:
            self.set_window(s, n)
        if self.row >= count:
            self.goto(count - 1, commit=True)

    def _draw_failed(self, nid, line):
        if self.graph is not None:
            self.graph.note(nid, line)
            self._restate()

    def _params_changed(self, nid):
        self.canvas.update()   # a band moved recolours its node's dot
        if document.is_selector(self.tools.get(self.doc.node(nid).tool)):
            self._pick_video()
            return
        if self.graph is None:
            return
        self.graph.sync()
        self._restate()
        if nid in self.graph.chain:
            self.worker.rerun_series()
        else:
            self._invalidate()
            self.goto(self.row, commit=True)

    def _invalidate(self):
        """The frame tools changed: the walk restarts, and the clip walk's rows are of a graph that is
        gone, so they are dropped here and now rather than when the worker gets to it."""
        self.worker.invalidate()
        self._clip_asked = False
        self.header.set_walking(False)
        self.header.clear_note()
        self.clip_results = {}
        self._show_pinned()

    # -- loading ---------------------------------------------------------
    def _pick_video(self):
        """Ask the document which file it means (its selector's answer, else its written path) and
        open that file if it is not the one open. A selector that answers nothing, or a file that
        will not open, is said on the video node and the canvas, and leaves what was open alone."""
        if self.doc is None:
            return False
        self._pick_paths()
        sel = self.doc.selector()
        path, why = document.pick_video(self.doc, self.tools)
        vid = self.doc.video_node()
        if self.pane.video is not None:
            self.pane.video.set_picker(sel is None, None if sel is None else sel.id)
        self._note_selectors()
        if vid is not None:
            self.canvas.errors.pop(vid.id, None)
        if path is None:
            if why:
                if self.pane.video is not None:
                    self.pane.video.show_none(why)
                if vid is not None:
                    self.canvas.errors[vid.id] = why
                    self.canvas.update()
            return False
        if self.decoder is not None and _same(self.decoder.path, path):
            return True
        opened = self._open_video(path)
        if not opened and vid is not None:
            self.canvas.errors[vid.id] = f"could not open {os.path.basename(str(path))}"
            self.canvas.update()
        return opened

    def _pick_paths(self):
        """Every tool node's path inputs: what the selector wired into each picks goes through the
        tool's loader into the node's params, once per file and again when the file changes on disk,
        which the window watches for; a miss is said on the node. A widget with `set_paths` is handed
        each input's picked file, whether or not its loader took it."""
        asked = set()
        for n in self.doc.nodes:
            tool = self.tools.get(n.tool)
            loaders = document.paths(tool)
            if not loaders:
                continue
            notes, errors, picked = [], [], {}
            w = self.pane.widget(n.id)
            for name, loader in loaders.items():
                sel = self.doc.selector(n.id, name)
                if sel is None:
                    self._taken.pop((n.id, name), None)
                    self._driven.pop((n.id, name), None)
                    continue
                path, why = document.pick_path(self.doc, self.tools, n.id, name)
                if why:
                    errors.append(f"{name}: {why}")
                    continue
                asked.add(path)
                picked[name] = os.path.abspath(path)
                notes.append(f"{name}: {os.path.basename(path)}")
                try:
                    stamp = (path, os.path.getmtime(path))
                    if self._taken.get((n.id, name)) == stamp:
                        continue
                    params = loader(path)
                except Exception as e:  # the file is the user's; say what was wrong with it, or that it is mid-save
                    errors.append(f"{name}: {type(e).__name__}: {e}")
                    continue
                self._taken[(n.id, name)] = stamp
                self._driven[(n.id, name)] = (tuple(params), sel.id)
                n.params = {**n.params, **params}
                if w is not None:
                    w.set_params(n.params)       # moves the knobs; each move is a change the pane reports
                else:
                    self._params_changed(n.id)
            if w is not None and hasattr(w, "set_driven"):
                held = [(keys, by) for (nid, _), (keys, by) in self._driven.items() if nid == n.id]
                w.set_driven({k for keys, _ in held for k in keys}, held[0][1] if held else None)
            if w is not None and hasattr(w, "set_paths"):
                w.set_paths(picked)
            if errors:
                self.canvas.errors[n.id] = "; ".join(errors)
            else:
                self.canvas.errors.pop(n.id, None)
            self.pane.note(n.id, "; ".join(errors or notes))
        self.canvas.update()
        self._watch_taken(asked)

    def _watch_taken(self, asked):
        """Watch every file a loader last read or was asked for and no other, and the folder of one
        that is not there, so a save that deletes and renames is seen when the new file lands. An
        editor that saves by replacing the file leaves the watcher holding the old inode, so the
        paths are re-added each time."""
        wanted = asked | {path for path, _ in self._taken.values()}
        watch = {p if os.path.exists(p) else os.path.dirname(p) for p in wanted}
        for had in (self._watch.files(), self._watch.directories()):
            if had:
                self._watch.removePaths(had)
        if watch:
            self._watch.addPaths(sorted(watch))

    def _path_changed(self, path):
        self._reload.start()

    def _note_selectors(self):
        """Every selector node's card: the count line, and the match list if its widget shows one."""
        folder = self.doc.folder()
        for n in self.doc.nodes:
            tool = self.tools.get(n.tool)
            if not document.is_selector(tool):
                continue
            matches = getattr(tool, "matches", None)
            try:
                picked = tool.select(folder, dict(n.params))
                found = matches(folder, dict(n.params)) if matches else None
            except Exception as e:
                self.pane.note(n.id, f"{type(e).__name__}: {e}")
                continue
            if picked is not None:
                picked = os.path.normpath(os.path.join(folder, picked))
            w = self.pane.widget(n.id)
            if found is not None and hasattr(w, "show_matches"):
                w.show_matches(folder, [os.path.normpath(p) for p in found], picked)
            picked_text = "" if picked is None else f", picked {os.path.basename(picked)}"
            if found is None:
                self.pane.note(n.id, "matched nothing" if picked is None else picked_text[2:])
            else:
                self.pane.note(n.id, f"{len(found)} match{'es' if len(found) != 1 else ''}{picked_text}")

    def load(self, path):
        """Open the video at `path` and record it in the document as written. A file that won't
        open is reported on the video node and leaves what was open alone; so does a path given
        while a selector is wired in, since the selector picks until it is unwired."""
        sel = self.doc.selector()
        if sel is not None:
            if self.pane.video is not None:
                self.pane.video.show_none(f"{sel.id} picks the video; unwire it to choose by hand")
            return
        was = self.doc.video
        self.doc.video = os.fspath(path)   # before opening: the open syncs, and the sync reopens what the document names
        if not self._open_video(path):
            self.doc.video = was

    def _open_video(self, path):
        try:
            decoder = Decoder(path, **({"cache_bytes": c} if (c := _gb(CACHE_ENV)) else {}))
        except IOError as e:
            if self.pane.video is not None:
                self.pane.video.show_error(path, e)
            return False
        self._unload()
        self.decoder = decoder
        self.graph = Graph(self.doc, decoder, self.tools, open_bake=lambda bake, cache: self.store.open_bake(bake, cache),
                           **({"memo_bytes": m} if (m := _gb(MEMO_ENV)) else {}))
        for nid, why in self._gone.items():
            self.graph.note(nid, why)
        self._gone = {}
        # the one line a report of this video's run needs beside the log's tracebacks
        print(f"SIEVE {time.strftime('%H:%M:%S')}: opened {path}: {decoder.width}x{decoder.height} at {decoder.fps:.3f} fps, "
              f"{decoder.count} rows claimed, luma plane {'read' if decoder.luma else 'converted'}; "
              f"memo {self.graph.memo.limit >> 30} GB, cache {decoder.cache_limit >> 30} GB", file=sys.stderr)
        # Attached for the video's life, read or not: docs/findings/2026-11-12-what-the-trace-costs.md. The sync below is its first plan.
        self.ledger = Ledger()
        self.graph.on_event = self.ledger.event
        if os.environ.get(DUMP_ENV):
            self.dump = Dump(self.graph, os.environ[DUMP_ENV])
        self.lateness = Lateness(self._sample, parent=self)
        self.pace = Pace()
        self.worker = Worker(self.graph, store=self.store)
        self.fps, self.count = self.graph.fps, self.graph.count
        ct = self.timeline.controls
        for signal, slot in (("rowReady", self._row_ready), ("seriesReady", self._series_ready),
                             ("densityReady", self.plot.set_fields), ("walked", lambda done, n, *was: ct.set_progress(done, n)),
                             ("walked", lambda _, n, *was: self._set_length(n)),   # the walk's own length: clamped, or closed early
                             ("walked", lambda *row: self._paced("window", *row)),
                             ("failed", self._failed), ("clipWalked", self._clip_walked), ("clipReady", self._clip_ready),
                             ("clipRefused", self._clip_refused), ("baked", self.pane.show_bake), ("bakeDone", self._baked),
                             ("bakeRefused", self._bake_refused), ("walkRefused", ct.progress.setText),
                             ("shortened", self._shortened)):
            getattr(self.worker, signal).connect(self._timed("slot", signal, slot))
        self.worker.finished.connect(lambda w=self.worker: self._worker_ended(w))
        self.header.setEnabled(True)
        self.timeline.strip.set_count(self.count, self.fps)
        ct.set_count(self.count, self.fps)
        ct.progress.setText("")
        self.timeline.setEnabled(True)
        self.worker.start()
        self.sync()
        self.set_window(0, min(self.count, round(10 * self.fps)))
        self.goto(0, commit=True)
        self.toggle_play()  # _unload left it paused
        if self.pane.video is not None:
            self.pane.video.show_source(path, (decoder.width, decoder.height, self.fps, self.count))
        self.pane.set_source(path, self.fps)
        self._retitle()
        return True

    def _sample(self, name, value, t):
        self.ledger.sample(name, value, t)
        if self.dump is not None:
            self.dump.sample(name, value, t)

    def _timed(self, kind, name, fn):
        """`fn` as a callable whose every call is a span of the GUI thread's in the stream of the
        video then open, a "slot" or a "paint" under `name`; see Graph.turn."""
        def timed(*args):
            if self.graph is None:
                return fn(*args)
            with self.graph.turn(kind, name):
                return fn(*args)
        return timed

    def _unload(self):
        if self.worker is None:
            return
        if self.playing:
            self.toggle_play()
        self.worker.stop()
        self.lateness.stop()
        if self.dump is not None:
            self.dump.close()
        self.dump = self.lateness = self.ledger = self.pace = None
        self.header.figure.set_figure(None)
        self.graph.close()
        self.decoder.close()
        self.decoder = self.graph = self.worker = None
        self.results, self.clip_results, self._clip_asked = {}, {}, False
        self.header.set_walking(False)
        self.header.clear_note()
        self.header.setEnabled(False)
        self.timeline.strip.set_series({})
        self.row, self.window_ = 0, (0, 0)
        self.plot.set_window(0, 0)
        self.plot.set_lines({}, 0)
        self.plot.set_fields({}, 0)
        self.display.clear()

    # -- state (every entry is a no-op until something is loaded) --------
    def set_window(self, start, length, playhead=None):
        """Move or resize the window. The playhead keeps its offset from the start, clamped inside,
        unless `playhead` names the row to show instead."""
        if self.graph is None:
            return
        start = max(0, min(self.count - 1, int(start)))
        length = max(1, min(self.count - start, int(length)))
        offset = self.row - self.window_[0] if playhead is None else int(playhead) - start
        offset = max(0, min(length - 1, offset))
        self.window_ = (start, length)
        self.plot.set_window(start, length, self.fps)
        self.timeline.strip.set_window(start, length)
        self.timeline.controls.set_window(start, length)
        self.worker.set_window(start, length)
        if self.row != start + offset:
            self.goto(start + offset, commit=True)

    def goto(self, row, commit):
        """Show `row` of the flagged node. A commit may ask the worker; a guess is served from the
        memo or not at all."""
        if self.graph is None:
            return
        self.row = row = max(0, min(self.count - 1, int(row)))
        shown = self.graph.shown
        if shown is None:
            self.display.clear()
        elif not self.graph.fed(shown):
            self.display.clear(f"{shown}: {self.graph.standing(shown)}")
        elif not self._show(row) and commit:
            self.worker.request_row(row)
        self.timeline.strip.set_playhead(row)
        self.timeline.controls.set_readout(row)
        for nid in self.graph.chain:
            w = self.pane.widget(nid)
            if w is not None and hasattr(w, "set_playhead"):
                w.set_playhead(row)
        self.plot.set_playhead(row)
        self._update_gate()

    def _scrub_begin(self, row):
        """The playhead is held: pause so the loop doesn't run away under the cursor."""
        self._resume = self.playing
        if self.playing:
            self.toggle_play()
        self.seek(row, commit=True)

    def _scrub_end(self, row):
        self.seek(row, commit=True)
        if self._resume:
            self.toggle_play()
        self._resume = False

    def seek(self, row, commit):
        """Move the playhead, clamped to the loop window. Only the handle and the spinboxes move
        the window; a gesture on the playhead never does."""
        if self.graph is None:
            return
        s, n = self.window_
        self.goto(max(s, min(s + n - 1, int(row))), commit)

    def toggle_play(self):
        if self.graph is None:
            return
        self.playing = not self.playing
        if self.playing:
            self.timer.start(max(1, int(round(1000 / self.fps))))
        else:
            self.timer.stop()
        self.timeline.controls.set_playing(self.playing)

    def _tick(self):
        s, n = self.window_
        nxt = self.row + 1
        if not s <= nxt < s + n:
            nxt = s
        self.goto(nxt, commit=True)

    # -- slots ----------------------------------------------------------
    def _show(self, row):
        """The shown node's frame at `row` from the memo, with the overlay node's plane over it if the
        memo has that too; False when either is not there yet, so a commit asks the worker for both."""
        frame = self.graph.peek(row)
        if frame is None:
            return False
        src = self.graph.shown
        while not imageable(frame):       # a table, blobs: show the nearest image upstream, with its draw() over it
            src = self.graph.source(src)
            frame = None if src is None else self.graph.peek(row, src)
            if frame is None:
                return False
        self.display.set_frame(frame, self.graph.key(self.graph.shown))
        self.display.frame_results = {nid: self.graph.peek(row, nid) for nid, *_ in self.display.drawers
                                      if nid not in self.graph.chain}
        over = self.graph.over
        plane = None if over is None else self.graph.peek(row, over)
        self.display.set_overlay(plane, None if over is None else self.graph.key(over))
        return over is None or plane is not None

    def _row_ready(self, row):
        if row == self.row and self.graph is not None:
            self._show(row)

    def _series_ready(self, results, start, fps):
        self.results, self.result_start = results, start
        self.plot.set_lines({nid: (r["signal"], r.get("gate")) for nid, r in results.items()
                             if isinstance(r, dict) and "signal" in r}, start)
        self._restate()
        for nid, result in results.items():
            w = self.pane.widget(nid)
            if w is not None and hasattr(w, "show_result"):
                w.show_result(result, start, fps)
        self._update_gate()
        self._show_pinned()

    # -- the clip walk ---------------------------------------------------
    def _toggle_clip(self):
        if self.worker is None:
            return
        if self._clip_asked:
            self.worker.stop_clip()
            self._clip_asked = False
            self.header.clear_note()
        else:
            self.worker.walk_clip()
            self._clip_asked = True
            self.header.note.setText("clip: after the window")
        self.header.set_walking(self._clip_asked)

    def _paced(self, lane, done, total, ran, served):
        self.pace.row(lane, done, total, ran, served)
        self.header.figure.set_figure(self.pace.figure(self.fps, self.count))

    def _clip_walked(self, done, total, ran, served):
        self._paced("clip", done, total, ran, served)
        if self._clip_asked:
            self.header.clear_note()
            if done >= total:
                self._clip_asked = False
                self.header.set_walking(False)

    def _clip_ready(self, results, start, fps):
        self.clip_results = results
        self._show_pinned()

    def _baked(self, nid, bake):
        """Recorded here, on the GUI thread, since the document is the GUI's and the worker's alone to read."""
        document.land(self.doc.node(nid), bake)
        self.header.show_store(self.store)
        self.sync()

    def _bake_refused(self, nid, why):
        self.pane.bake_refused(nid, why)
        self._restate()

    def _clip_refused(self, why):
        self._clip_asked = False
        self.header.set_walking(False)
        self.header.note.setText(why)

    def _show_pinned(self):
        """The strip draws every shown node that has a signal: the clip walk's when it has one, else
        the window's, each at its own rows."""
        series = {}
        for nid in document.shown(self.selection, self.doc.pinned) if self.doc is not None else []:
            if nid in self.clip_results:
                r, start = self.clip_results[nid], 0
            else:
                r, start = self.results.get(nid), self.result_start
            if isinstance(r, dict) and "signal" in r:
                series[nid] = (r["signal"], start, r.get("gate"))
        self.timeline.strip.set_series(series, self.selection)

    def _set_length(self, rows):
        """The plot's x axis is the window, so a walk fills in at its place instead of stretching."""
        self.plot.set_window(self.window_[0], rows, self.fps)

    def _hover(self, row):
        """One cursor for the strip and the plot; -1 clears it."""
        self.plot.set_hover(row)
        self.timeline.strip.set_hover(row)

    def _update_gate(self):
        """The border is on while every leaf of the series chain, a chain node no chain node reads,
        gates the playhead's row: each band zeroes what the next reads, so a leaf's gate is its branch's."""
        i = self.row - self.result_start
        chain = self.graph.series_chain() if self.graph is not None else []
        read = {src for _, _, _, _, src in chain}
        gates = [self.results[nid].get("gate") for nid, *_ in chain
                 if nid not in read and isinstance(self.results.get(nid), dict)]
        self.display.set_gate(bool(gates) and all(g is not None and 0 <= i < len(g) and bool(g[i]) for g in gates))
        self.display.set_state(self.row, self.results, self.result_start)

    SPLIT = 0.5   # the frame's share of the width until the handle is dragged

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if not self._split_moved:
            QTimer.singleShot(0, self._split_default)   # after the layout has given the splitter its width

    def _split_default(self):
        if not self._split_moved:
            w = self.split.width()
            self.split.setSizes([int(w * self.SPLIT), w - int(w * self.SPLIT)])

    def closeEvent(self, e):
        self.timer.stop()
        self._unload()
        super().closeEvent(e)
