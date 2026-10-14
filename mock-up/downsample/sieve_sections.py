"""Mock-up of a SIEVE panel split into three sections: inputs over config over outputs.

The shell owns the sections and the Inputs and Outputs widgets; they look the same for every
tool. A tool offers `settings(parent)` as today, plus `output_name(src, params) -> path` and
`export_command(src, dst, params, fps) -> argv`; the shell runs that argv when Export is pressed.
`describe_output(src, params, fps) -> str` is optional and goes under the target name. The window
comes up with no video and never prompts: the decoder, chain and worker are built on the first
pick and replaced on the next.

This duplicates PlayerWindow's wiring rather than subclassing it, because PlayerWindow builds its
decoder before its panel; adopting this means splitting the two.
"""
import os

import cv2
from PySide6.QtCore import QProcess, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QKeySequence, QPainter, QShortcut
from PySide6.QtWidgets import (QFileDialog, QFrame, QLabel, QMainWindow, QPushButton, QScrollArea,
                               QSplitter, QVBoxLayout, QWidget)

from sieve_player import Chain, Decoder, Worker
from sieve_player.timeline import Timeline
from sieve_player.window import Display

# section name -> (background, label ink, label corner). Inputs is a cool grey, outputs a warm one,
# a luminance step apart so they still separate in monochrome. Config is white and carries no
# label (None ink). The word sits top-right of its section; this is the rule for the main app too.
SECTIONS = {
    "inputs": ("#E2E6EC", "#C4CBD5", Qt.AlignRight | Qt.AlignTop),
    "config": ("#FFFFFF", None, None),
    "outputs": ("#F3EEE6", "#D9D0C2", Qt.AlignRight | Qt.AlignTop),
}
# The watermark: one style for every labelled section, drawn behind the content. The corner comes
# from SECTIONS; `vertical` turns the word to read bottom-to-top; `outline` strokes instead of fills.
WATERMARK = dict(
    families=["Arial Black", "Arial", "Helvetica", "DejaVu Sans"],  # Windows and macOS ship the first
    px=34, squeeze=-0.12, vertical=False, outline=False, inset=(8, 4),
)
VIDEO_FILTER = "Video (*.mp4 *.MP4 *.avi *.mov *.mkv);;All (*)"


def probe(src):
    """(width, height, fps, count) via cv2."""
    cap = cv2.VideoCapture(str(src))
    try:
        return (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                cap.get(cv2.CAP_PROP_FPS) or 30.0, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
    finally:
        cap.release()


class Section(QFrame):
    """A tinted frame with its name drawn behind the content as a watermark (see WATERMARK)."""

    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name
        bg, ink, self.corner = SECTIONS[name]
        self.bg, self.ink = QColor(bg), (QColor(ink) if ink else None)
        self.setAutoFillBackground(False)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(12, 10, 12, 10)

    def add(self, w):
        self.lay.addWidget(w)

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), self.bg)
        if self.ink is not None:
            draw_watermark(p, self.rect(), self.name.upper(), self.ink, self.corner)


def draw_watermark(p, rect, text, ink, anchor, style=None):
    w = style or WATERMARK
    f = QFont()
    f.setFamilies(w["families"])
    f.setPixelSize(w["px"])
    f.setWeight(QFont.Black)
    f.setLetterSpacing(QFont.AbsoluteSpacing, w["squeeze"] * w["px"])
    p.setFont(f)
    dx, dy = w["inset"]
    r = rect.adjusted(dx, dy, -dx, -dy)
    p.save()
    if w["vertical"]:
        p.translate(r.left(), r.bottom())
        p.rotate(-90)
        r = QRect(0, 0, r.height(), r.width())
    if w["outline"]:
        from PySide6.QtGui import QPainterPath, QPen
        path = QPainterPath()
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(text)
        a = anchor
        x = r.left() if a & Qt.AlignLeft else r.right() - tw if a & Qt.AlignRight else r.center().x() - tw / 2
        y = r.top() + fm.ascent() if a & Qt.AlignTop else r.bottom() - fm.descent() if a & Qt.AlignBottom else r.center().y() + (fm.ascent() - fm.descent()) / 2
        path.addText(x, y, f, text)
        p.setPen(QPen(ink, 1.5))
        p.setBrush(Qt.NoBrush)
        p.setRenderHint(QPainter.Antialiasing)
        p.drawPath(path)
    else:
        p.setPen(ink)
        p.drawText(r, anchor, text)
    p.restore()


