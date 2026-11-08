"""The parameter pane: one card per node, built once per document, shown one at a time.

The document is the store and a card a view over it, as a Houdini parameter pane is over its node:
a tool's settings widget must take the stored values and its knobs are the node's whole param set,
so one that cannot be told them is shown as a defect, never as its own defaults. The pane writes
params, bands and the pin into the document and says what changed; it knows nothing of the
runtime, and what it shows of a run, the density, the trace, the standing line, the window hands it.
"""
import os
import re

from PySide6.QtCore import QProcess, QSize, Qt, Signal
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFileDialog, QFrame, QPushButton, QScrollArea, QVBoxLayout,
                               QWidget)

from .document import (OPEN, VIDEO_OUTPUT, VIDEO_OUTPUTS, VIDEO_PRODUCES, VIDEO_SCALE, VIDEO_TOOL, is_selector, mode_of,
                       paths, video_output, video_scale)
from .theme import CONTROL_W, GAP, PAD, WIDE_W, Form, GlyphButton, Layer, measured, readout
from .widgets import Density, Trace

VIDEO_FILTER = "Video (*.mp4 *.MP4 *.avi *.mov *.mkv *.mts *.MTS);;All (*)"


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
    """The video node's settings: a picker, the chosen path and what cv2 says about it, and the
    decoder's two params, `output`, bgr as decoded, gray or luma, and `scale`, a factor, both applied
    before its cache so a chain that wants small gray frames never holds the large colour ones."""
    sourceChanged = Signal(str)
    paramChanged = Signal(str, object)     # (param name, value)

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = _column(self)
        self.button = QPushButton("Choose…")
        self.path, self.info = readout("no video"), readout()   # info: the file's facts, or the error
        form = Form([("video", self.button)])
        form.add_line(self.path)
        form.add_line(self.info)
        self.output = QComboBox()
        self.output.addItems(list(VIDEO_OUTPUTS))
        self.output.setFixedWidth(CONTROL_W)
        form.add_row(VIDEO_OUTPUT, self.output)
        self.output_note = readout()
        form.add_line(self.output_note)
        self.scale = QDoubleSpinBox()
        self.scale.setRange(0.05, 1.0)
        self.scale.setSingleStep(0.05)
        self.scale.setDecimals(2)
        self.scale.setFixedWidth(CONTROL_W)
        form.add_row(VIDEO_SCALE, self.scale)
        lay.addWidget(form)
        self.button.clicked.connect(self._pick)
        self.output.currentTextChanged.connect(self._note_output)
        self.output.currentTextChanged.connect(lambda v: self.paramChanged.emit(VIDEO_OUTPUT, v))
        self.scale.valueChanged.connect(lambda v: self.paramChanged.emit(VIDEO_SCALE, float(v)))
        self._note_output(self.output.currentText())

    OUTPUT_NOTES = {
        "bgr": "as decoded",
        "gray": "full range, 0 to 255; from the stream's luma plane where it has one, with no colour conversion",
        "luma": "the stream's luma plane as is: fastest, and limited range, 16 to 235, on most camera files",
    }

    def _note_output(self, value):
        self.output_note.setText(self.OUTPUT_NOTES.get(value, ""))

    def set_params(self, doc):
        """Moves the knobs to the document's values without reporting a change."""
        for w, v in ((self.output, video_output(doc)), (self.scale, video_scale(doc))):
            w.blockSignals(True)
            w.setCurrentText(v) if w is self.output else w.setValue(v)
            w.blockSignals(False)
        self._note_output(video_output(doc))

    def _pick(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open video", "", VIDEO_FILTER)
        if path:
            self.sourceChanged.emit(path)

    def show_source(self, path, facts):
        """`facts` is (width, height, fps, count), as the decoder found them."""
        w, h, fps, n = facts
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
    """The export block under a tool that defines `export_command(src, dst, params, fps) -> argv`
    and `output_name(src, params) -> path`: the target, a button that runs the argv in a QProcess,
    and the process's last line; `describe_output(src, params, fps) -> str`, if defined, is the
    line under the target."""

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


class BakeBlock(QWidget):
    """The block under a tool declaring BAKES: the node's mode, the button that asks the window
    for a bake and cancels one running, and the line that says how far it is or why it stopped."""
    asked = Signal()
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = _column(self)
        self.mode, self.button, self.status = readout(mono=True), QPushButton("Bake"), readout()
        self.form = Form([("mode", self.mode), ("bake", self.button)])
        self.form.add_line(self.status)
        lay.addWidget(self.form)
        self.running = False
        self.button.clicked.connect(lambda: (self.cancelled if self.running else self.asked).emit())

    def set_mode(self, mode):
        self.mode.setText(mode or "")

    def set_progress(self, done, total):
        self.running = done < total
        self.button.setText("Cancel" if self.running else "Bake")
        self.status.setText(f"baking {done}/{total}" if self.running else f"baked {total} rows" if total else "")

    def set_refused(self, why):
        self.running = False
        self.button.setText("Bake")
        self.status.setText(why)


class Pane(QWidget):
    """`tools` is the catalogue, name to module. `select(nid)` shows that node's surface, None
    shows nothing. `video` is the video node's widget, `widget(nid)` a tool node's settings widget,
    `exports[nid]` the Export under a node whose tool exports. Its size hint is the shown card's
    height, so a host that stacks it under the canvas gives it only the room its content needs."""
    paramsChanged = Signal(str)   # this node's params in the document changed here
    pinChanged = Signal()         # the document's pinned flag moved here
    videoPicked = Signal(str)
    bakeAsked = Signal(str)       # the Bake button under this node
    bakeCancelled = Signal(str)

    def __init__(self, tools, parent=None):
        super().__init__(parent)
        self.tools = tools
        self.doc = None
        self.cards, self.widgets, self.exports, self.notes = {}, {}, {}, {}
        self.standings = {}   # tool node -> the line under its settings, see set_standing
        self.densities = {}   # frame node -> its Density plot, hidden until the window hands it counts
        self.traces = {}      # series node -> its Trace, hidden until the window hands it a result
        self.pins = {}        # series node -> the pin in its card's corner
        self.bakes = {}       # node whose tool BAKES -> its BakeBlock
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
        self.standings.pop(nid, None)
        self.densities.pop(nid, None)
        self.traces.pop(nid, None)
        self.pins.pop(nid, None)
        self.bakes.pop(nid, None)
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
            self.video.set_params(self.doc)
            self.video.sourceChanged.connect(self.videoPicked)
            self.video.paramChanged.connect(lambda name, v, nid=node.id: self._video_param(nid, name, v))
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
                self.standings[node.id] = readout()
                self.standings[node.id].hide()
                card.add(self.standings[node.id])
                if hasattr(w, "set_source"):
                    w.set_source(self._src, self._fps)
                if is_selector(tool) or paths(tool):
                    self.notes[node.id] = readout()
                    card.add(self.notes[node.id])
                kind = getattr(tool, "KIND", "frame")   # "same" takes both plots: the walk fills the one its wire's kind has
                if is_selector(tool):
                    pass
                if kind in ("frame", "same"):
                    plot = Density()
                    if node.band is not None:
                        plot.levels = [float(v) for v in node.band]
                    plot.levelReleased.connect(lambda _i, _v, nid=node.id: self._banded(nid))   # the picture crops as it moves; the data when let go
                    plot.hide()
                    card.add(plot)
                    self.densities[node.id] = plot
                if kind in ("series", "same"):
                    plot = Trace(rows=5, levels=2)
                    plot.levels[:] = [float(v) for v in node.band] if node.band is not None else list(OPEN)
                    plot.levelDragged.connect(lambda _i, _v, nid=node.id: self._banded(nid))    # the chain reruns on the stack already walked, cheap enough to follow the drag
                    plot.levelReleased.connect(lambda _i, _v, nid=node.id: self._banded(nid))
                    plot.hide()
                    card.add(plot)
                    self.traces[node.id] = plot
                    pin = GlyphButton("pin", "pinned", "draw this signal on the timeline")
                    pin.setChecked(self.doc.pinned == node.id)
                    pin.clicked.connect(lambda on, nid=node.id: self._pin(nid, on))
                    card.add_corner(pin)
                    self.pins[node.id] = pin
            if w is not None and getattr(tool, "BAKES", None):
                block = BakeBlock()
                block.set_mode(mode_of(self.doc, self.tools, node.id))
                block.asked.connect(lambda nid=node.id: self.bakeAsked.emit(nid))
                block.cancelled.connect(lambda nid=node.id: self.bakeCancelled.emit(nid))
                card.add(block)
                self.bakes[node.id] = block
            if w is not None and getattr(tool, "export_command", None) is not None:
                ex = Export(tool)
                ex.set_params(node.params)
                ex.set_source(self._src, self._fps)
                card.add(ex)
                self.exports[node.id] = ex
        card.hide()
        self._lay.insertWidget(self._lay.count() - 1, card)
        self.cards[node.id] = card

    def _banded(self, nid):
        """A density or trace handle moved: the band is the node's, saved and keyed like a param."""
        plot = self.densities.get(nid) or self.traces[nid]
        self.doc.node(nid).band = tuple(plot.levels)
        self.paramsChanged.emit(nid)

    def _pin(self, nid, on):
        """A pin was clicked: the flag lands on `nid` or leaves it, and every pin shows where it is."""
        self.doc.pinned = nid if on else None
        for i, pin in self.pins.items():
            pin.setChecked(i == self.doc.pinned)
        self.pinChanged.emit()

    def _video_param(self, nid, name, value):
        """A video node knob moved: its param, saved and keyed like any node's."""
        self.doc.node(nid).params[name] = value
        self.paramsChanged.emit(nid)

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

    def show_series(self, results, start):
        """`results` is {series node: result} for the chain the walk ran, each with "gate" (see
        `graph.gated`): a node in it with a signal shows it, and any other series node shows no plot."""
        for nid, plot in self.traces.items():
            r = results.get(nid)
            if isinstance(r, dict) and "signal" in r:
                plot.set_series(r["signal"], start, r.get("gate"))
                plot.show()
            else:
                plot.hide()

    def show_bake(self, nid, done, total):
        if nid in self.bakes:
            self.bakes[nid].set_progress(done, total)

    def bake_refused(self, nid, why):
        if nid in self.bakes:
            self.bakes[nid].set_refused(why)

    def show_modes(self):
        """Every mode line follows the document, after a bake lands or a document is reopened."""
        for nid, block in self.bakes.items():
            block.set_mode(mode_of(self.doc, self.tools, nid))

    def set_playhead(self, row):
        for plot in (*self.densities.values(), *self.traces.values()):
            plot.set_playhead(row)

    def note(self, nid, text):
        """The line under a selector's settings, what its rule matched, or under a tool with path
        inputs, which files were picked for them."""
        if nid in self.notes:
            self.notes[nid].setText(text)

    def set_standing(self, nid, text):
        """The line under `nid`'s settings: why it does not run, or what its run said, from the
        runtime through the window; "" hides it."""
        lab = self.standings.get(nid)
        if lab is not None:
            lab.setText(text)
            lab.setVisible(bool(text))

    def set_source(self, path, fps):
        """The video every Export, and every settings widget with a `set_source`, writes from; None
        when nothing is loaded."""
        self._src, self._fps = path, fps
        for w in (*self.exports.values(), *[w for w in self.widgets.values() if hasattr(w, "set_source")]):
            w.set_source(path, fps)
