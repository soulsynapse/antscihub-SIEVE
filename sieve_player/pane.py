"""The parameter pane: the selected node's settings.

One surface per node, built once per document and shown one at a time: the widget the tool's
`settings()` returns, with its knobs moved to the node's params. The document is the store and the
widget a view over it, as a Houdini parameter pane is over its node: the widget must take the
stored values (`set_params`) and its knobs are the node's whole param set, so a tool whose
`settings()` returns anything less is shown as a defect, not as its own defaults. Two parts are SIEVE's own. The
video node's is a picker, the chosen path and what cv2 says about the file; while a selector is
wired in, the picker is greyed and the selector picks. A selector's card is its settings and a
note of what its rule matched, which the window writes. Under a tool that
exports sits the target it would write, an Export button that runs the tool's argv in a QProcess,
and the process's last line; a tool takes part by defining `output_name(src, params) -> path` and
`export_command(src, dst, params, fps) -> argv`, and may add `describe_output(src, params, fps)
-> str` for the line under the target. Under a frame node's settings sits its density, the
population its plane's values make per row of the loop window, which the window hands the pane for
every fed frame node; a node whose output is a mask or a field, or that the video does not
reach, shows none. A node whose tool the catalogue lacks shows which name was
not found and its params read-only. The pane writes params into the document and says which node
changed; it knows nothing of the runtime.
"""
import os
import re
from functools import lru_cache

import cv2
from PySide6.QtCore import QProcess, QSize, Qt, Signal
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QFileDialog, QFrame, QPushButton, QScrollArea, QVBoxLayout, QWidget

from .document import VIDEO_TOOL, is_selector, paths
from .theme import GAP, PAD, WIDE_W, Form, Layer, measured, readout
from .widgets import Density

VIDEO_FILTER = "Video (*.mp4 *.MP4 *.avi *.mov *.mkv);;All (*)"


