"""The parameter pane: one card per node, built once per document, shown one at a time.

The document is the store and a card a view over it, as a Houdini parameter pane is over its node:
a tool's settings widget must take the stored values and its knobs are the node's whole param set,
so one that cannot be told them is shown as a defect, never as its own defaults. The pane writes
params into the document and says what changed; it knows nothing of the runtime, and what it
shows of a run, the standing line and a card's badges, the window hands it. A node's plot is the window's, under the frame.
"""
import os

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QComboBox, QFileDialog, QFrame, QPushButton, QScrollArea, QVBoxLayout, QWidget

from .document import VIDEO_OUTPUT, VIDEO_OUTPUTS, VIDEO_TOOL, is_selector, paths, video_output
from .theme import CONTROL_W, GAP, HELD, PAD, WIDE_W, Badge, CloseMark, Form, Layer, readout

VIDEO_FILTER = "Video (*.mp4 *.MP4 *.avi *.mov *.mkv *.mts *.MTS);;All (*)"


def _column(parent, spacing=GAP):
    lay = QVBoxLayout(parent)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(spacing)
    return lay


class Video(QWidget):
    """The video node's settings: a picker, the chosen path and what cv2 says about it, and the
    decoder's one param, `output`, bgr as decoded, gray or luma, applied before its cache so a chain
    that wants gray frames never holds the colour ones; a smaller frame is a rescale node's."""
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
        lay.addWidget(form)
        self.button.clicked.connect(self._pick)
        self.output.currentTextChanged.connect(self._note_output)
        self.output.currentTextChanged.connect(lambda v: self.paramChanged.emit(VIDEO_OUTPUT, v))
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
        self.output.blockSignals(True)
        self.output.setCurrentText(video_output(doc))
        self.output.blockSignals(False)
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


class Pane(QWidget):
    """`tools` is the catalogue, name to module. `select(nid)` shows that node's surface, None
    shows nothing, and the x in a card's corner shows nothing and says `closed`; the node is
    untouched. `video` is the video node's widget, `widget(nid)` a tool node's settings widget.
    Its size hint is the shown card's height, so a host that stacks it under the canvas gives it only the room its content needs."""
    paramsChanged = Signal(str)   # this node's params in the document changed here
    videoPicked = Signal(str)
    cutting = Signal(str, bool)   # this node's settings widget began, or ended, writing the files its tool's cut_file answers with
    closed = Signal()             # the x in the shown card's corner; the pane already shows nothing

    def __init__(self, tools, parent=None):
        super().__init__(parent)
        self.tools = tools
        self.doc = None
        self.cards, self.widgets, self.notes = {}, {}, {}
        self.standings = {}   # tool node -> the line under its settings, see set_standing
        self.sizes = {}       # node -> the badge after its name that says what its result would take on disk, see set_size
        self.takes = {}       # node -> the badge after that one that says how long its work would take, see set_takes
        self.video = None
        self.current = None
        self._src, self._fps, self._of = None, None, {}
        self._cuts = set()    # nodes whose widget said a cut began and has not said it ended
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

    def _cut(self, nid, on):
        (self._cuts.add if on else self._cuts.discard)(nid)
        self.cutting.emit(nid, on)

    def _drop(self, nid):
        if nid in self._cuts:
            self._cut(nid, False)       # the widget goes with its cut and can no longer say it ended
        card = self.cards.pop(nid)
        self.widgets.pop(nid, None)
        self.notes.pop(nid, None)
        self.standings.pop(nid, None)
        self.sizes.pop(nid, None)
        self.takes.pop(nid, None)
        if self.video is not None and self.video.parent() is card:
            self.video = None
        self._lay.removeWidget(card)
        card.hide()
        card.setParent(None)
        card.deleteLater()

    def _build(self, node):
        card = Layer(1, node.id)
        self.sizes[node.id], self.takes[node.id] = Badge(), Badge()
        card.add_badge(self.sizes[node.id])
        card.add_badge(self.takes[node.id])
        close = CloseMark("Close these settings; the node stays")
        close.clicked.connect(self._close)
        card.tuck_corner(close)
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
                    w.set_source(self._of.get(node.id, self._src), self._fps)
                if hasattr(w, "cutting"):
                    w.cutting.connect(lambda on, nid=node.id: self._cut(nid, on))
                if is_selector(tool) or paths(tool):
                    self.notes[node.id] = readout()
                    card.add(self.notes[node.id])
        card.hide()
        self._lay.insertWidget(self._lay.count() - 1, card)
        self.cards[node.id] = card

    def _video_param(self, nid, name, value):
        """A video node knob moved: its param, saved and keyed like any node's."""
        self.doc.node(nid).params[name] = value
        self.paramsChanged.emit(nid)

    def _changed(self, nid):
        node = self.doc.node(nid)
        node.params = self.widgets[nid].params()   # the knobs are the whole set; a param a tool dropped goes with it
        self.paramsChanged.emit(nid)

    def select(self, nid):
        self.current = nid if nid in self.cards else None
        for i, card in self.cards.items():
            card.setVisible(i == self.current)
        self.updateGeometry()

    def _close(self):
        self.select(None)
        self.closed.emit()

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

    def set_size(self, nid, text, unit="", tip=""):
        """The badge after `nid`'s name that says what its result would take on disk, from the
        window: `text` in the colour theme.HELD has for `unit`, one of held.UNITS, and `tip` the
        sentence under the pointer; a `text` of "" hides it."""
        badge = self.sizes.get(nid)
        if badge is not None:
            badge.say(text, HELD.get(unit), tip)

    def set_takes(self, nid, text, tip=""):
        """The badge after `nid`'s size that says how long its work would take, from the window;
        "" hides it."""
        badge = self.takes.get(nid)
        if badge is not None:
            badge.say(text, tip=tip)

    def set_source(self, path, fps, of=None):
        """The footage every settings widget with a `set_source` writes from or beside: `path`, the
        open video, or for a node of `of`, node to path, the file its inputs are frames of; None
        when nothing is loaded. A widget is told only when its footage or the fps changed."""
        was, self._src, self._fps, self._of = (self._src, self._fps, self._of), path, fps, dict(of or {})
        for nid, w in self.widgets.items():
            if hasattr(w, "set_source") and (was[2].get(nid, was[0]), was[1]) != (self._of.get(nid, path), fps):
                w.set_source(self._of.get(nid, path), fps)