class Inputs(QWidget):
    """Standard inputs: a picker, the chosen path and what cv2 says about it."""
    sourceChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.button, self.path, self.info = QPushButton("Choose video…"), QLabel("no video"), QLabel("")
        for w in (self.path, self.info):
            w.setWordWrap(True)
        lay.addWidget(self.button, 0, Qt.AlignLeft)  # hugs its text; the corner stays clear for the label
        lay.addWidget(self.path)
        lay.addWidget(self.info)
        self.button.clicked.connect(self._pick)

    def _pick(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open video", "", VIDEO_FILTER)
        if path:
            self.show_source(path)
            self.sourceChanged.emit(path)

    def show_source(self, path):
        w, h, fps, n = probe(path)
        self.path.setText(path)
        self.info.setText(f"{w}×{h}   {fps:.2f} fps   {n} frames   {n / fps:.1f} s")


class Outputs(QWidget):
    """Standard outputs: the target the tool would write, an Export button that runs the tool's
    argv in a QProcess, and the process's last line of output."""

    def __init__(self, tool, parent=None):
        super().__init__(parent)
        self.tool = tool
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.target, self.button, self.status = QLabel(""), QPushButton("Export"), QLabel("")
        for w in (self.target, self.status):
            w.setWordWrap(True)
        lay.addWidget(self.target)
        lay.addWidget(self.button, 0, Qt.AlignLeft)
        lay.addWidget(self.status)
        self.button.clicked.connect(self._export)
        self.button.setEnabled(False)
        self.proc, self.src, self.fps, self.params = None, None, None, {}

    def set_source(self, path, fps):
        self.src, self.fps = path, fps
        self.button.setEnabled(True)
        self._describe()

    def set_params(self, params):
        self.params = dict(params)
        self._describe()

    def _describe(self):
        if self.src is None:
            self.target.setText("pick a video in Inputs")
            return
        text = os.path.basename(self.tool.output_name(self.src, self.params))
        describe = getattr(self.tool, "describe_output", None)
        if describe:
            text += "\n" + describe(self.src, self.params, self.fps)
        self.target.setText(text)

    def _export(self):
        if self.proc is not None:
            self.proc.kill()
            return
        dst = self.tool.output_name(self.src, self.params)
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
        self.status.setText(f"wrote {os.path.basename(dst)}" if code == 0 else f"exited {code}")


class SectionedWindow(QMainWindow):
    def __init__(self, tool, title="SIEVE"):
        super().__init__()
        self.setWindowTitle(title)
        self.tool = tool
        self.decoder = self.chain = self.worker = None
        self.fps, self.count = 30.0, 0
        self.row, self.playing, self.window_ = 0, False, (0, 0)
        self.result, self.result_start = None, 0

        self.display = Display()
        self.timeline = Timeline()
        self.sections = {n: Section(n) for n in SECTIONS}
        self.inputs_w, self.config_w, self.outputs_w = Inputs(), tool.settings(), Outputs(tool)
        self.sections["inputs"].add(self.inputs_w)
        self.sections["config"].add(self.config_w)
        self.sections["config"].lay.addStretch(1)  # config takes the column's slack; its rows hug the top
        self.sections["outputs"].add(self.outputs_w)
        self.inputs_w.sourceChanged.connect(self.load)
        self.config_w.changed.connect(self._config_changed)
        self.config_w.changed.connect(lambda: self.outputs_w.set_params(self.config_w.params()))
        self.outputs_w.set_params(self.config_w.params())

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
        st.pressed.connect(lambda r: self.goto(r, commit=True))
        st.dragged.connect(lambda r: self.goto(r, commit=False))
        st.released.connect(lambda r: self.goto(r, commit=True))
        st.windowChanged.connect(self.set_window)
        ct.playToggled.connect(self.toggle_play)
        ct.step.connect(lambda d: self.goto(self.row + d, commit=True))
        ct.windowEdited.connect(lambda s, n: self.set_window(round(s * self.fps), round(n * self.fps)))
        ct.windowEdited.connect(lambda s, n: self.goto(round(s * self.fps), commit=True))
        QShortcut(QKeySequence(Qt.Key_Space), self, self.toggle_play)
        QShortcut(QKeySequence(Qt.Key_Left), self, lambda: self.goto(self.row - 1, commit=True))
        QShortcut(QKeySequence(Qt.Key_Right), self, lambda: self.goto(self.row + 1, commit=True))
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self._tick)
        ct.progress.setText("no video")

    # -- loading ---------------------------------------------------------
    def load(self, path):
        self._unload()
        self.decoder = Decoder(path)
        self.chain = Chain(self.decoder, [self.tool])
        self.chain.set_params(0, self.config_w.params())
        self.worker = Worker(self.chain)
        self.fps, self.count = self.chain.fps, self.chain.count
        self.worker.rowReady.connect(self._row_ready)
        self.worker.seriesReady.connect(self._series_ready)
        self.worker.walked.connect(self.timeline.controls.set_progress)
        self.worker.failed.connect(lambda r: self.timeline.controls.progress.setText(f"tool raised at row {r}, see console"))
        self.timeline.strip.set_count(self.count, self.fps)
        self.timeline.controls.set_count(self.count, self.fps)
        self.timeline.controls.progress.setText("")
        self.worker.start()
        self.set_window(0, min(self.count, round(10 * self.fps)))
        self.goto(0, commit=True)
        self.outputs_w.set_source(path, self.fps)

    def _unload(self):
        if self.worker is None:
            return
        if self.playing:
            self.toggle_play()
        self.worker.stop()
        self.decoder.close()
        self.decoder = self.chain = self.worker = None
        self.result = None

    # -- state (as PlayerWindow, guarded for the empty state) ------------
    def set_window(self, start, length):
        if self.chain is None:
            return
        start = max(0, min(self.count - 1, int(start)))
        length = max(1, min(self.count - start, int(length)))
        self.window_ = (start, length)
        self.timeline.strip.set_window(start, length)
        self.timeline.controls.set_window(start, length)
        self.worker.set_window(start, length)
        if self.playing and not start <= self.row < start + length:
            self.goto(start, commit=True)

    def goto(self, row, commit):
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
        self._update_gate()

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

    def _config_changed(self):
        if self.chain is None:
            return
        self.chain.set_params(0, self.config_w.params())
        self.worker.invalidate()
        self.goto(self.row, commit=True)

    def _row_ready(self, row):
        if row == self.row and self.chain is not None:
            frame = self.chain.peek(row)
            if frame is not None:
                self.display.set_frame(frame)

    def _series_ready(self, result, start, fps):
        self.result, self.result_start = result, start
        self._update_gate()

    def _update_gate(self):
        gate = self.result.get("gate") if isinstance(self.result, dict) else None
        i = self.row - self.result_start
        self.display.set_gate(gate is not None and 0 <= i < len(gate) and bool(gate[i]))

    def showEvent(self, e):
        super().showEvent(e)
        if not getattr(self, "_split_done", False):
            self._split_done = True
            half = self.split.width() // 2
            self.split.setSizes([half, half])

    def closeEvent(self, e):
        self.timer.stop()
        self._unload()
        super().closeEvent(e)


def play(tool, path=None, title="SIEVE"):
    """Open the sectioned player on `tool`. A path preloads; none opens empty, with no prompt."""
    import sys

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    win = SectionedWindow(tool, title)
    win.showMaximized()
    if path:
        win.load(path)
        win.inputs_w.show_source(path)
        win.setWindowTitle(f"{title} — {os.path.basename(path)}")
    return app.exec()
