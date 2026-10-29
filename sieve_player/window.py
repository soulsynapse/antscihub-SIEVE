"""The window: the frame left, the canvas over the parameter pane right, the transport across the
bottom.

The document is the one source of truth for the graph. The canvas and the pane read and write it
and say what changed; the window carries the change to the runtime, which is built on every load
of a video and re-synced on every change. The frame shows the node that carries the display flag;
a flagged node the video does not reach blanks the frame and says why, and no flag is empty
ground. The transport, the decoder, the worker and the memo are as they were: the display reads
the memo and never waits on the decoder. It opens with no video and never prompts.
"""
import os
import traceback

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QKeySequence, QPainter, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import QFileDialog, QMainWindow, QSizePolicy, QVBoxLayout, QWidget

from . import dev, document, theme
from .canvas import Canvas
from .decoder import Decoder
from .graph import Graph
from .pane import Pane
from .registry import Entry
from .theme import GAP, PAD
from .timeline import Timeline
from .widgets import Trace
from .worker import Worker

DOCUMENT_FILTER = "SIEVE document (*.json);;All (*)"


def _same(a, b):
    """Whether two paths name one file, as far as their text says."""
    return os.path.normcase(os.path.abspath(str(a))) == os.path.normcase(os.path.abspath(str(b)))


def to_qimage(a):
    a = np.asarray(a)
    if a.dtype == bool:
        a = a.astype(np.uint8) * 255
    elif a.dtype != np.uint8:
        top = float(a.max()) if a.size else 1.0
        a = np.clip(a * (255.0 if top <= 1.0 else 1.0), 0, 255).astype(np.uint8)
    a = np.ascontiguousarray(a)
    if a.ndim == 2:
        fmt = QImage.Format_Grayscale8
    elif a.ndim == 3 and a.shape[2] == 3:
        fmt = QImage.Format_BGR888
    else:
        raise ValueError(f"cannot display array of shape {a.shape}")
    return QImage(a.data, a.shape[1], a.shape[0], a.strides[0], fmt).copy()