@lru_cache(maxsize=16)
def _probe(path, mtime):
    cap = cv2.VideoCapture(path)
    try:
        if not cap.isOpened():
            raise IOError(f"cannot open {path}")
        return (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                cap.get(cv2.CAP_PROP_FPS) or 30.0, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
    finally:
        cap.release()


def probe(src):
    """(width, height, fps, count) via cv2, cached per path and mtime. The count is the container's
    claim; the decoder trusts the stream over it."""
    src = str(src)
    return _probe(src, os.stat(src).st_mtime)


def free_name(dst):
    """`dst` if nothing is there, else the first `stem-2.ext`, `stem-3.ext`... that is free."""
    if not os.path.exists(dst):
        return dst
    root, ext = os.path.splitext(dst)
    root = re.sub(r"-\d+$", "", root)
    n = 2
    while os.path.exists(f"{root}-{n}{ext}"):
        n += 1
    return f"{root}-{n}{ext}"


def _column(parent, spacing=GAP):
    lay = QVBoxLayout(parent)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(spacing)
    return lay


class Video(QWidget):
    """The video node's settings: a picker, the chosen path and what cv2 says about it."""
    sourceChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = _column(self)
        self.button = QPushButton("Choose…")
        self.path, self.info = readout("no video"), readout()   # info: the file's facts, or the error
        form = Form([("video", self.button)])
        form.add_line(self.path)
        form.add_line(self.info)
        lay.addWidget(form)
        self.button.clicked.connect(self._pick)

    def _pick(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open video", "", VIDEO_FILTER)
        if path:
            self.sourceChanged.emit(path)

    def show_source(self, path):
        w, h, fps, n = probe(path)
        self.path.setText(str(path))
        self.info.setText(f"{w}×{h} · {fps:.2f} fps · {n} frames · {n / fps:.1f} s")

    def show_error(self, path, err):
        self.path.setText(str(path))
        self.info.setText(f"could not open: {err}")

    def show_none(self, why):
        """The selector answered nothing: the one line that says why, under whatever path is still open."""
        self.info.setText(why)

    def set_picker(self, free, by=None):
        """The picker is live while nothing is wired into the video node; wired, `by` names the
        node that picks instead, and the button says so."""
        self.button.setEnabled(free)
        self.button.setToolTip("" if free else f"{by} picks the video; unwire it to choose by hand")


class Export(QWidget):
    """The export block under a tool that defines `export_command`."""

    def __init__(self, tool, parent=None):
        super().__init__(parent)
        self.tool = tool
        lay = _column(self)
        self.target, self.detail = measured(wide=True), readout()
        self.button, self.status = QPushButton("Export"), readout()
        self.form = Form([("target", self.target)])
        self.form.add_line(self.detail)
        self.form.add_row("export", self.button)
        self.form.add_line(self.status)
        lay.addWidget(self.form)
        self.button.clicked.connect(self._export)
        self.button.setEnabled(False)
        self.proc, self.src, self.fps, self.params = None, None, None, {}
        self._describe()

    def set_source(self, path, fps):
        self.src, self.fps = path, fps
        self.button.setEnabled(path is not None)
        self._describe()

    def set_params(self, params):
        self.params = dict(params)
        self._describe()

    def _target(self):
        return free_name(self.tool.output_name(self.src, self.params))

    def _describe(self):
        if self.src is None:
            self.target.setText("")
            self.detail.setText("pick a video on the video node")
            return
        dst = self._target()
        self._name = os.path.basename(dst)
        self._elide()
        self.target.setToolTip(dst)
        describe = getattr(self.tool, "describe_output", None)
        self.detail.setText(describe(self.src, self.params, self.fps) if describe else "")

    _name = ""

    def _elide(self):
        metrics = QFontMetrics(self.target.font())
        self.target.setText(metrics.elidedText(self._name, Qt.ElideMiddle, self.target.width() - 12))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._name:
            self._elide()

    def _export(self):
        if self.proc is not None:
            self.proc.kill()
            return
        dst = self._target()
        cmd = self.tool.export_command(self.src, dst, self.params, self.fps)
        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._progress)
        self.proc.finished.connect(lambda code, _: self._done(code, dst))
        self.proc.start(cmd[0], cmd[1:])
        self.button.setText("Cancel")
        self.status.setText(f"writing {os.path.basename(dst)}")

    def _progress(self):
        text = bytes(self.proc.readAllStandardOutput()).decode(errors="replace").replace("\r", "\n")
        lines = [s for s in text.split("\n") if s.strip()]
        if lines:
            self.status.setText(lines[-1].strip())

    def _done(self, code, dst):
        self.proc = None
        self.button.setText("Export")
        if code == 0:
            self.status.setText(f"wrote {os.path.basename(dst)}")
        else:
            if os.path.exists(dst):
                os.remove(dst)  # a cancelled or failed run leaves no partial file behind
            self.status.setText(f"exited {code}; nothing written")
        self._describe()


class Pane(QWidget):
    """`tools` is the catalogue, name to module. `select(nid)` shows that node's surface, None
    shows nothing. `video` is the video node's widget, `widget(nid)` a tool node's settings widget,
    `exports[nid]` the Export under a node whose tool exports. Its size hint is the shown card's
    height, so a host that stacks it under the canvas gives it only the room its content needs."""
    paramsChanged = Signal(str)   # this node's params in the document changed here
    videoPicked = Signal(str)

    def __init__(self, tools, parent=None):
        super().__init__(parent)
        self.tools = tools
        self.doc = None
        self.cards, self.widgets, self.exports, self.notes = {}, {}, {}, {}
        self.densities = {}   # frame node -> its Density plot, hidden until the window hands it counts
        self.video = None
        self.current = None
        self._src, self._fps = None, None
        lay = _column(self, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._host = QWidget()
        self._lay = _column(self._host)
        self._lay.setContentsMargins(0, 0, GAP, 0)   # room for the scrollbar
        self._lay.addStretch(1)
        scroll.setWidget(self._host)
        self._host.installEventFilter(self)
        lay.addWidget(scroll)
        self.setMinimumWidth(WIDE_W + 2 * PAD + GAP)   # one form and the scrollbar's gutter

    def set_document(self, doc):
        for nid in list(self.cards):
            self._drop(nid)
        self.doc = doc
        for node in doc.nodes:
            self._build(node)
        self.select(None)

    def sync(self):
        """The document's nodes changed: a card per node, none for a node that is gone."""
        ids = {n.id for n in self.doc.nodes}
        for nid in list(self.cards):
            if nid not in ids:
                self._drop(nid)
        for node in self.doc.nodes:
            if node.id not in self.cards:
                self._build(node)
        if self.current not in self.cards:
            self.select(None)

    def _drop(self, nid):
        card = self.cards.pop(nid)
        self.widgets.pop(nid, None)
        self.exports.pop(nid, None)
        self.notes.pop(nid, None)
        self.densities.pop(nid, None)
        if self.video is not None and self.video.parent() is card:
            self.video = None
        self._lay.removeWidget(card)
        card.hide()
        card.setParent(None)
        card.deleteLater()

    def _build(self, node):
        card = Layer(1, node.id)
        if node.tool == VIDEO_TOOL:
            self.video = Video()
            self.video.sourceChanged.connect(self.videoPicked)
            card.add(self.video)
        elif node.unresolved:
            card.add(readout(f"tool {node.tool!r} not found"))
            for k, v in node.params.items():
                card.add(readout(f"{k} = {v!r}", mono=True))
        else:
            tool = self.tools[node.tool]
            w = tool.settings()
            if not all(hasattr(w, a) for a in ("changed", "params", "set_params")):
                # the document is the store and the widget a view over it; one that cannot be told
                # the stored values would show its own, so it is not shown at all
                card.add(readout(f"{node.tool}.settings() must return a ParamWidget (or one with "
                                 f"changed, params() and set_params()); got {type(w).__name__}"))
                w.deleteLater()
                w = None
            else:
                w.set_params(node.params)     # before changed is connected: moving the knobs is not a change
                w.changed.connect(lambda nid=node.id: self._changed(nid))
                card.add(w)
                self.widgets[node.id] = w
                if is_selector(tool) or paths(tool):
                    self.notes[node.id] = readout()
                    card.add(self.notes[node.id])
                elif getattr(tool, "KIND", "frame") == "frame":
                    self.densities[node.id] = Density()
                    self.densities[node.id].hide()
                    card.add(self.densities[node.id])
            if w is not None and getattr(tool, "export_command", None) is not None:
                ex = Export(tool)
                ex.set_params(node.params)
                ex.set_source(self._src, self._fps)
                card.add(ex)
                self.exports[node.id] = ex
        card.hide()
        self._lay.insertWidget(self._lay.count() - 1, card)
        self.cards[node.id] = card

    def _changed(self, nid):
        node = self.doc.node(nid)
        node.params = self.widgets[nid].params()   # the knobs are the whole set; a param a tool dropped goes with it
        if nid in self.exports:
            self.exports[nid].set_params(node.params)
        self.paramsChanged.emit(nid)

    def select(self, nid):
        self.current = nid if nid in self.cards else None
        for i, card in self.cards.items():
            card.setVisible(i == self.current)
        self.updateGeometry()

    def sizeHint(self):
        """As tall as the shown card at the pane's width; the host caps it and the scroll area takes
        the overflow. A wrapping label's plain hint guesses a width, so the card is asked at the real one."""
        card = self.cards.get(self.current)
        if card is None:
            return QSize(super().sizeHint().width(), 0)
        m = self._lay.contentsMargins()
        w = self.width() - m.left() - m.right()
        h = card.heightForWidth(w) if card.hasHeightForWidth() and w > 0 else card.sizeHint().height()
        return QSize(super().sizeHint().width(), h + m.top() + m.bottom())

    def eventFilter(self, obj, e):
        if obj is self._host and e.type() == e.Type.LayoutRequest:
            self.updateGeometry()   # a card's content changed; the scroll area would not pass it on
        return super().eventFilter(obj, e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if e.oldSize().width() != e.size().width():
            self.updateGeometry()   # wrapping labels need a different height at a different width

    def minimumSizeHint(self):
        return QSize(super().minimumSizeHint().width(), 0)

    def widget(self, nid):
        return self.widgets.get(nid)

    def show_density(self, counts, start):
        """`counts` is {frame node: (rows, bins)} for every plane the walk computed: a node in it shows
        them, and one not in it, whose output is a mask or a field or that the video does not reach,
        shows no plot."""
        for nid, plot in self.densities.items():
            if nid in counts:
                plot.set_series(counts[nid], start)
                plot.show()
            else:
                plot.hide()

    def set_playhead(self, row):
        for plot in self.densities.values():
            plot.set_playhead(row)

    def note(self, nid, text):
        """The line under a selector's settings, what its rule matched, or under a tool with path
        inputs, which files were picked for them."""
        if nid in self.notes:
            self.notes[nid].setText(text)

    def set_source(self, path, fps):
        """The video every Export writes from; None when nothing is loaded."""
        self._src, self._fps = path, fps
        for ex in self.exports.values():
            ex.set_source(path, fps)
