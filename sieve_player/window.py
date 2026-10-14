"""The window: frame left, the sectioned panel right, timeline across the bottom.

It opens with no video and never prompts. `load(path)` builds the decoder, chain and worker, and
replaces them on the next load. Until then the transport is disabled and the frame is black.
"""
import os

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QImage, QKeySequence, QPainter, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (QFrame, QGroupBox, QMainWindow, QScrollArea, QSizePolicy, QSplitter,
                               QVBoxLayout, QWidget)

from .chain import Chain
from .decoder import Decoder
from .sections import Inputs, Outputs, Section
from .timeline import Timeline
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pix, self.gate = None, False
        self.setMinimumSize(160, 120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_frame(self, a):
        self._pix = QPixmap.fromImage(to_qimage(a))
        self.update()

    def clear(self):
        self._pix = None
        self.update()

    def set_gate(self, on):
        if on != self.gate:
            self.gate = on
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), Qt.black)
        if self._pix is None:
            return
        pix = self._pix.scaled(self.size(), Qt.KeepAspectRatio, Qt.FastTransformation)
        x, y = (self.width() - pix.width()) // 2, (self.height() - pix.height()) // 2
        p.drawPixmap(x, y, pix)
        if self.gate:
            p.setPen(QPen(QColor(230, 60, 60), 6))
            p.drawRect(x + 3, y + 3, pix.width() - 6, pix.height() - 6)


class PlayerWindow(QMainWindow):
    def __init__(self, tools, title="SIEVE"):
        super().__init__()
        self.title = title
        self.setWindowTitle(title)
        self.tools = list(tools)
        self.decoder = self.chain = self.worker = None
        self.fps, self.count = 30.0, 0
        self.row, self.playing, self.window_ = 0, False, (0, 0)
        self.result, self.result_start = None, 0

        self.display = Display()
        self.timeline = Timeline()
        self.sections = {n: Section(n) for n in ("inputs", "config", "outputs")}

        self.inputs = Inputs()
        self.inputs.sourceChanged.connect(self.load)
        self.sections["inputs"].add(self.inputs)

        # config: one group box per tool, as before; widgets are built once and outlive loads
        self.frame_widgets, self.series_widget = [], None
        frame_tools = [t for t in self.tools if getattr(t, "KIND", "frame") == "frame"]
        series_tools = [t for t in self.tools if getattr(t, "KIND", "frame") == "series"]
        for i, t in enumerate(frame_tools):
            w = self._boxed(self.sections["config"], t)
            w.changed.connect(lambda i=i, w=w: self._frame_tool_changed(i, w))
            self.frame_widgets.append(w)
        if series_tools:
            w = self.series_widget = self._boxed(self.sections["config"], series_tools[0])
            w.changed.connect(lambda w=w: self._series_tool_changed(w))
        self.sections["config"].lay.addStretch(1)

        # outputs: the chain's last tool exports, if it can
        self.export_tool = self.tools[-1] if self.tools else None
        self.export_widget = self.frame_widgets[-1] if self.export_tool in frame_tools else self.series_widget
        self.outputs = Outputs(self.export_tool)
        self.sections["outputs"].add(self.outputs)
        if self.export_widget is not None:
            self.export_widget.changed.connect(lambda: self.outputs.set_params(self.export_widget.params()))
            self.outputs.set_params(self.export_widget.params())

        column = QWidget()
        cl = QVBoxLayout(column)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        for name, s in self.sections.items():
            cl.addWidget(s, 1 if name == "config" else 0)  # inputs and outputs hug their content
        scroll = QScrollArea()
        scroll.setWidget(column)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        split = QSplitter(Qt.Horizontal)
        split.addWidget(self.display)
        split.addWidget(scroll)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 1)
        self.split = split
        central = QWidget()
        lay = QVBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(split, 1)
        lay.addWidget(self.timeline, 0)
        self.setCentralWidget(central)

        st, ct = self.timeline.strip, self.timeline.controls
        st.pressed.connect(lambda r: self.seek(r, commit=True))
        st.dragged.connect(lambda r: self.seek(r, commit=False))
        st.released.connect(lambda r: self.seek(r, commit=True))
        st.windowChanged.connect(self.set_window)
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

    @staticmethod
    def _boxed(section, tool):
        w = tool.settings()
        box = QGroupBox(tool.NAME)
        QVBoxLayout(box).addWidget(w)
        section.add(box)
        return w

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
        self.chain = Chain(decoder, self.tools)
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
    def set_window(self, start, length):
        """Move or resize the window. The playhead keeps its offset from the start, clamped inside."""
        if self.chain is None:
            return
        start = max(0, min(self.count - 1, int(start)))
        length = max(1, min(self.count - start, int(length)))
        offset = max(0, min(length - 1, self.row - self.window_[0]))
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

    def _update_gate(self):
        gate = self.result.get("gate") if isinstance(self.result, dict) else None
        i = self.row - self.result_start
        self.display.set_gate(gate is not None and 0 <= i < len(gate) and bool(gate[i]))

    def showEvent(self, e):
        super().showEvent(e)
        if not getattr(self, "_split_done", False):  # sizes set before show get reshaped by hints
            self._split_done = True
            half = self.split.width() // 2
            self.split.setSizes([half, half])

    def closeEvent(self, e):
        self.timer.stop()
        self._unload()
        super().closeEvent(e)