class Display(QWidget):
    """The frame, the gate border, and each tool's draw() on top, in node order."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pix, self.gate, self.reason = None, False, ""
        self.drawers, self.row, self.result, self.start = [], 0, None, 0
        self.setMinimumSize(160, 120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_state(self, row, result, start):
        self.row, self.result, self.start = row, result, start
        self.update()

    def set_frame(self, a):
        self._pix, self.reason = QPixmap.fromImage(to_qimage(a)), ""
        self.update()

    def clear(self, reason=""):
        """No frame; `reason` is the one line that says why, so an empty frame never reads as a stall."""
        self._pix, self.reason = None, reason
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
        pix = self._pix.scaled(self.size(), Qt.KeepAspectRatio, Qt.FastTransformation)
        x, y = (self.width() - pix.width()) // 2, (self.height() - pix.height()) // 2
        p.drawPixmap(x, y, pix)
        if self.gate:
            p.setPen(QPen(theme.AMBER, 4))
            p.drawRect(x + 2, y + 2, pix.width() - 4, pix.height() - 4)
        if not self.drawers:
            return
        p.save()
        p.translate(x, y)
        p.scale(pix.width() / self._pix.width(), pix.height() / self._pix.height())
        for tool in self.drawers:
            try:
                tool.draw(p, self.row, self.result, self.start)
            except Exception:
                traceback.print_exc()
                self.drawers = [t for t in self.drawers if t is not tool]  # once, not every repaint
        p.restore()


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
    def __init__(self, source, title="SIEVE", tools=()):
        """`source` is a list of tools, which become the document, or the path of a saved document.
        The catalogue the Tab menu offers and the document's names index is `tools`, plus the list
        when `source` is one. Either list holds tool modules or registry entries; see `catalogue`."""
        super().__init__()
        self.title = title
        self.setStyleSheet(theme.sheet())
        from_file = isinstance(source, (str, os.PathLike))
        modules, self.tools, broken = catalogue(list(tools) if from_file else [*source, *tools])
        if not from_file:
            modules = catalogue(source)[0]
        self.doc = None
        self.decoder = self.graph = self.worker = None
        self.fps, self.count = 30.0, 0
        self.row, self.playing, self.window_ = 0, False, (0, 0)
        self._resume = False  # playback to restore when a playhead drag ends
        self.result, self.result_start = None, 0
        self._taken = {}       # (node id, path input) -> the file last handed to its loader
        self._driven = {}      # (node id, path input) -> (the keys its loader set, the selector's id)
        self.traces = []
        self._hooked = set()   # ids of traces already wired to the strip's cursor

        self.display = Display()
        self.canvas = Canvas(self.tools, broken)
        self.pane = Pane(self.tools)
        self.timeline = Timeline()
        # an empty selection leaves the pane on its last node, so a click on empty canvas never blanks it
        self.canvas.selectionChanged.connect(lambda ids: ids and self.pane.select(ids[-1]))
        self.canvas.changed.connect(self.sync)
        self.pane.paramsChanged.connect(self._params_changed)
        self.pane.videoPicked.connect(self.load)

        right = Column()
        right.lay.addWidget(self.canvas, 1)
        right.lay.addWidget(self.pane, 0)
        right.capped = self.pane
        split = theme.Splitter(Qt.Horizontal)
        split.setHandleWidth(GAP)
        split.addWidget(self.display)
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
        doc.resolve(self.tools)
        self.canvas.set_document(doc)
        self.pane.set_document(doc)
        self._hook_traces()
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
        document.save(self.doc, path)
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

    def _hook_traces(self):
        """Every trace in the pane shares the strip's playhead and cursor; a new one is wired once."""
        self.traces = self.pane.findChildren(Trace)
        for tr in self.traces:
            if id(tr) in self._hooked:
                continue
            self._hooked.add(id(tr))
            tr.pressed.connect(self._scrub_begin)
            tr.dragged.connect(lambda r: self.seek(r, commit=False))
            tr.released.connect(self._scrub_end)
            tr.hovered.connect(self._hover)

    # -- the graph changed ------------------------------------------------
    def sync(self):
        """The document's wiring, nodes or flag changed: the pane, the runtime, the canvas and the
        frame follow, and the video, if a selector now picks a different file."""
        self.pane.sync()
        self._hook_traces()
        self._pick_video()
        self.display.drawers = [self.tools[n.tool] for n in self.doc.nodes
                                if n.tool in self.tools and hasattr(self.tools[n.tool], "draw")]
        self.canvas.update()
        if self.graph is None:
            return
        self.graph.sync()
        self.worker.invalidate()
        self.goto(self.row, commit=True)

    def _params_changed(self, nid):
        if document.is_selector(self.tools.get(self.doc.node(nid).tool)):
            self._pick_video()
            return
        if self.graph is None:
            return
        self.graph.sync()
        if nid == self.graph.series:
            self.worker.rerun_series()
        else:
            self.worker.invalidate()
            self.goto(self.row, commit=True)

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
        tool's loader into the node's params, once per file; a miss is said on the node."""
        for n in self.doc.nodes:
            tool = self.tools.get(n.tool)
            loaders = document.paths(tool)
            if not loaders:
                continue
            notes, errors = [], []
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
                notes.append(f"{name}: {os.path.basename(path)}")
                if self._taken.get((n.id, name)) == path:
                    continue
                try:
                    params = loader(path)
                except Exception as e:  # the file is the user's; say what was wrong with it
                    errors.append(f"{name}: {type(e).__name__}: {e}")
                    continue
                self._taken[(n.id, name)] = path
                self._driven[(n.id, name)] = (tuple(params), sel.id)
                n.params = {**n.params, **params}
                if w is not None:
                    w.set_params(n.params)       # moves the knobs; each move is a change the pane reports
                else:
                    self._params_changed(n.id)
            if w is not None and hasattr(w, "set_driven"):
                held = [(keys, by) for (nid, _), (keys, by) in self._driven.items() if nid == n.id]
                w.set_driven({k for keys, _ in held for k in keys}, held[0][1] if held else None)
            if errors:
                self.canvas.errors[n.id] = "; ".join(errors)
            else:
                self.canvas.errors.pop(n.id, None)
            self.pane.note(n.id, "; ".join(errors or notes))
        self.canvas.update()

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
        if self._open_video(path):
            self.doc.video = os.fspath(path)

    def _open_video(self, path):
        try:
            decoder = Decoder(path)
        except IOError as e:
            if self.pane.video is not None:
                self.pane.video.show_error(path, e)
            return False
        self._unload()
        self.decoder = decoder
        self.graph = Graph(self.doc, decoder, self.tools)
        self.worker = Worker(self.graph)
        self.fps, self.count = self.graph.fps, self.graph.count
        ct = self.timeline.controls
        self.worker.rowReady.connect(self._row_ready)
        self.worker.seriesReady.connect(self._series_ready)
        self.worker.walked.connect(ct.set_progress)
        self.worker.failed.connect(lambda r: ct.progress.setText(f"tool raised at row {r}, see console"))
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
            self.pane.video.show_source(path)
        self.pane.set_source(path, self.fps)
        self._retitle()
        return True

    def _unload(self):
        if self.worker is None:
            return
        if self.playing:
            self.toggle_play()
        self.worker.stop()
        self.decoder.close()
        self.decoder = self.graph = self.worker = None
        self.result = None
        self.row, self.window_ = 0, (0, 0)
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
            self.display.clear(f"{shown}: no input")
        else:
            frame = self.graph.peek(row)
            if frame is not None:
                self.display.set_frame(frame)
            elif commit:
                self.worker.request_row(row)
        self.timeline.strip.set_playhead(row)
        self.timeline.controls.set_readout(row)
        w = self.pane.widget(self.graph.series)
        if w is not None and hasattr(w, "set_playhead"):
            w.set_playhead(row)
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
    def _row_ready(self, row):
        if row == self.row and self.graph is not None:
            frame = self.graph.peek(row)
            if frame is not None:
                self.display.set_frame(frame)

    def _series_ready(self, result, start, fps):
        self.result, self.result_start = result, start
        w = self.pane.widget(self.graph.series) if self.graph is not None else None
        if w is not None and hasattr(w, "show_result"):
            w.show_result(result, start, fps)
        self._update_gate()

    def _hover(self, row):
        """One cursor for the strip and every trace; -1 clears it."""
        for tr in self.traces:
            tr.set_hover(row)
        self.timeline.strip.set_hover(row)

    def _update_gate(self):
        gate = self.result.get("gate") if isinstance(self.result, dict) else None
        i = self.row - self.result_start
        self.display.set_gate(gate is not None and 0 <= i < len(gate) and bool(gate[i]))
        self.display.set_state(self.row, self.result, self.result_start)

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
