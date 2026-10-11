"""The window: frame left, tool settings right, timeline across the bottom."""
import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QImage, QKeySequence, QPainter, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (QGroupBox, QMainWindow, QScrollArea, QSizePolicy, QSplitter,
                               QVBoxLayout, QWidget)

from .timeline import Timeline


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
    def __init__(self, decoder, chain, worker, title="SIEVE"):
        super().__init__()
        self.setWindowTitle(title)
        self.decoder, self.chain, self.worker = decoder, chain, worker
        self.fps, self.count = chain.fps, chain.count
        self.row, self.playing, self.window_ = 0, False, (0, 0)
        self.result, self.result_start = None, 0

        self.display = Display()
        self.timeline = Timeline()
        panel, pl = QWidget(), None
        pl = QVBoxLayout(panel)
        self.series_widget = None
        for i, t in enumerate(chain.frame_tools):
            w = self._boxed(pl, t)
            w.changed.connect(lambda i=i, w=w: self._frame_tool_changed(i, w))
            chain.set_params(i, w.params())
        if chain.series_tool:
            w = self.series_widget = self._boxed(pl, chain.series_tool)
            w.changed.connect(lambda w=w: self._series_tool_changed(w))
            chain.set_series_params(w.params())
        pl.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidget(panel)
        scroll.setWidgetResizable(True)
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
        st.set_count(self.count, self.fps)
        ct.set_count(self.count, self.fps)
        st.pressed.connect(lambda r: self.goto(r, commit=True))
        st.dragged.connect(lambda r: self.goto(r, commit=False))
        st.released.connect(lambda r: self.goto(r, commit=True))
        st.windowChanged.connect(self.set_window)
        ct.playToggled.connect(self.toggle_play)
        ct.step.connect(lambda d: self.goto(self.row + d, commit=True))
        ct.windowEdited.connect(lambda s, n: self.set_window(round(s * self.fps), round(n * self.fps)))
        ct.windowEdited.connect(lambda s, n: self.goto(round(s * self.fps), commit=True))
        worker.rowReady.connect(self._row_ready)
        worker.seriesReady.connect(self._series_ready)
        worker.walked.connect(ct.set_progress)
        worker.failed.connect(lambda r: ct.progress.setText(f"tool raised at row {r}, see console"))
        QShortcut(QKeySequence(Qt.Key_Space), self, self.toggle_play)
        QShortcut(QKeySequence(Qt.Key_Left), self, lambda: self.goto(self.row - 1, commit=True))
        QShortcut(QKeySequence(Qt.Key_Right), self, lambda: self.goto(self.row + 1, commit=True))

        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self._tick)
        self.set_window(0, min(self.count, round(10 * self.fps)))
        self.goto(0, commit=True)

    @staticmethod
    def _boxed(layout, tool):
        w = tool.settings()
        box = QGroupBox(tool.NAME)
        QVBoxLayout(box).addWidget(w)
        layout.addWidget(box)
        return w

    # -- state ----------------------------------------------------------
    def set_window(self, start, length):
        start = max(0, min(self.count - 1, int(start)))
        length = max(1, min(self.count - start, int(length)))
        self.window_ = (start, length)
        self.timeline.strip.set_window(start, length)
        self.timeline.controls.set_window(start, length)
        self.worker.set_window(start, length)
        if self.playing and not start <= self.row < start + length:
            self.goto(start, commit=True)

    def goto(self, row, commit):
        """Show `row`. A commit may ask the worker; a guess is served from the memo or not at all."""
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

    def toggle_play(self):
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
        self.chain.set_params(i, w.params())
        self.worker.invalidate()
        self.goto(self.row, commit=True)

    def _series_tool_changed(self, w):
        self.chain.set_series_params(w.params())
        self.worker.rerun_series()

    def _row_ready(self, row):
        if row == self.row:
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
        self.worker.stop()
        self.decoder.close()
        super().closeEvent(e)
