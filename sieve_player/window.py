"""The window: the header across the top, the frame over the plot left, the canvas over the
parameter pane right, the transport across the bottom.

The document is the one source of truth. The canvas and the pane read and write it and say what
changed; the window carries the change to the runtime, built on every load of a video and
re-synced on every change, and carries the runtime's results and standings back to the widgets.
The display reads the memo and never waits on the decoder. It opens on whatever the document names, or empty, and never prompts.
"""
import json
import os
import pickle
import sys
import tempfile
import threading
import time
import traceback

import cv2
import numpy as np
from PySide6.QtCore import QFileSystemWatcher, QProcess, QProcessEnvironment, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QImage, QKeySequence, QPainter, QPixmap, QShortcut
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QMainWindow, QMenu, QMessageBox, QProgressBar, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from . import bare, budget, dev, document, filemenu, held, recent, store, theme, wire
from . import decoder as decoder_module
from .canvas import Canvas
from .catalogue import Log
from .cut import cut_in_time, holding, place_in
from .decoder import Decoder
from .graph import Graph
from .ledger import Ledger, row_cost
from .machine import Watch
from .pace import Pace, clock
from .pacecontrol import PaceControl
from .storecontrol import StoreControl
from .pane import Pane
from .plan import Provisional, stands, walked_keys
from . import registry
from .registry import CATEGORIES, Entry, category, description, signature
from .stream import ASKED, EDIT, HAND, Emitter
from .theme import GAP, PAD, ROW_H, readout
from .timeline import Timeline
from .trace import Dump
from .plot import Plot, Stage
from .heldwalks import Shown, as_given, gate_result, held_chain, held_periods, listed_cuts, period_run, shown_at, touched_periods, window_gate_result, window_periods
from .worker import Worker

STALE_MS = 250              # how long the cards' marks of other code may wait on a run held alone
HOLD_MS = 2000              # how long the held runs rest, nothing new held, before they are written beside the document
HELD_BYTES = budget.here()["held"]      # what the held runs and the window's own take together, as wire.result_bytes counts them, before the oldest go
WINDOW_RUNS_BYTES = HELD_BYTES // 8     # the window's own runs' part of it
TELL = 0.1                  # s between the worker's tellings of a walk's rows; docs/findings/2026-11-13-a-signal-a-row.md
DUMP_ENV = "SIEVE_DUMP"  # names the file every video opened in this process dumps its stream to


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

DOCUMENT_SUFFIX = "json"
DOCUMENT_FILTER = f"SIEVE document (*.{DOCUMENT_SUFFIX});;All (*)"


def _save_held(file, runs, failed):
    """held.File.write on the writer's thread, where a failure can only be said on stderr;
    `failed` is set when the file did not land."""
    try:
        for start, rows, *_ in file.write(runs):
            print(f"SIEVE {time.strftime('%H:%M:%S')}: the run of {rows} rows from {start} does not pickle and is not in {file.path}", file=sys.stderr)
    except Exception as e:
        failed.set()
        print(f"SIEVE {time.strftime('%H:%M:%S')}: could not write {file.path}: {type(e).__name__}: {e}", file=sys.stderr)


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
    return image_of(painted(a, top))


def painted(a, top=None):
    """The uint8 pixels to_qimage shows for `a` and `top`: (H, W) gray or (H, W, 3) BGR."""
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
    return np.ascontiguousarray(a)


def image_of(a):
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


PROXY_W, PROXY_H, PROXY_QUALITY = 1280, 720, 85
PROXY_BYTES = budget.here()["proxy"]


def packed(img):
    """`img`, uint8 pixels, as jpeg bytes within PROXY_W by PROXY_H, its aspect kept and never enlarged."""
    h, w = img.shape[:2]
    s = min(1.0, PROXY_W / w, PROXY_H / h)
    if s < 1:
        img = cv2.resize(img, (max(1, round(w * s)), max(1, round(h * s))), interpolation=cv2.INTER_AREA)
    return cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, PROXY_QUALITY])[1]


def loop_spills(rows, plane, limit):
    """Whether `rows` of the shown `plane` together pass `limit`, the memo's bytes."""
    return rows * np.asarray(plane).nbytes > limit


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


def outside_cuts(e, nid, row):
    """What the frame says in place of a frame at `row` of the node `nid`, whose plan Entry is `e`:
    that the row is outside its cuts, or "" where one holds it or there is no entry."""
    return "" if e is None or holding(e.cuts, row) is not None else f"row {row} is outside {nid}'s cuts"


class Display(QWidget):
    drawFailed = Signal(str, str)   # a tool's draw() or pick() raised: the node, the line
    picked = Signal(str, dict)      # a drawer claimed a left click: the node, the params to merge

    """The frame, the overlay heated over it, and each drawing node's draw() on
    top, in node order, each handed its own node's result: a series node's over the window, a
    frame node's at the row, the painter moved to where the pixels its node reads lie on the frame.
    A left click is offered to the drawers whose pick() claims it, the one drawn last first, as a
    point in those pixels."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pix, self._size, self.reason = None, None, ""   # _size: the frame's own, which a proxy's smaller _pix stands for
        self._proxies, self._proxy_under, self._proxy_bytes, self.proxied = {}, None, 0, False   # row -> proxy, oldest first; what they picture
        self._over, self._over_key, self._top = None, None, 0.0   # the overlay image, whose node's key, its running max
        self._frame_key, self._frame_top = None, 0.0               # the shown node's key and running max, for a measured plane
        self.drawers, self.row, self.results, self.start, self.starts = [], 0, {}, 0, {}   # drawers: [(node id, tool, node)]
        self.dropped = set()                                       # id() of each tool whose draw() or pick() raised; the window keeps them out of drawers
        self.frame_results = {}                                    # node id -> a drawing frame node's output at the row
        self.places = {}                                           # node id -> (x, y) on the frame of the first pixel of what a drawer's node reads; one with no place on it is not here
        self.setMinimumSize(160, 120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_state(self, row, results, start, starts=None):
        """`results` are node to result, each over the rows from `start`, or from its own row in `starts` where it has one."""
        self.row, self.results, self.start, self.starts = row, results, start, starts or {}
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
        self._pix, self.reason, self.proxied = QPixmap.fromImage(to_qimage(a, top)), "", False
        self._size = self._pix.size()
        self.update()

    def keep(self, row, under, frame, plane, limit):
        """Packs what was just painted at `row`, from `frame` and the overlay's `plane` as set_frame and
        set_overlay were handed them and the drawers' frame_results and places, as a proxy of what
        `under` names. Proxies of another `under` are let go first, and the oldest while all pass `limit` bytes."""
        if under != self._proxy_under:
            self.drop_proxies()
            self._proxy_under = under
        if row in self._proxies:
            return
        frame = np.asarray(frame)
        top = None if frame.dtype in (np.uint8, bool) else self._frame_top
        gray = otop = None
        if plane is not None:
            plane = np.asarray(plane)
            otop = None if plane.dtype == bool else self._top
            gray = packed(plane.view(np.uint8) * np.uint8(255) if otop is None else over(plane, otop))
        jpg = packed(painted(frame, top))
        results = dict(self.frame_results)
        n = jpg.nbytes + (0 if gray is None else gray.nbytes) + sum(wire.table_bytes(v) for v in results.values())
        self._proxies[row] = (jpg, top, gray, otop, self._size, results, dict(self.places), n)
        self._proxy_bytes += n
        while self._proxy_bytes > limit and self._proxies:
            self._proxy_bytes -= self._proxies.pop(next(iter(self._proxies)))[-1]

    def show_proxy(self, row, under):
        """Paints the proxy of `row` kept under `under`, the measured planes over the running tops now;
        False where there is none. Under another `under` than they were kept under, all are let go."""
        if under != self._proxy_under:
            self.drop_proxies()
        got = self._proxies.get(row)
        if got is None:
            return False
        jpg, top, gray, otop, self._size, self.frame_results, self.places, _ = got
        img = cv2.imdecode(jpg, cv2.IMREAD_UNCHANGED)
        if top is not None and self._frame_top > top:
            img = cv2.convertScaleAbs(img, alpha=top / self._frame_top)
        self._pix, self.reason, self.proxied = QPixmap.fromImage(image_of(img)), "", True
        self._over = None if gray is None else heat(cv2.imdecode(gray, cv2.IMREAD_UNCHANGED), 255.0 if otop is None else 255.0 * max(self._top, otop) / max(otop, 1e-6))
        self.update()
        return True

    def drop_proxies(self):
        self._proxies, self._proxy_under, self._proxy_bytes = {}, None, 0

    def clear(self, reason=""):
        """No frame; `reason` is the one line that says why, so an empty frame never reads as a stall."""
        self._pix, self.reason, self.proxied = None, reason, False
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

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), theme.qgray(theme.GROUND))
        if self._pix is None:
            if self.reason:
                p.setPen(theme.qgray(theme.INK_2))
                p.drawText(self.rect(), Qt.AlignCenter, self.reason)
            return
        shrinking = self._pix.width() > self.width() or self._pix.height() > self.height() or self.proxied
        # nearest-neighbour drops rows and columns when shrinking, which reads as stripes; grown, it shows each pixel as it is, which a proxy's are not
        x, y, w, h = self.frame_rect()
        pix = self._pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation if shrinking else Qt.FastTransformation)
        p.drawPixmap(x, y, pix)
        if self._over is not None:
            p.drawImage(QRectF(x, y, pix.width(), pix.height()), self._over)   # stretched to the frame, as draw() is
        if not self.drawers:
            return
        p.save()
        # Window/viewport rather than translate/scale: the same mapping, and a drawer can read the
        # frame's rect back from painter.window() when its own data is another resolution.
        p.setViewport(x, y, pix.width(), pix.height())
        p.setWindow(0, 0, self._size.width(), self._size.height())
        for nid, tool, node in self.drawers:
            if nid not in self.places:
                continue
            p.save()
            p.translate(*self.places[nid])
            try:
                tool.draw(p, self.row, self.frame_results.get(nid, self.results.get(nid)), self.starts.get(nid, self.start), node.params)
            except Exception as e:
                traceback.print_exc()
                self.drop(tool)
                self.drawFailed.emit(nid, f"draw() raised: {type(e).__name__}: {e}")
            p.restore()
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
        scaled = self._size.scaled(self.size(), Qt.KeepAspectRatio)
        return (self.width() - scaled.width()) // 2, (self.height() - scaled.height()) // 2, scaled.width(), scaled.height()

    def to_frame(self, pos):
        """A widget point as (x, y) in the frame's pixels, or None off the frame."""
        r = self.frame_rect()
        if r is None:
            return None
        x, y, w, h = r
        fw, fh = self._size.width(), self._size.height()
        fx, fy = (pos.x() - x) * fw / w, (pos.y() - y) * fh / h
        return (fx, fy) if 0 <= fx < fw and 0 <= fy < fh else None

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton or (point := self.to_frame(e.position())) is None:
            return
        shape = (self._size.height(), self._size.width())
        for nid, tool, node in reversed(self.drawers):
            pick, result = registry.pick_of(tool), self.frame_results.get(nid, self.results.get(nid))
            if pick is None or result is None or nid not in self.places:
                continue
            x, y = self.places[nid]
            try:
                answer = pick((point[0] - x, point[1] - y), shape, self.row, result, node.params)
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
    return modules, registry.by_name(modules), broken


