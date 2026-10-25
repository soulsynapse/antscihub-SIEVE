"""The window: frame left, the chain right, the transport across the bottom.

Everything sits on the ground gray. The chain is a column of layer-1 cards: Inputs, one per tool,
Outputs. The links between them run in a rail left of the cards: each leaves the card it reads
and turns into the card that reads it, and the strip above a card names what it receives. An
output nothing reads, and no file takes, ends in red. The frame and the column open at equal
widths and the column never shrinks below one form. The transport is one more surface. Every trace
in the column and the strip share one cursor: hovering any of them marks the row in all of them,
and a press in a trace moves the playhead as a press in the strip does. It opens with no video and
never prompts.

A tool's name is a link. It, or a double-click on the card, opens the tool alone: Input above it,
a picker of the stages it may read, or nothing; Output below, a checkbox per later stage that
expects what it hands out, checked if that stage reads it. The two are one wiring seen from both
ends: unchecking a reader leaves it with no input, and a stage with no input is computed as
nothing, red in the strip above it. The frame shows this stage, and keeps showing it after the
tool is closed: the card whose name is in the accent is the one on the frame. Only a wiring that
leaves that stage with no input moves the frame, to the last stage the video reaches. Knobs and
both pickers act at once; Save or a right-click anywhere keeps them, Cancel (or Escape) puts them
back.
`load(path)` builds the decoder, chain and worker, and replaces them on the next load. Until then
the transport is disabled and the frame is empty ground.
"""
import os
import traceback

import numpy as np
from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QImage, QKeySequence, QPainter, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QScrollArea,
                               QSizePolicy, QSplitter, QVBoxLayout, QWidget)

from . import theme
from .chain import VIDEO, Chain, Links

NOTHING = -2   # the Input picker's entry for no source; a combo box cannot find None
from .decoder import Decoder
from .sections import Inputs, Outputs
from .theme import GAP, PAD, RAIL, Form, Layer, Link, Rail, readout
from .timeline import Timeline
from .widgets import Trace
from .worker import Worker


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
    """The frame, the gate border, and each tool's draw() on top, in chain order."""

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