class Header(QWidget):
    """The row across the top, all at its right: what the clip walk or a refused store has to say, a
    bare walk's bar, the store, whose press changes it, the walk's figure, the button that walks the
    clip bare (bare.py) and the clip walk's."""

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(GAP)
        self.note = readout(mono=True, wrap=False)
        self.note.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._refused = ""
        self.store = StoreControl("click to choose the store's folder")
        self.figure = PaceControl("click for the monitor")
        self.walk = QPushButton("Walk clip")
        self.walk.setFixedSize(80, ROW_H)
        self.bare = QPushButton("Walk bare")
        self.bare.setFixedSize(80, ROW_H)
        self.bare.setToolTip("Walks the clip in a process of its own: a bar, its rate and when it ends, "
                             "the series nodes' results at its end, and nothing in the monitor")
        self.bar = QProgressBar()
        self.bar.setFixedSize(160, ROW_H)
        self.bar.setTextVisible(False)
        self.bar.hide()
        lay.addStretch(1)
        lay.addWidget(self.note)
        lay.addWidget(self.bar)
        lay.addWidget(self.store)
        lay.addWidget(self.figure)
        lay.addWidget(self.bare)
        lay.addWidget(self.walk)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def show_store(self, folder, refused=""):
        """`folder`, the store, read now; `refused` is why a choice was not taken, said in the note
        until the next showing, if the note still says it then."""
        self.store.set_store(folder)
        if refused or (self._refused and self.note.text() == self._refused):
            self.note.setText(refused)
        self._refused = refused

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
    framesCounted = Signal(str, int)    # a video's frame times are read: its path and their rows, never fewer than its stream's frames

    def __init__(self, source, title="SIEVE", tools=(), log=None, noted=None):
        """`source` is a list of tools, which become the document, or the path of a saved document.
        The catalogue the Tab menu offers and the document's names index is `tools`, plus the list
        when `source` is one. Either list holds tool modules or registry entries; see `catalogue`.
        `log` names where stderr also goes, for a line that sends the user there. `noted` is the file
        the documents this window opens and saves are noted in and Open Recent reads, as
        recent.FILE is; with None nothing is noted and Open Recent has none."""
        super().__init__()
        self.title, self.log, self.noted = title, log or "stderr", noted
        self.setStyleSheet(theme.sheet())
        self.framesCounted.connect(self._frames_counted)
        from_file = isinstance(source, (str, os.PathLike))
        modules, self.tools, broken = catalogue(list(tools) if from_file else [*source, *tools])
        if not from_file:
            modules = catalogue(source)[0]
        self.doc = self._written = None           # the document, and its text as last opened, made or saved
        self.decoder = self.graph = self.stream = self.worker = None
        self.ledger = self.lateness = self.machine = None     # the open video's stream kept over time, and the GUI thread's and the machine's samplers into it
        self.pace = None                          # the open video's walks as the header's figure reads them
        self.dump = None                          # the stream's file, while DUMP_ENV names one
        self.fps, self.count = 30.0, 0
        self.row, self.playing, self.window_ = 0, False, (0, 0)
        self._spill_under, self._spill_from = None, 0   # the picture proxies are of, and the memo's evictions when it was first shown
        self._bare = None          # the QProcess of a bare walk under way
        self._resume = False  # playback to restore when a playhead drag ends
        self.results, self.result_start = {}, 0   # node id -> the series chain's results, and the row they start at
        self.clip_results = {}                    # the same over the clip walk's rows, from row 0; {} when there are none
        self.window_periods = {}                  # what the window shows of each cut in time it overlaps, as heldwalks.window_periods has it
        self._clip_asked = False                  # a clip walk was asked for and has not finished or been stopped
        self._of_plan = None                      # the Plan _of_cuts was answered of
        self._of_cuts = (None, None, {})          # (the walked nodes' chain and the count, held_periods, node -> listed_cuts) as _show_held last answered them; the first None once the runs are taken whole
        self.runs = held.Runs(HELD_BYTES - WINDOW_RUNS_BYTES, self._result_bytes)  # the held runs, the file's and this session's walks of the clip and its cuts
        self.window_runs = held.Runs(WINDOW_RUNS_BYTES, self._result_bytes)   # the window's own walks: they serve the window again and nothing else reads them
        self._spared = False                      # the window's results are a held run's, and the worker runs no chain over it
        self._clip_ended = False                  # the clip walk told of its last row and its results have not yet come
        self._clip_rests = False                  # the clip walk last told of every row of its range done: the clip's last, or the one it was stopped at
        self._given = False                       # the window walk was given held results for some of the chain and steps the rest
        self._unwritten = False                   # a run was held since the checkpoint was written
        self._file = None                         # the held.File the runs were read from or last written to; the writer's thread's while that lives
        self._writer = None                       # the thread writing the checkpoint, or the last that did
        self._write_failed = threading.Event()    # the last writer's file did not land: the next write carries its runs
        self._taken = {}      # (node id, path input) -> (the file last handed to its loader, its mtime)
        self._watch = QFileSystemWatcher(self)
        self._watch.fileChanged.connect(self._path_changed)
        self._watch.directoryChanged.connect(self._path_changed)
        self._reload = QTimer(self)      # a save is often several writes; the loaders run once they settle
        self._reload.setSingleShot(True)
        self._reload.setInterval(RELOAD_SETTLE_MS)
        self._reload.timeout.connect(self._pick_paths)
        self._driven = {}      # (node id, path input) -> (the keys set through it, the id of the node wired in)

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
        self.canvas.pinToggled.connect(self._toggle_pin)
        self.pane.paramsChanged.connect(self._params_changed)
        self.pane.storeChanged.connect(self._store_changed)
        self.pane.videoPicked.connect(self.load)
        # the canvas reports a selection only when it changes, so the closed card's node is let go: a click on it opens the card again
        self.pane.closed.connect(lambda: self.canvas.select([]))
        self.plot.pressed.connect(self._scrub_begin)
        self.plot.dragged.connect(lambda r: self.seek(r, commit=False))
        self.plot.released.connect(self._scrub_end)
        self.plot.hovered.connect(self._hover)
        self.plot.bandDragged.connect(self._band_dragged)
        self.plot.bandReleased.connect(self._band_released)
        self.plot.chipClicked.connect(lambda nid: self.canvas.select([nid]))
        self.plot.pinToggled.connect(self._toggle_pin)
        self.display.drawFailed.connect(self._draw_failed)
        self.display.picked.connect(self._picked)
        self.selection = None      # the node the canvas last selected, whose settings the pane shows until its card is closed and whose axis the plot draws
        self.header = Header()
        self.header.show_store(store.folder())
        self.header.store.clicked.connect(self._choose_store)
        self.header.walk.clicked.connect(self._toggle_clip)
        self.header.bare.clicked.connect(self._toggle_bare)
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
        menu.addAction("New", QKeySequence.New, self._new)
        menu.addAction("Open…", QKeySequence.Open, self._open_dialog)
        self._recent = menu.addMenu("Open Recent")
        self._recent.aboutToShow.connect(self._fill_recent)
        menu.addSeparator()
        menu.addAction("Save", QKeySequence.Save, self.save_document)
        menu.addAction("Save As…", QKeySequence.SaveAs, self._save_as)
        menu.addSeparator()
        menu.addAction("Let Go of Held Results…", self._ask_let_go)
        dev.install(self)
        for m in self.menuBar().findChildren(QMenu):
            theme.round_menu(m)

        st, ct = self.timeline.strip, self.timeline.controls
        st.pressed.connect(self._scrub_begin)
        st.dragged.connect(lambda r: self.seek(r, commit=False))
        st.released.connect(self._scrub_end)
        st.windowChanged.connect(lambda s, n: self.set_window(s, n, by=HAND))
        st.windowPlaced.connect(lambda s, n: self.set_window(s, n, playhead=s, by=HAND))
        st.hovered.connect(self._hover)
        ct.playToggled.connect(self.toggle_play)
        ct.step.connect(lambda d: self.seek(self.row + d, commit=True))
        ct.windowEdited.connect(lambda s, n: self.set_window(round(s * self.fps), round(n * self.fps), by=HAND))
        QShortcut(QKeySequence(Qt.Key_Space), self, self.toggle_play)
        QShortcut(QKeySequence(Qt.Key_Left), self, lambda: self.seek(self.row - 1, commit=True))
        QShortcut(QKeySequence(Qt.Key_Right), self, lambda: self.seek(self.row + 1, commit=True))

        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self._tick)
        self._hold = QTimer(self)                 # running while a run held since the last write waits for a quiet moment
        self._hold.setSingleShot(True)
        self._hold.setInterval(HOLD_MS)
        self._hold.timeout.connect(lambda: self._write_held())
        self._stale_due = QTimer(self)            # running while a run held alone waits for the cards to be marked: the marks read the tools' files, once for however many are held meanwhile
        self._stale_due.setSingleShot(True)
        self._stale_due.setInterval(STALE_MS)
        self._stale_due.timeout.connect(lambda: self._show_stale(self._chain()))
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
        doc.resolve(self.tools)
        self.canvas.set_document(doc)
        self.pane.set_document(doc)
        self.selection = None
        self.plot.set_selection(None)
        self._show_plot()
        self._retitle()
        self._pick_video()
        self._written = self._text()

    def open_document(self, path):
        """Open a saved document; a file that will not read is reported in the transport and leaves
        the current document alone."""
        try:
            doc = document.load(path, self.tools)
        except (OSError, ValueError, KeyError) as e:   # FormatError and json's errors are ValueErrors
            self.timeline.controls.progress.setText(f"could not open {os.path.basename(str(path))}: {e}")
            return False
        self.set_document(doc)
        self._note()
        return True

    def save_document(self, path=None):
        """Save to `path`, else to where the document lives, else ask."""
        path = path or self.doc.path
        if not path:
            return self._save_as()
        was = self.doc.path
        try:
            document.save(self.doc, path)
        except OSError as e:
            self.timeline.controls.progress.setText(f"could not save {os.path.basename(str(path))}: {e}")
            return False
        self._written = self._text()
        self._note()
        self._unwritten |= was != self.doc.path
        self._write_held(wait=True)
        self._retitle()
        return True

    def _note(self):
        if self.noted:
            recent.note(self.noted, self.doc.path)

    def _text(self):
        return json.dumps(self.doc.to_dict(), sort_keys=True)

    def differs(self):
        """Whether the document is other than it was when last opened, made or saved."""
        return self.doc is not None and self._text() != self._written

    def ask_unsaved(self):
        """"save", "discard" or "cancel", asked by a dialog naming the document."""
        name = os.path.basename(self.doc.path) if self.doc.path else "The document"
        box = QMessageBox(self)
        box.setWindowTitle("Unsaved changes")
        box.setText(f"{name} has unsaved changes.")
        buttons = QMessageBox.StandardButton
        box.setStandardButtons(buttons.Save | buttons.Discard | buttons.Cancel)
        box.setDefaultButton(buttons.Save)
        box.exec()
        return {buttons.Save: "save", buttons.Discard: "discard"}.get(box.standardButton(box.clickedButton()), "cancel")

    def _leaving(self):
        """True when the document may be left behind: it does not differ, or the user chose Discard,
        or chose Save and the save was taken."""
        if not self.differs():
            return True
        answer = self.ask_unsaved()
        return self.save_document() if answer == "save" else answer == "discard"

    def _new(self):
        if self._leaving():
            self.set_document(document.from_tools([]))

    def _open_dialog(self):
        if not self._leaving():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Open document", os.path.dirname(self._save_as_start()), DOCUMENT_FILTER)
        if path:
            self.open_document(path)

    def _fill_recent(self):
        filemenu.fill(self._recent, recent.entries(self.noted) if self.noted else [],
                      lambda path: self._leaving() and self.open_document(path))

    def _save_as_start(self):
        """The file a save dialog opens on: the document's own, else one named for the open video
        and beside it, else a bare name in whatever folder the dialog falls to."""
        if self.doc.path:
            return self.doc.path
        if self.decoder is not None:
            return f"{os.path.splitext(self.decoder.path)[0]}.{DOCUMENT_SUFFIX}"
        return f"untitled.{DOCUMENT_SUFFIX}"

    def _save_as(self):
        dialog = QFileDialog(self, "Save document", self._save_as_start(), DOCUMENT_FILTER)
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setDefaultSuffix(DOCUMENT_SUFFIX)
        return bool(dialog.exec()) and self.save_document(dialog.selectedFiles()[0])

    def _retitle(self):
        parts = [self.title]
        if self.doc is not None and self.doc.path:
            parts.append(os.path.basename(self.doc.path))
        if self.decoder is not None:
            parts.append(os.path.basename(self.decoder.path))
        self.setWindowTitle(" - ".join(parts))

    def _select(self, nid):
        self.selection = nid
        if self.stream is not None:
            self.stream.watch(nid)
        self.pane.select(nid)
        self.plot.set_selection(nid)
        self._tell_shown()
        self._show_pinned()
        self._show_size()
        self._show_takes()

    def _show_plot(self):
        """The plot and the strip follow the document's pinned set and bands."""
        self.plot.set_pinned(self.doc.pinned)
        self._tell_shown()
        self._show_bands()
        self._show_pinned()

    def _tell_shown(self):
        """The worker folds the densities of what the plot shows."""
        if self.worker is not None:
            self.worker.watch(document.shown(self.selection, self.doc.pinned))

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
        self._set_drawers()
        self.canvas.update()
        if self.graph is None:
            return
        self.graph.sync()
        self._restate()
        self._invalidate()
        self.goto(self.row, commit=True)

    def reflag(self):
        """A flag moved: the runtime's plan follows and the frame shows the new node at the same row.
        The memo and the walk stand; nothing a flag names is computed differently."""
        self._set_drawers()
        self.canvas.update()
        if self.graph is None:
            return
        self.graph.sync()
        self._restate()
        self.goto(self.row, commit=True)

    def _set_drawers(self):
        """The display paints the draw() of each node on the document's drawn list whose tool has
        one that has not raised, in node order, and the graph is told which."""
        self.display.drawers = [(n.id, self.tools[n.tool], n) for n in self.doc.nodes
                                if n.id in self.doc.drawn and n.tool in self.tools and registry.draws(self.tools[n.tool])
                                and id(self.tools[n.tool]) not in self.display.dropped]
        self._tell_painted()

    def _places(self, shown, row, shape):
        """Drawer to where, on `shown`'s frame of `shape` at `row`, the first pixel of what its
        node reads lies, as cut.place_in; a drawer with no place on that frame is left out."""
        of, plate, out = self.graph.entry(shown), (self.decoder.height, self.decoder.width), {}
        at = None if of is None else holding(of.cuts, row)
        for nid, *_ in self.display.drawers:
            e = self.graph.entry(nid)
            read = None if e is None else holding(e.reads, row)
            if at is not None and read is not None and (xy := place_in(read, at, row, shape, plate)) is not None:
                out[nid] = xy
        return out

    def _tell_painted(self):
        if self.graph is not None:
            self.graph.paints([nid for nid, *_ in self.display.drawers])

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

    def _restate(self):
        if self.graph is None:
            return
        self.canvas.served = {n.id for n in self.doc.nodes if (e := self.graph.entry(n.id)) is not None and e.file is not None}
        self.pane.set_source(self.decoder.path, self.fps, {n.id: self.graph.footage(n.id) for n in self.doc.nodes})
        self.pane.set_cut_files_in_use(self.graph.cut_files_in_use())
        cutting = {n.id: e for n in self.doc.nodes if (e := self.graph.entry(n.id)) is not None and registry.cuts(e.tool)}
        unheld = self.graph.snapshot().unheld      # a card is handed no provisional cut, so none is written to a file
        self.pane.set_cuts({nid: (tuple(c for c in e.cuts if not c.provisional) if nid in unheld else e.cuts, self.count,
                                  w.src if (by := registry.cut_by(e.tool)) and (w := self.doc.source(nid, by[0])) else None)
                            for nid, e in cutting.items()})
        self.timeline.strip.set_periods({nid: [s for r in e.cuts if (s := cut_in_time(r))] for nid, e in cutting.items()})
        for n in self.doc.nodes:
            text = self.graph.standing(n.id)
            self.pane.set_standing(n.id, text)
            if text:
                self.canvas.standings[n.id] = text
            else:
                self.canvas.standings.pop(n.id, None)
        self._bare_stands()

    def _failed(self, row, nid):
        self._restate()
        self.timeline.controls.progress.setText(f"{nid} {self.graph.standing(nid)}" if nid else f"a tool raised at row {row}, see {self.log}")

    def _worker_ended(self):
        """The slot of a worker's `finished`. One that exited other than through `_unload` is still
        the window's, so nothing will answer the display again until the video is reopened; the
        traceback is on stderr."""
        if self.worker is not None and self.sender() is self.worker:
            self.timeline.controls.progress.setText(f"the worker stopped, see {self.log}; reopen the video")

    def _frames_counted(self, path, rows):
        """The open video's frame times have `rows` rows, never fewer than its stream's frames: the
        count comes down to them where its container claimed more, before any read reaches the end."""
        if self.decoder is not None and self.decoder.path == path:
            self.decoder.ends_at(rows)
            self._shortened(self.decoder.count)

    def _shortened(self, count):
        """The stream ended short of its container's claim: everything sized by the count follows
        the decoder's, a cut made of a run reaching the last row among it, and a playhead past the
        end lands on the last row there is."""
        if self.graph is None or count == self.count:
            return
        self.count = count
        self._recut(by_count=True)
        self.timeline.strip.set_count(count, self.fps)
        self.timeline.controls.set_count(count, self.fps)
        if self.pane.video is not None:
            self.pane.video.show_source(self.decoder.path, (self.decoder.width, self.decoder.height, self.fps, count))
        s, n = self.window_
        if s + n > count:
            self.set_window(s, n)
        self._show_held()
        if self.row >= count:
            self.goto(count - 1, commit=True)

    def _draw_failed(self, nid, line):
        self._tell_painted()
        if self.graph is not None:
            self.graph.note(nid, line)
            self._restate()

    def _choose_store(self):
        path = QFileDialog.getExistingDirectory(self, "Store folder", store.folder())
        if not path:
            return
        refused = store.choose(path)
        self.header.show_store(store.folder(), refused)
        if not refused:
            self.sync()     # the cutting nodes are asked again, of the store chosen
            if self.graph is not None:
                self.pane.set_cut_files_in_use(self.graph.cut_files_in_use(), again=True)

    def _keys(self):
        return {nid: e.key for nid, e in self.graph.snapshot().entries.items()}

    def _params_changed(self, nid):
        self.canvas.update()   # a band moved recolours its node's dot
        if registry.is_selector(self.tools.get(self.doc.node(nid).tool)):
            self._pick_video()
            return
        if self.graph is not None:
            self._asked_again(nid)

    def _store_changed(self, nid):
        """`nid`'s card wrote or removed files of the store: the store is read and the cutting
        nodes asked again, the document as it was."""
        self.header.show_store(store.folder())
        if self.graph is not None:
            self._asked_again(nid)

    def _asked_again(self, nid):
        """The graph synced after a change at `nid`, and the walk begun again only where a key moved."""
        keys, ranges = self._keys(), self._own_ranges()
        self.graph.sync()
        self._restate()
        if self._keys() == keys:
            self.goto(self.row, commit=True)    # nothing is computed differently; a drawer may draw the params as they now are
        elif nid in self.graph.chain:
            if self._spared or self._given or self._held_over(self._chain()) is not None:
                self._ask_window(EDIT)  # what was held is no longer the chain's, or a run now is: the walk begins again with what is held now
            self.worker.rerun_series()
            self._show_held()
        elif nid in self._walked_nodes() and self._own_ranges() == ranges:
            self._walk_periods_again()
        else:
            self._invalidate()
            self.goto(self.row, commit=True)

    def _walk_periods_again(self):
        """The plan moved under the cuts in time and under nothing either own range walks: each lane
        walks the cuts the plan now has that the runs do not hold, and neither own range begins again."""
        self._restate()
        self.window_periods = window_periods(self.graph.snapshot(), self.runs, *self.window_)
        self._show_held()
        self.worker.recut()
        self.goto(self.row, commit=True)

    def _invalidate(self):
        """The frame tools changed: the walk restarts, and the clip walk's rows are of a graph that is
        gone, so they are dropped here and now rather than when the worker gets to it."""
        self.worker.invalidate()
        self._ask_window(EDIT)
        self._show_held()
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
            loaders = registry.paths(tool)
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
            if not registry.is_selector(tool):
                continue
            matches = registry.matches_of(tool)
            try:
                picked = tool.select(folder, registry.computed(tool, n.params))
                found = matches(folder, registry.computed(tool, n.params)) if matches else None
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
            decoder = Decoder(path, cache_bytes=budget.here()["cache"])
        except IOError as e:
            if self.pane.video is not None:
                self.pane.video.show_error(path, e)
            return False
        self._unload()
        self.decoder = decoder
        decoder_module.STORE = store.folder
        decoder_module.read_frame_times_ahead(path, lambda rows, path=str(path): self.framesCounted.emit(path, rows))     # the first seek would wait on it: docs/findings/2026-11-15-a-file-whose-times-do-not-count-its-rows.md
        self.stream = Emitter()
        self.graph = Graph(self.doc, decoder, self.tools, stream=self.stream, cut_result=self._cut_result, memo_bytes=budget.here()["memo"])
        # the one line a report of this video's run needs beside the log's tracebacks
        print(f"SIEVE {time.strftime('%H:%M:%S')}: opened {path}: {decoder.width}x{decoder.height} at {decoder.fps:.3f} fps, "
              f"{decoder.count} rows claimed, luma plane {'read' if decoder.luma else 'converted'}; "
              f"memo {self.graph.memo.limit >> 30} GB, cache {decoder.cache_limit >> 30} GB", file=sys.stderr)
        # Attached for the video's life, read or not: docs/findings/2026-11-12-what-the-trace-costs.md. The sync below is its first plan.
        self.ledger = Ledger(timed=lambda stream=self.stream: stream.turn("monitor", "ledger"), watch=Log())
        self.stream.on_event = self.ledger.event
        self.stream.watch(self.selection)
        if os.environ.get(DUMP_ENV):
            self.dump = Dump(self.graph, os.environ[DUMP_ENV])
        self.lateness = Lateness(self._sample, parent=self)
        self.machine = Watch(self._sample, still_out=self.stream.still_out)
        self.pace = Pace()
        self.worker = Worker(self.graph, tell_every=TELL)
        self._tell_shown()
        self.fps, self.count = self.graph.fps, self.graph.count
        ct = self.timeline.controls
        for signal, slot in (("rowReady", self._row_ready), ("seriesReady", self._window_ready),
                             ("densityReady", self.plot.set_fields), ("walked", lambda done, n, *was: ct.set_progress(done, n)),
                             ("walked", lambda _, n, *was: self._set_length(n)),   # the walk's own length: clamped, or closed early
                             ("walked", lambda *row: self._paced("window", *row)),
                             ("failed", self._failed), ("clipWalked", self._clip_walked), ("clipReady", self._clip_ready),
                             ("clipRefused", self._clip_refused), ("walkRefused", ct.progress.setText),
                             ("periodWalked", self._period_walked), ("periodReady", self._period_ready),
                             ("windowPeriodWalked", self._window_period_walked), ("windowPeriodReady", self._window_period_ready),
                             ("shortened", self._shortened)):
            getattr(self.worker, signal).connect(self._timed("slot", signal, slot))
        self.worker.finished.connect(self._worker_ended)    # no closure over the worker: one connected to its own signal keeps it, its graph and the memo for good
        self.header.setEnabled(True)
        self.timeline.strip.set_count(self.count, self.fps)
        ct.set_count(self.count, self.fps)
        ct.progress.setText("")
        self.timeline.setEnabled(True)
        self.worker.start()
        self.sync()
        self._file = held.File(held.path_for(self.doc.path)) if self.doc.path else None
        self._take_runs(self._file.load() if self._file is not None else [])
        self._recut()
        selected, window = recent.view_of(recent.views_beside(self.noted), self.doc.path) if self.noted and self.doc.path else (None, None)
        s, n = window or (0, min(self.count, round(10 * self.fps)))
        self.set_window(s, n, by=HAND)
        self._show_held()
        self.goto(self.window_[0], commit=True)
        if any(n.id == selected for n in self.doc.nodes):
            self.canvas.select([selected])
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
        video then open, a "slot" or a "paint" under `name`; see stream.Emitter.turn."""
        def timed(*args):
            if self.stream is None:
                return fn(*args)
            with self.stream.turn(kind, name):
                return fn(*args)
        return timed

    def _unload(self):
        if self.worker is None:
            return
        if self.noted and self.doc is not None and self.doc.path:
            recent.keep_view(recent.views_beside(self.noted), self.doc.path, self.selection, self.window_)
        if self.playing:
            self.toggle_play()
        self._end_bare()
        self._write_held(wait=True)
        self._take_runs([])
        self._unwritten, self._file = False, None
        self._write_failed.clear()
        self._spared = self._given = False
        self.worker.stop()
        self.lateness.stop()
        self.machine.close()
        if self.dump is not None:
            self.dump.close()
        self.dump = self.lateness = self.machine = self.ledger = self.pace = None
        self.header.figure.set_figure(None)
        self.graph.empty()      # the stores go with the video whoever still holds the graph
        self.graph.close()
        self.decoder.close()
        self.decoder = self.graph = self.stream = self.worker = None
        self.results, self.clip_results, self.window_periods, self._clip_asked = {}, {}, {}, False
        self.header.set_walking(False)
        self.header.clear_note()
        self.header.setEnabled(False)
        self.timeline.setEnabled(False)
        self.timeline.controls.progress.setText("no video")
        self.timeline.strip.set_series({})
        self.timeline.strip.set_held([])
        self.timeline.strip.set_periods({})
        self.row, self.window_ = 0, (0, 0)
        self.plot.set_window(0, 0)
        self.plot.set_lines({})
        self.plot.set_fields({}, 0)
        self.display.clear()
        self.display.drop_proxies()

    # -- state (every entry is a no-op until something is loaded) --------
    def set_window(self, start, length, playhead=None, by=ASKED):
        """Move or resize the window. The playhead keeps its offset from the start, clamped inside,
        unless `playhead` names the row to show instead. `by` is what the walk's begin says began
        it, as Worker.set_window takes it: a caller that says nothing is no hand and no edit."""
        if self.graph is None:
            return
        start = max(0, min(self.count - 1, int(start)))
        length = max(1, min(self.count - start, int(length)))
        offset = self.row - self.window_[0] if playhead is None else int(playhead) - start
        offset = max(0, min(length - 1, offset))
        self.window_ = (start, length)
        self.graph.holds(start, length)
        self.plot.set_window(start, length, self.fps)
        self.timeline.strip.set_window(start, length)
        self.timeline.controls.set_window(start, length)
        self._ask_window(by)
        if self.row != start + offset:
            self.goto(start + offset, commit=True)

    def goto(self, row, commit):
        """Show `row` of the flagged node. A commit may ask the worker; a guess is served from the
        memo, or while playing a display proxy, or not at all. A row a proxy shows asks nothing."""
        if self.graph is None:
            return
        self.row = row = max(0, min(self.count - 1, int(row)))
        self.graph.looks_at(row)
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
        self._update_display()

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
        """Move the playhead, clamped to the loop window. Only the handle, a press in the strip
        outside the window and the spinboxes move the window; a gesture on the playhead never does."""
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
            if self.display.proxied:
                self.goto(self.row, commit=True)
        self.timeline.controls.set_playing(self.playing)

    def _tick(self):
        s, n = self.window_
        nxt = self.row + 1
        if not s <= nxt < s + n:
            nxt = s
        self.goto(nxt, commit=True)

    # -- slots ----------------------------------------------------------
    def _show(self, row):
        """The shown node's frame at `row` from the memo, with the overlay node's plane over it and
        the drawing frame nodes' outputs if the memo has those too; False when any is not there
        yet, so a commit asks the worker for them all. While playing, a row the memo lacks is
        painted from the display's proxy of it where there is one, and True. A row painted whole
        is kept as a proxy while the window's rows of its plane pass the memo's limit, or once the
        memo has let anything go since this picture was first shown: the memo holds a row's other
        planes too, which the first test does not count. At a row
        outside the shown node's cuts the frame says so, and nothing is asked."""
        if outside := outside_cuts(self.graph.entry(self.graph.shown), self.graph.shown, row):
            self.display.clear(outside)
            return True
        under = self._pictured()
        frame = self.graph.peek(row)
        if frame is None:
            return self.playing and self.display.show_proxy(row, under)
        src = self.graph.shown
        while not imageable(frame):       # a table, blobs: show the nearest image upstream, with its draw() over it
            src = self.graph.source(src)
            frame = None if src is None else self.graph.peek(row, src)
            if frame is None:
                return self.playing and self.display.show_proxy(row, under)
        self.display.set_frame(frame, self.graph.key(self.graph.shown))
        self.display.places = self._places(src, row, frame.shape[:2])
        walked = self._walked_nodes()
        self.display.frame_results = {nid: self.graph.peek(row, nid) for nid, *_ in self.display.drawers if nid not in walked}
        over = self.graph.over
        plane = None if over is None else self.graph.peek(row, over)
        self.display.set_overlay(plane, None if over is None else self.graph.key(over))
        drawn = all(self.display.frame_results.get(nid, True) is not None for nid in self.graph.drawing())
        if not (drawn and (over is None or plane is not None)):
            return self.playing and self.display.show_proxy(row, under)
        if under != self._spill_under:
            self._spill_under, self._spill_from = under, self.graph.memo.evictions
        if loop_spills(self.window_[1], frame, self.graph.memo.limit) or self.graph.memo.evictions > self._spill_from:
            self.display.keep(row, under, frame, plane, PROXY_BYTES)
        return True

    def _pictured(self):
        """What a proxy pictures, so one kept under another is let go: the shown node's key, the
        overlay's, those of the drawers the memo serves, which hold the footage and every param,
        and the loop's range."""
        walked, g = self._walked_nodes(), self.graph
        drawers = tuple(self._key(nid) for nid, *_ in self.display.drawers if nid not in walked)
        return g.key(g.shown), None if g.over is None else g.key(g.over), drawers, self.window_

    def _row_ready(self, row):
        if row == self.row and self.graph is not None:
            self._show(row)

    def _held_over(self, chain):
        """The chain's results over the window as the runs serve them: those of the clip's walk, or
        else of a walk from the window's first row to its last, a window's own before it; None
        with none."""
        s, n = self.window_
        asks = ((self.runs, (0, self.count)), (self.runs, (s, s + n)), (self.window_runs, (s, s + n)))
        return next((got for runs, walk in asks if (got := runs.over(s, n, chain, walk)) is not None), None)

    def _ask_window(self, by=ASKED):
        """Asks the worker for the window: spared the chain where the runs serve it, by _held_over,
        whose rows are then the window's results at once; else given what they serve of the chain's
        stepped nodes to the window's own walk, so only the rest is stepped. The densities the plot
        shows are folded either way. `by` as set_window's."""
        s, n = self.window_
        chain = self._chain()
        got = self._held_over(chain)
        part = {} if got is not None else self.runs.part(s, n, chain, (s, s + n)) or self.window_runs.part(s, n, chain, (s, s + n))
        self._spared, self._given = got is not None, bool(part)
        self.worker.set_window(s, n, self._spared, self._as_given(part), by)
        self.window_periods = window_periods(self.graph.snapshot(), self.runs, s, n)
        self._show_lines()
        if got is not None:
            self._series_ready(got, s, self.fps)
        else:
            self._show_pinned()

    def _as_given(self, part):
        return as_given(self.graph.snapshot(), part)

    def _take_runs(self, runs):
        self.runs.take(runs)
        self._of_cuts = (None, None, {})

    def _show_held(self, moved=None, changed=None):
        """What is held, or the chain's keys, changed: the strip's bar is over the runs held under
        the keys the chain now has, and the worker is given what they have of the clip. `moved` is
        what Runs.hold returned where one run held is all that changed since the last, and
        `changed` the runs that went or came by it: what is held and listed of a cut in time
        holding no row of `moved` stands, and so do the bar and what the worker has of the clip
        where no run of `changed` has a result of the chain's."""
        chain = self._chain()
        p = None if self.graph is None else self.graph.snapshot()
        under = None if p is None else (self._chain(self._walked_nodes()), self.count)
        again = moved is not None and under == self._of_cuts[0] and p is self._of_plan
        _, periods, listed = self._of_cuts if again else (None, None, {})
        periods = None if self.worker is None else held_periods(p, self.runs, periods, moved)
        self._of_cuts, self._of_plan = (under, periods, {}), p
        own = changed is None or any(nid in run.results for run in changed for nid in chain.keys)
        if own:
            self.timeline.strip.set_held(self.runs.spans(chain))
        if self.worker is not None:
            if own:
                self.worker.give_clip(self.count, self._as_given(self.runs.part(0, self.count, chain, (0, self.count))))
            self.worker.give_periods(periods, touched_periods(p, moved) if again else None)
            self.window_periods.update({of: v for of, v in window_periods(self.graph.snapshot(), self.runs, *self.window_).items()
                                        if v.held and of in self.window_periods})
            self._show_lines()
        if moved is None:
            self._show_stale(chain)
        elif not self._stale_due.isActive():
            self._stale_due.start()
        self._show_pinned()
        self._show_listed(listed, moved)

    def _show_listed(self, was, moved):
        """Each card of a node below a cut in time is shown its values in every cut it is of, as the
        runs held under the keys its walk's chain now has serve them; `was`, node to what it was
        last shown, and `moved` as heldwalks.listed_cuts takes them."""
        if self.graph is None:
            return
        now = self._of_cuts[2]
        for walk in self.graph.snapshot().timed:
            chain = self._chain(walk.chain)
            for nid in walk.chain:
                w, e = self.pane.widget(nid), self.graph.entry(nid)
                if w is not None and e is not None and hasattr(w, "show_listed"):
                    now[nid] = listed_cuts(self.runs, nid, chain, e.cuts, self.count, was.get(nid), moved)
                    w.show_listed(now[nid], self.fps)

    def _show_stale(self, chain):
        """Each card says whether its node is of held.marked, by the tools' files as they lie."""
        entries = {} if self.graph is None else {n.id: e for n in self.doc.nodes if (e := self.graph.entry(n.id)) is not None}
        ran = {nid: e for nid, e in entries.items() if e.file is None}
        seen = {}
        now = {nid: d for nid, e in ran.items() if (d := registry.code_print(e.tool, seen)) is not None}
        above = {nid: [s for s in e.srcs.values() if s is not None] if nid in ran else [] for nid, e in entries.items()}
        stale = held.marked(self.runs, chain, now, above)
        for n in self.doc.nodes:
            self.pane.set_stale(n.id, "its held results were made under other code than its tool's, or a tool's above it, as the files lie now; "
                                      "File, Let Go of Held Results walks them again" if n.id in stale else "")

    def _ask_let_go(self):
        if self.graph is None or not len(self.runs):
            return
        box = QMessageBox(self)
        box.setWindowTitle("Let go of held results")
        box.setText(f"Every result held for {os.path.basename(self.doc.path) if self.doc.path else 'the document'} is let go, and walked again when it is next wanted.")
        buttons = QMessageBox.StandardButton
        box.setStandardButtons(buttons.Discard | buttons.Cancel)
        box.setDefaultButton(buttons.Cancel)
        box.exec()
        if box.standardButton(box.clickedButton()) == buttons.Discard:
            self.let_go()

    def let_go(self):
        """Lets go of every run held, the file's with them, and of the clip walk's results; the
        window is walked again."""
        if self.graph is None:
            return
        self._hold.stop()
        if self._writer is not None:
            self._writer.join()
        self._take_runs([])
        self.clip_results = {}
        self._unwritten = False
        self._write_failed.clear()
        if self._file is not None and os.path.exists(self._file.path):
            try:
                self._file.write([])
            except OSError as e:
                self.timeline.controls.progress.setText(f"could not write {os.path.basename(self._file.path)}: {e}")
        self._ask_window(by=HAND)
        self._show_held()

    def _chain(self, nodes=None):
        """The series chain, or `nodes` of the plan, as held.Runs is told it; one of no nodes with no video open."""
        g = self.graph
        if g is None:
            return held.Chain({}, frozenset(), {})
        return held_chain(g.snapshot(), g.chain if nodes is None else nodes)

    def _walked_nodes(self):
        p = self.graph.snapshot()
        return [*p.chain, *(nid for w in p.timed for nid in w.chain)]

    def _key(self, nid):
        """The key `nid` now has; None for a node the plan does not have."""
        e = self.graph.entry(nid)
        return None if e is None else e.key

    def _window_ready(self, results, start, fps):
        """The window walk's results, held among the window's own once they reach the window's last
        row: they serve the window when it returns, and no walk of the clip, cut or file is handed
        them. One that arrives while a held run is shown is of a walk since left. A walk given
        held rows is not held: its run would hold those rows a second time, and the window is
        stepped from them again for the rest when it returns."""
        if self._spared:
            return
        self._series_ready(results, start, fps)
        if start == self.window_[0] and not self._given:
            self.window_runs.hold(start, self.window_[1], results, self._chain())

    def _series_ready(self, results, start, fps):
        self.results, self.result_start = results, start
        self._cut_again(results)
        self._show_lines()
        self._restate()
        for nid, result in results.items():
            w = self.pane.widget(nid)
            if w is not None and hasattr(w, "show_result"):
                w.show_result(result, start, fps)
        self._update_display()
        self._show_pinned()
        self._show_size()
        self._show_takes()

    # -- the clip walk ---------------------------------------------------
    def _toggle_clip(self):
        if self.worker is None:
            return
        if self._clip_asked:
            self.worker.stop_clip()
            self._clip_asked = False
            self.header.clear_note()
        else:
            self.worker.walk_clip(HAND)
            self._clip_asked = True
            self.header.note.setText("clip: after the window")
        self.header.set_walking(self._clip_asked)

    # -- the bare walk: the clip in a process of its own, bare.py ---------
    def _toggle_bare(self):
        if self._bare is not None:
            self._end_bare("bare: stopped")
        elif self.worker is not None:
            self._start_bare()

    def _start_bare(self):
        folder = tempfile.mkdtemp(prefix="sieve-bare-")
        job = bare.job(self.doc, self.decoder.path, self.tools, os.path.join(folder, "results.pkl"))
        with open(os.path.join(folder, "job.json"), "w", encoding="utf-8") as f:
            json.dump(job, f)
        p = QProcess(self)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONPATH", os.pathsep.join(filter(None, [os.path.dirname(os.path.dirname(os.path.abspath(__file__))), env.value("PYTHONPATH")])))
        p.setProcessEnvironment(env)
        p.readyReadStandardOutput.connect(self._bare_said)
        p.finished.connect(lambda code, _: self._bare is p and self._end_bare(f"bare: its process ended with {code} and no results"))
        self._bare, self._bare_keys, self._bare_t = p, walked_keys(self.graph.snapshot()), time.perf_counter()
        self.header.bar.setRange(0, 0)
        self.header.bar.show()
        self.header.note.setText("bare: starting")
        self.header.bare.setText("Stop bare")
        p.start(sys.executable, ["-X", "utf8", "-m", "sieve_player.bare", os.path.join(folder, "job.json")])

    def _bare_said(self):
        p = self._bare
        while p is not None and self._bare is p and p.canReadLine():
            try:
                said = json.loads(bytes(p.readLine()).decode("utf-8"))
            except ValueError:
                continue
            if "done" in said:
                done, total, rate = said["done"], said["total"], said["rate"]
                self.header.bar.setRange(0, total)
                self.header.bar.setValue(done)
                left = f", {clock((total - done) / rate)} left" if rate else ""
                self.header.note.setText(f"bare: {done} of {total} rows, {rate:.0f} a second{left}")
                self._bare_rate = rate
            elif "period" in said:
                self.header.note.setText(f"bare: a period, {said['period']} of {said['of']}")
            elif "count" in said:
                self.decoder.ends_at(said["count"])   # the bare walk found the stream's end; this process's decoder may not have read that far
                self._shortened(self.decoder.count)
            elif "results" in said:
                took = time.perf_counter() - self._bare_t
                if not self._bare_stands():
                    return
                with open(said["results"], "rb") as f:
                    results, start, fps, periods = pickle.load(f)
                self._end_bare(f"bare: the clip in {clock(took)}, {getattr(self, '_bare_rate', 0.0):.0f} rows a second"
                               + (f"; {', '.join(results)} read back" if results else "")
                               + (f", and {len(periods)} periods" if periods else ""))
                self._take_bare(results, start, fps, periods)
            elif "refused" in said:
                self._end_bare(f"bare: {said['refused']}")
            elif "failed" in said:
                row, nid, text = said["failed"]
                self._end_bare(f"bare: {nid or 'a tool'} raised at row {row}: {text}")

    def _take_bare(self, results, start, fps, periods):
        """What a bare walk left, as bare.py's file has it, is held as a clip walk's is: the clip's
        results at once, so the cuts they make are the plan's before each cut's own are held."""
        if results:
            self._clip_ended = True
            self._clip_ready(results, start, fps)
        for got, first, of in periods:
            self._period_ready(got, first, of, fps)

    def _bare_stands(self):
        """Whether the bare walk under way stands, by the keys it began under; one that does not is ended, its results dropped."""
        if self._bare is None or stands(self._bare_keys, self.graph.snapshot()):
            return True
        self._end_bare("bare: the key of a node it walks moved, and its results were dropped")
        return False

    def _end_bare(self, note=""):
        p, self._bare = self._bare, None
        if p is None:
            return
        if p.state() != QProcess.NotRunning:
            p.kill()
            p.waitForFinished(2000)
        p.deleteLater()
        self.header.bar.hide()
        self.header.note.setText(note)
        self.header.bare.setText("Walk bare")

    def _paced(self, lane, done, total, ran):
        self.pace.row(lane, done, total, ran)
        self.header.figure.set_figure(self.pace.figure(self.fps, self.count))

    def _clip_walked(self, done, total, ran):
        self._paced("clip", done, total, ran)
        self._clip_ended = self._clip_rests = done >= total > 0     # the results that follow are a walk's own, held at once
        if self._clip_asked:
            self.header.clear_note()
            if done >= total:
                self._clip_asked = False
                self.header.set_walking(False)

    def _period_walked(self, done, total, left):
        """The clip lane walks a cut in time behind the clip's own range: the header says so, and the
        walk is the clip walk's to stop until the last cut ends."""
        self._clip_asked = done < total or bool(left)
        self.header.set_walking(self._clip_asked)
        self.header.note.setText(f"clip: a period, {done} of {total} rows, {left} periods behind it"
                                 if self._clip_asked else "")

    def _period_ready(self, results, start, of, fps):
        """The cut in time `of`, as period_run takes it, walked whole from its first row, `start`:
        held as a run of that cut under the chain of the timed Walk its nodes are of, with the
        walked node's rows it was stepped over."""
        run = period_run(self.graph.snapshot(), results, start, of)
        if run is not None:
            self._hold_run(run.start, run.rows, run.results, run.chain, run.cut, of_clip=True, walked=run.walked)

    def _window_period_walked(self, done, total, left):
        """The window walks a cut in time behind its own range: the progress line says so until the last ends."""
        ct = self.timeline.controls
        if done < total or left:
            ct.progress.setText(f"window: a period, {done} of {total} rows, {left} periods behind it")
        elif ct.progress.text().startswith("window: a period"):
            ct.progress.setText("")

    def _window_period_ready(self, results, start, of, fps):
        """The window's walk of one cut in time, `of` as window_periods keys it; one of a window
        since left, or of a cut whose walk is held, is dropped."""
        got = self.window_periods.get(of)
        if got is not None and not got.held and got.start == start:
            self.window_periods[of] = Shown(start, results, got.best, False)
            self._show_lines()
            self._update_display()
            self._show_pinned()

    def _show_lines(self):
        """The plot is handed each node's line in pieces: the window walk's from its first row, and
        one a period the window shows, each from the row its results begin at and said best effort
        where window_periods says so of its node."""
        lines = {}
        for start, results, best in [(self.result_start, self.results, ()), *((v.start, v.results, v.best) for v in self.window_periods.values())]:
            for nid, r in results.items():
                if isinstance(r, dict) and "signal" in r:
                    lines.setdefault(nid, []).append((r["signal"], r.get("gate"), start, nid in best))
        self.plot.set_lines(lines)

    def _clip_ready(self, results, start, fps):
        self.clip_results = results
        stands, rows = self._stands()
        if stands and self._clip_ended:
            self._clip_ended = False
            self._hold_run(0, rows, stands, of_clip=True)
        elif stands:
            self._hold.start()      # a rerun of the chain over a walk long ended: held once the knob is at rest
        self._show_pinned()

    def _stands(self):
        """The clip's results that are a run from row 0, and its rows: those that reach furthest,
        where they reach the clip's last row or the clip walk rests, stopped short of it or
        refused; ({}, 0) while it walks and with none."""
        has = {nid: r for nid, r in self.clip_results.items() if isinstance(r, dict) and "signal" in r}
        rows = max((len(r["signal"]) for r in has.values()), default=0)
        if not rows or not (self._clip_rests or rows == self.count):
            return {}, 0
        return {nid: r for nid, r in has.items() if len(r["signal"]) == rows}, rows

    def _write_held(self, wait=False):
        """A clip walk's results that stand are held as a run, and the runs held since the checkpoint
        was written go into it when the document has been saved, on a thread of their own, which
        pickles only the runs the file has not had; `wait` returns once the file has landed. A
        write that did not land is made again with the next, the one at the video's close included."""
        if self.graph is None:
            return
        stands, rows = self._stands()
        self._hold_run(0, rows, stands)
        self._hold.stop()
        path = held.path_for(self.doc.path)
        busy = self._writer is not None and self._writer.is_alive()
        if busy and wait:
            self._writer.join()
        elif busy and self._unwritten:
            return self._hold.start()       # one file, one writer: this one's turn comes when that one lands
        if self._write_failed.is_set() and not self._writer.is_alive():
            self._write_failed.clear()
            self._unwritten = True
        if path and self._unwritten:
            self._unwritten = False
            if self._file is None or self._file.path != path:
                self._file = held.File(path)       # the document saved under another name: nothing there is known to be this one's
            self._writer = threading.Thread(target=_save_held, args=(self._file, list(self.runs), self._write_failed), name="held")
            self._writer.start()
            if wait:
                self._writer.join()

    def _hold_run(self, start, rows, results, chain=None, cut=None, of_clip=False, walked=None):
        """Holds `results` as a run where held.Runs.hold does, under `chain`, the window's with none,
        inside a cut of rows `cut`, with `walked` as hold takes it, weighed against the others by
        every walk's chain; and one held is written once nothing more has been for HOLD_MS. A run
        `of_clip` is a clip walk's. The cuts are made again only where a run that went or came has
        a result some cutting node is cut by: no other run moves a cut."""
        was = set(self.runs)
        if moved := self.runs.hold(start, rows, results, chain or self._chain(), cut, worth=self._chain(self._walked_nodes()), walked=walked):
            self._unwritten = True
            self._hold.start()
            changed = was ^ set(self.runs)
            self._show_held(moved, changed)
            gates = self._cut_by_nodes()
            if any(nid in run.results for run in changed for nid in gates):
                self._recut(resume=of_clip)

    def _cut_by_nodes(self):
        """The nodes wired into a cutting node's CUT_BY input."""
        wires = ((by, n.id) for n in self.doc.nodes if (by := registry.cut_by(self.tools.get(n.tool))))
        return {w.src for by, nid in wires if (w := self.doc.source(nid, by[0]))}

    def _cut_result(self, nid, key, within):
        """What plan.plan asks of a cutting node `nid` cut by a result on a wire over `within`, a
        cut.Record: the result of the node wired there under `key`, as a held run from row 0 to the
        clip's last row has it, or for a cut in time a run of that cut walked whole; with neither,
        as heldwalks.window_gate_result has it, a plan.Provisional; None with none."""
        by = registry.cut_by(self.tools.get(self.doc.node(nid).tool))
        w = by and self.doc.source(nid, by[0])
        if not w:
            return None
        got = gate_result(self.runs, w.src, key, within, self.count)
        if got is None and (seen := window_gate_result(self.results, self.result_start, w.src, key, within)):
            return Provisional(*seen)
        return got

    def _cut_again(self, results):
        """The window walked `results`: where one is of a node whose result a cutting node waits on or
        is cut provisionally by, the cuts are made again. Nothing is asked where none is."""
        unheld = self.graph.snapshot().unheld
        if unheld and any((w := self.doc.source(nid, by[0])) and w.src in results
                          for nid in unheld if (by := registry.cut_by(self.tools.get(self.doc.node(nid).tool)))):
            self._recut()

    def _recut(self, resume=False, by_count=False):
        """The graph synced where a cutting node is cut by a result on a wire, or any cutting node
        where `by_count` says the count moved, and where the cuts they then make are not those they
        made, the walk begun again over them, and the clip walk asked again where it was asked or
        `resume` says a clip walk's run made them. Where a run held moved only cuts in time, nothing
        the own ranges walk, each lane walks the cuts now made and neither own range begins again."""
        if self.graph is None:
            return
        of = registry.cuts if by_count else registry.cut_by
        cutting = lambda: {nid: e.cuts for nid, e in self.graph.snapshot().entries.items() if of(e.tool)}
        was, ranges = cutting(), self._own_ranges()
        if not was:
            return
        self.graph.sync()
        if cutting() == was:
            return
        if not by_count and self._own_ranges() == ranges:
            self._walk_periods_again()
            return
        walking = self._clip_asked
        self._restate()
        self._invalidate()
        self.goto(self.row, commit=True)
        if walking or resume:
            self._toggle_clip()

    def _own_ranges(self):
        """What the window's and the clip's own ranges walk under: the walked node and each chain node, their keys and cuts."""
        p = self.graph.snapshot()
        return {nid: (p.entries[nid].key, p.entries[nid].cuts) for nid in [p.walk, *p.walks, *p.chain] if nid in p.entries}

    def _clip_result(self, nid):
        """The clip's result for `nid`: the clip walk's, or the held run's from row 0 that reaches
        further under the key the node now has; None with neither."""
        r = self.clip_results.get(nid)
        if self.graph is None:
            return r
        key = self._key(nid)
        if not held.good(r, key):
            r = None        # of a key the node has left, where the walk it came from had no rows to run the chain over again
        best = self.runs.from_first_row(nid, key)
        return r if best is None or (isinstance(r, dict) and "signal" in r and len(r["signal"]) >= best.rows) else best.results[nid]

    def _result_bytes(self, nid, result):
        e = None if self.graph is None else self.graph.entry(nid)
        return wire.result_bytes(None if e is None else e.produces, result)

    def _show_size(self):
        """The selected node's card says about what its result over the clip would add to the held
        file, from the window's rows."""
        if self.selection is not None:
            per = held.per_row(self.results.get(self.selection))
            figure, unit = held.in_units(per * self.count) if per else ("", "")
            self.pane.set_size(self.selection, f"~{figure} {unit}" if per else "", unit, f"about {figure} {unit} held over the clip")

    def _show_takes(self):
        """The selected node's card says about how long its own work would take over the clip, every
        row at what ledger.row_cost makes of the key it now has; nothing where that is None."""
        nid = self.selection
        if nid is None or self.ledger is None or self.graph is None:
            return
        cost = row_cost(self.ledger.view().walks, nid, self._key(nid))
        if cost is None:
            self.pane.set_takes(nid, "")
            return
        ms, n, lane = cost
        s = ms * self.count / 1000
        text = f"{s * 1000:.0f} ms" if s < 1 else f"{s:.1f} s" if s < 10 else f"{s:.0f} s" if s < 60 else clock(s)
        self.pane.set_takes(nid, f"~{text}", f"about {text} of this node's own work over the clip's {self.count} rows, "
                                             f"at {ms:.2f} ms a run over the {lane} walk's {n}")

    def _clip_refused(self, why):
        self._clip_asked = False
        self.header.set_walking(False)
        self.header.note.setText(why)

    def _show_pinned(self):
        """The strip draws every shown node that has a signal: the clip's when there is one, walked or
        held, else the window's, and with it the node's signal over the rows of every other run held
        under the key it now has that nothing drawn before it is over, the run that began earliest
        first as held.Runs.over serves, so no row is drawn twice. A node below a cut in time has no
        range of its own: its signal is over each run held under its key, or with none held over
        each period the window walked."""
        series, more = {}, {}
        below = set() if self.graph is None else {nid for w in self.graph.snapshot().timed for nid in w.chain}
        for nid in document.shown(self.selection, self.doc.pinned) if self.doc is not None else []:
            if (r := self._clip_result(nid)) is not None:
                start = 0
            else:
                r, start = self.results.get(nid), self.result_start
            if isinstance(r, dict) and "signal" in r:
                series[nid] = (r["signal"], start, r.get("gate"))
                more[nid] = self.runs.beside(nid, self._key(nid), start, len(r["signal"]))
            elif nid in below and (pieces := self.runs.beside(nid, self._key(nid), 0, 0) or [
                    (v.results[nid]["signal"], v.start, v.results[nid].get("gate")) for v in self.window_periods.values()
                    if isinstance(v.results.get(nid), dict) and "signal" in v.results[nid]]):
                series[nid], more[nid] = pieces[0], pieces[1:]
        self.timeline.strip.set_series(series, self.selection, more)

    def _set_length(self, rows):
        """The plot's x axis is the window, so a walk fills in at its place instead of stretching."""
        self.plot.set_window(self.window_[0], rows, self.fps)

    def _hover(self, row):
        """One cursor for the strip and the plot; -1 clears it."""
        self.plot.set_hover(row)
        self.timeline.strip.set_hover(row)

    def _update_display(self):
        below = shown_at(self.window_periods, self.row)    # a node below a cut in time: its result over the period holding the row
        self.display.set_state(self.row, {**self.results, **{nid: r for nid, (r, _) in below.items()}}, self.result_start,
                               {nid: start for nid, (_, start) in below.items()})

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
        if not self._leaving():
            e.ignore()
            return
        self.timer.stop()
        self._unload()
        super().closeEvent(e)