class Column(QWidget):
    """The chain's cards in a stack with a rail down the left. `show(cards)` lays out exactly those
    widgets, a Link strip between each pair; the rail is told its links separately."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(RAIL, 0, GAP, 0)   # the rail, and room for the scrollbar
        self.lay.setSpacing(0)
        self.rail = Rail(self)
        self.strips = []   # Link strips in order, one above each card but the first

    def show(self, cards):
        while self.lay.count():
            item = self.lay.takeAt(0)
            if item.widget() is not None:
                item.widget().hide()
        for strip in self.strips:
            strip.deleteLater()
        self.strips = []
        for i, card in enumerate(cards):
            if i:
                strip = Link()
                self.strips.append(strip)
                self.lay.addWidget(strip)
            self.lay.addWidget(card)
            card.show()
        self.lay.addStretch(1)
        self.rail.raise_()
        QTimer.singleShot(0, self.rail.update)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.rail.setGeometry(self.rect())

    def event(self, e):
        if e.type() == QEvent.Type.LayoutRequest:
            QTimer.singleShot(0, self.rail.update)   # after the children have their geometry
        return super().event(e)


class PlayerWindow(QMainWindow):
    def __init__(self, tools, title="SIEVE"):
        super().__init__()
        self.title = title
        self.setWindowTitle(title)
        self.setStyleSheet(theme.sheet())
        self.tools = list(tools)
        self.links = Links(self.tools)   # the wiring outlives every load
        self.decoder = self.chain = self.worker = None
        self.fps, self.count = 30.0, 0
        self.row, self.playing, self.window_ = 0, False, (0, 0)
        self._resume = False  # playback to restore when a playhead drag ends
        self.result, self.result_start = None, 0

        self.display = Display()
        self.display.drawers = [t for t in self.tools if hasattr(t, "draw")]
        self.timeline = Timeline()
        self.cards = []   # one layer-1 card per tool, in chain order: its index is its stage

        self.inputs = Inputs()
        self.inputs.sourceChanged.connect(self.load)

        # one section per tool; widgets are built once and outlive loads
        self.frame_widgets, self.series_widget = [], None
        frame_tools = [t for t in self.tools if getattr(t, "KIND", "frame") == "frame"]
        series_tools = [t for t in self.tools if getattr(t, "KIND", "frame") == "series"]
        for i, t in enumerate(frame_tools):
            w = self._card(t.NAME, t.settings())
            w.changed.connect(lambda i=i, w=w: self._frame_tool_changed(i, w))
            self.frame_widgets.append(w)
        if series_tools:
            w = self.series_widget = self._card(series_tools[0].NAME, series_tools[0].settings())
            w.changed.connect(lambda w=w: self._series_tool_changed(w))

        # outputs: the chain's last tool exports, if it can
        self.export_tool = self.tools[-1] if self.tools else None
        self.export_widget = self.frame_widgets[-1] if self.export_tool in frame_tools else self.series_widget
        self.outputs = Outputs(self.export_tool)
        if self.export_widget is not None:
            self.export_widget.changed.connect(lambda: self.outputs.set_params(self.export_widget.params()))
            self.outputs.set_params(self.export_widget.params())

        ends = {n: Layer(1, n, edge=theme.EDGE_TINTS[n]) for n in ("inputs", "outputs")}
        ends["inputs"].add(self.inputs)
        ends["outputs"].add(self.outputs)
        self.ends = ends
        self.column = column = Column()
        self.focused = None   # a stage number while a tool is open alone
        self._laid = None     # the mode the column is laid out for (see _populate)
        self._kept = None     # (params, source) to put back on Cancel
        self.source_card, self.source_pick = self._source_card()
        self.sink_card, self.sink_line = self._sink_card()
        self._populate()
        scroll = QScrollArea()
        scroll.setWidget(column)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(theme.WIDE_W + 2 * PAD + GAP)   # one form and the scrollbar's gutter
        split = QSplitter(Qt.Horizontal)
        split.setHandleWidth(GAP)
        split.addWidget(self.display)
        split.addWidget(scroll)
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

        st, ct = self.timeline.strip, self.timeline.controls
        st.pressed.connect(self._scrub_begin)
        st.dragged.connect(lambda r: self.seek(r, commit=False))
        st.released.connect(self._scrub_end)
        st.windowChanged.connect(self.set_window)
        st.windowPlaced.connect(lambda s, n: self.set_window(s, n, playhead=s))
        st.hovered.connect(self._hover)
        self.traces = column.findChildren(Trace)
        for tr in self.traces:
            tr.pressed.connect(self._scrub_begin)
            tr.dragged.connect(lambda r: self.seek(r, commit=False))
            tr.released.connect(self._scrub_end)
            tr.hovered.connect(self._hover)
        ct.playToggled.connect(self.toggle_play)
        ct.step.connect(lambda d: self.seek(self.row + d, commit=True))
        ct.windowEdited.connect(lambda s, n: self.set_window(round(s * self.fps), round(n * self.fps)))
        QShortcut(QKeySequence(Qt.Key_Space), self, self.toggle_play)
        QShortcut(QKeySequence(Qt.Key_Left), self, lambda: self.seek(self.row - 1, commit=True))
        QShortcut(QKeySequence(Qt.Key_Right), self, lambda: self.seek(self.row + 1, commit=True))
        QShortcut(QKeySequence(Qt.Key_Escape), self, self.cancel)
        QApplication.instance().installEventFilter(self)   # a right-click anywhere leaves the open tool

        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self._tick)
        self.timeline.setEnabled(False)
        ct.progress.setText("no video")

    def _card(self, name, w):
        """A named layer-1 card holding `w`, queued for the column; returns `w`. The card's number
        in self.cards is its stage: frame stages in order, then the series stage."""
        card = Layer(1, name, link=True)
        card.add(w)
        stage = len(self.cards)
        card.activated.connect(lambda: self.focus(stage))
        buttons = QWidget()
        h = QHBoxLayout(buttons)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(GAP)
        cancel, save = QPushButton("Cancel"), QPushButton("Save")
        cancel.clicked.connect(self.cancel)
        save.clicked.connect(self.save)
        for b in (cancel, save):
            b.setFixedHeight(theme.ROW_H)
            b.setFixedWidth(theme.CONTROL_W // 2 - GAP // 2)
            h.addWidget(b)
        h.addStretch(1)
        card.add(buttons)
        card.buttons = buttons
        buttons.hide()
        self.cards.append(card)
        return w

    # -- the column: pipeline or one tool ---------------------------------
    def _name(self, stage):
        return "video" if stage == VIDEO else self.links.tool(stage).NAME

    def _exports(self, stage):
        """Whether Outputs writes this stage to a file."""
        return (self.outputs.tool is not None and stage == self._sink())

    def _sink(self):
        """The stage Outputs belongs to: the series stage, else the last frame stage, else the video."""
        if self.links.series is not None:
            return self.links.series
        return len(self.links.frame_tools) - 1

    def _dead(self, stage):
        """A frame stage nothing reads and no file takes. The series stage's output is its trace;
        a stage with no input hands out nothing, so there is nothing to be unread."""
        return (stage != self.links.series and self.links.produces(stage) is not None
                and not self.links.consumers(stage) and not self._exports(stage))

    def _receives(self, stage):
        src = self.links.source(stage)
        if src is None:
            return "no input"
        return f"{self.links.produces(src) or 'nothing'} from {self._name(src)}"

    def _populate(self):
        """Lay the column out for the mode, every card or Input, one tool, Output, then refresh.
        Only a change of mode rebuilds the column; a rewire within one refreshes it in place."""
        if self.focused is None:
            for card in self.cards:
                card.set_link(True)
                card.buttons.hide()
            self.column.show([self.ends["inputs"], *self.cards, self.ends["outputs"]])
        else:
            stage, card = self.focused, self.cards[self.focused]
            card.set_link(False)
            card.set_shown(False)
            card.buttons.show()
            self._fill_source_pick(stage)
            self._fill_sink(stage)
            self.column.show([self.source_card, card, self.sink_card])
        self._laid = self.focused
        self._refresh()

    def _refresh(self):
        """The strips' texts, the pickers' states and the rail follow the wiring."""
        links, dead = [], []
        if self.focused is None:
            at = {VIDEO: self.ends["inputs"], **{i: c for i, c in enumerate(self.cards)}}
            for stage, card in at.items():
                card.set_shown(stage == self.links.shown)   # the accent names what the frame is
            for stage, card in enumerate(self.cards):
                src = self.links.source(stage)
                self.column.strips[stage].set_text(self._receives(stage), bad=src is None)
                if src is not None:
                    links.append((at[src], card))
            sink = self._sink()
            self.column.strips[-1].set_text(f"{self.links.produces(sink) or 'nothing'} from {self._name(sink)}")
            links.append((at[sink], self.ends["outputs"]))
            for stage in range(len(self.cards)):
                if self._dead(stage):
                    dead.append(at[stage])
                    strip = self.column.strips[stage + 1] if stage + 1 < len(self.column.strips) else None
                    if strip is not None:
                        strip.set_text(strip.text, f"{self.links.produces(stage)} unread", bad=strip.bad)
        else:
            stage, card = self.focused, self.cards[self.focused]
            pick = self.source_pick
            pick.blockSignals(True)
            src = self.links.source(stage)
            pick.setCurrentIndex(pick.findData(NOTHING if src is None else src))
            pick.blockSignals(False)
            for reader, (_, box) in zip(self.links.readers(stage), self.sink_card.form.rows):
                box.blockSignals(True)
                box.setChecked(self.links.source(reader) == stage)
                box.blockSignals(False)
            self.column.strips[0].set_text(self._receives(stage), bad=src is None)
            if src is not None:
                links.append((self.source_card, card))
            out = self.links.produces(stage) or "nothing"
            readers = [self._name(c) for c in self.links.consumers(stage)]
            if self._exports(stage):
                readers.append("Outputs")
            if stage == self.links.series:
                text, red = f"{out}: the trace", False
            elif readers:
                text, red = f"{out} read by {', '.join(readers)}", False
            else:
                text, red = f"{out}: nothing reads this and no file takes it", True
            self.column.strips[1].set_text(f"{out} from {self._name(stage)}", "" if not red else f"{out} unread")
            self.sink_line.setText(text)
            self.sink_line.setStyleSheet(f"color: {theme.RED.name()};" if red else "")
            links.append((card, self.sink_card))
            if red:
                dead.append(card)
        self.column.rail.set_links(links, dead)

    def _source_card(self):
        card = Layer(1, "input", edge=theme.EDGE_TINTS["inputs"])
        pick = QComboBox()
        pick.currentIndexChanged.connect(self._source_picked)
        form = Form([("from", pick)])
        card.add(form)
        return card, pick

    def _sink_card(self):
        card = Layer(1, "output", edge=theme.EDGE_TINTS["outputs"])
        line = readout()
        card.add(line)
        card.form = None   # one checkbox per stage that may read this one; rebuilt per focus
        return card, line

    def _fill_sink(self, stage):
        """The Output card: a checkbox per later stage that expects this stage's product, checked
        if it reads it now, and the line saying what reads it."""
        card = self.sink_card
        if card.form is not None:
            card.body.removeWidget(card.form)
            card.form.hide()
            card.form.setParent(None)
            card.form.deleteLater()
        card.form = Form()
        card.body.insertWidget(card.body.indexOf(self.sink_line), card.form)
        for reader in self.links.readers(stage):
            box = QCheckBox()
            box.setChecked(self.links.source(reader) == stage)
            box.toggled.connect(lambda on, r=reader: self._reader_toggled(r, on))
            card.form.add_row(self._name(reader), box)

    def _reader_toggled(self, reader, on):
        stage = self.focused
        if stage is None:
            return
        try:
            if on:
                self.links.set_source(reader, stage)
            else:
                self.links.detach(reader, stage)
        except ValueError as e:
            self._refresh()
            self.sink_line.setText(str(e))
            self.sink_line.setStyleSheet(f"color: {theme.RED.name()};")
            return
        self._rewired()

    def _fill_source_pick(self, stage):
        pick = self.source_pick
        pick.blockSignals(True)
        pick.clear()
        pick.addItem("nothing", NOTHING)
        for j in self.links.compatible(stage):
            pick.addItem(f"{self._name(j)} · {self.links.produces(j)}", j)
        src = self.links.source(stage)
        pick.setCurrentIndex(pick.findData(NOTHING if src is None else src))
        pick.blockSignals(False)

    def _source_picked(self, index):
        if self.focused is None or index < 0:
            return
        src = self.source_pick.itemData(index)
        src = None if src == NOTHING else src
        try:
            self.links.set_source(self.focused, src)
        except ValueError as e:
            self._refresh()
            self.sink_line.setText(str(e))
            self.sink_line.setStyleSheet(f"color: {theme.RED.name()};")
            return
        self._rewired()

    def _rewired(self):
        """The links or the shown stage changed: keys, the walk and the frame follow. An open tool
        is shown even with no input; in the pipeline view an unfed shown stage gives way to the
        last one the video reaches."""
        self._settle_shown()
        if self._laid == self.focused:
            self._refresh()
        else:
            self._populate()
        if self.chain is None:
            return
        self.chain.relink()
        self.worker.invalidate()
        if not self.links.fed(self.links.shown):
            self.display.clear(f"{self._name(self.focused)}: no input")
        self.goto(self.row, commit=True)

    def _settle_shown(self):
        """In the pipeline view an unfed shown stage gives way to the last one the video reaches."""
        if self.focused is None and not self.links.fed(self.links.shown):
            self.links.shown = self.links.last_fed()

    def focus(self, stage):
        """Open one tool alone; the frame shows its stage from now on (the series card: what it
        stacks)."""
        if self.focused is not None:
            self.save()
        w = self.frame_widgets[stage] if stage < len(self.frame_widgets) else self.series_widget
        self._kept = (dict(w.params()), list(self.links.sources), self.links.series_source)
        self.focused = stage
        self.links.shown = self.links.series_source if stage == self.links.series else stage
        self._rewired()

    def eventFilter(self, obj, e):
        if (self.focused is not None and e.type() == QEvent.Type.MouseButtonPress
                and e.button() == Qt.MouseButton.RightButton and isinstance(obj, QWidget) and obj.window() is self):
            self.save()
            return True
        return super().eventFilter(obj, e)

    def save(self):
        if self.focused is None:
            return
        self.focused, self._kept = None, None
        self._rewired()

    def cancel(self):
        if self.focused is None:
            return
        stage, (params, sources, series_source) = self.focused, self._kept
        w = self.frame_widgets[stage] if stage < len(self.frame_widgets) else self.series_widget
        self.links.sources, self.links.series_source = sources, series_source   # valid when kept
        if hasattr(w, "set_params"):
            w.set_params(params)
        self.save()

    # -- loading ---------------------------------------------------------
    def load(self, path):
        """Open `path`, replacing whatever was open. A file that won't open leaves the old one."""
        try:
            decoder = Decoder(path)
        except IOError as e:
            self.inputs.show_error(path, e)
            return
        self._unload()
        self.decoder = decoder
        self.chain = Chain(decoder, self.links)
        for i, w in enumerate(self.frame_widgets):
            self.chain.set_params(i, w.params())
        if self.series_widget is not None:
            self.chain.set_series_params(self.series_widget.params())
        self.worker = Worker(self.chain)
        self.fps, self.count = self.chain.fps, self.chain.count
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
        self._settle_shown()   # the wiring outlives the load; what it showed may no longer be fed
        self._refresh()
        if not self.links.fed(self.links.shown):
            self.display.clear(f"{self._name(self.focused)}: no input")
        self.set_window(0, min(self.count, round(10 * self.fps)))
        self.goto(0, commit=True)
        self.toggle_play()  # _unload left it paused
        self.inputs.show_source(path)
        self.outputs.set_source(path, self.fps)
        self.setWindowTitle(f"{self.title} — {os.path.basename(path)}")

    def _unload(self):
        if self.worker is None:
            return
        if self.playing:
            self.toggle_play()
        self.worker.stop()
        self.decoder.close()
        self.decoder = self.chain = self.worker = None
        self.result = None
        self.row, self.window_ = 0, (0, 0)
        self.display.clear()

    # -- state (every entry is a no-op until something is loaded) --------
    def set_window(self, start, length, playhead=None):
        """Move or resize the window. The playhead keeps its offset from the start, clamped inside,
        unless `playhead` names the row to show instead."""
        if self.chain is None:
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
        """Show `row`. A commit may ask the worker; a guess is served from the memo or not at all."""
        if self.chain is None:
            return
        self.row = row = max(0, min(self.count - 1, int(row)))
        frame = self.chain.peek(row)
        if frame is not None:
            self.display.set_frame(frame)
        elif commit:
            self.worker.request_row(row)
        self.timeline.strip.set_playhead(row)
        self.timeline.controls.set_readout(row)
        if self.series_widget is not None:
            self.series_widget.set_playhead(row)
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
        if self.chain is None:
            return
        s, n = self.window_
        self.goto(max(s, min(s + n - 1, int(row))), commit)

    def toggle_play(self):
        if self.chain is None:
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
    def _frame_tool_changed(self, i, w):
        if self.chain is None:
            return
        self.chain.set_params(i, w.params())
        self.worker.invalidate()
        self.goto(self.row, commit=True)

    def _series_tool_changed(self, w):
        if self.chain is None:
            return
        self.chain.set_series_params(w.params())
        self.worker.rerun_series()

    def _row_ready(self, row):
        if row == self.row and self.chain is not None:
            frame = self.chain.peek(row)
            if frame is not None:
                self.display.set_frame(frame)

    def _series_ready(self, result, start, fps):
        self.result, self.result_start = result, start
        if self.series_widget is not None:
            self.series_widget.show_result(result, start, fps)
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
