"""The right panel's three sections and the two SIEVE owns: Inputs over config over Outputs.

Inputs and Outputs look the same in every tool. Inputs is a picker plus what cv2 says about the
file; Outputs is the target a tool would write, an Export button that runs the tool's argv in a
QProcess, and the process's last line. A tool takes part in Outputs by defining
`output_name(src, params) -> path` and `export_command(src, dst, params, fps) -> argv`, and may add
`describe_output(src, params, fps) -> str` for the line under the target. Without them the
Outputs section says so and has no button.
"""
import os
import re
from functools import lru_cache

import cv2
from PySide6.QtCore import QProcess, QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QFileDialog, QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

# section name -> (background, label ink, label corner). Inputs is a cool grey, outputs a warm one,
# a luminance step apart so they still separate in monochrome. Config is white and carries no
# label (None ink). The word sits top-right of its section.
SECTIONS = {
    "inputs": ("#E2E6EC", "#C4CBD5", Qt.AlignRight | Qt.AlignTop),
    "config": ("#FFFFFF", None, None),
    "outputs": ("#F3EEE6", "#D9D0C2", Qt.AlignRight | Qt.AlignTop),
}
# The watermark: one style for every labelled section, drawn behind the content.
WATERMARK = dict(
    families=["Arial Black", "Arial", "Helvetica", "DejaVu Sans"],  # Windows and macOS ship the first
    px=34, squeeze=-0.12, inset=(8, 4),
)
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
            w = WATERMARK
            f = QFont()
            f.setFamilies(w["families"])
            f.setPixelSize(w["px"])
            f.setWeight(QFont.Black)
            f.setLetterSpacing(QFont.AbsoluteSpacing, w["squeeze"] * w["px"])
            p.setFont(f)
            p.setPen(self.ink)
            dx, dy = w["inset"]
            p.drawText(self.rect().adjusted(dx, dy, -dx, -dy), self.corner, self.name.upper())


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
            self.sourceChanged.emit(path)

    def show_source(self, path):
        w, h, fps, n = probe(path)
        self.path.setText(path)
        self.info.setText(f"{w}×{h}   {fps:.2f} fps   {n} frames   {n / fps:.1f} s")

    def show_error(self, path, err):
        self.path.setText(path)
        self.info.setText(f"could not open: {err}")


class Outputs(QWidget):
    """Standard outputs for the chain's exporting tool (None if it has none)."""

    def __init__(self, tool=None, parent=None):
        super().__init__(parent)
        self.tool = tool if tool is not None and hasattr(tool, "export_command") else None
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
        if self.tool is None:
            self.button.hide()
            self.target.setText("this chain has nothing to export")

    def set_source(self, path, fps):
        self.src, self.fps = path, fps
        self.button.setEnabled(self.tool is not None)
        self._describe()

    def set_params(self, params):
        self.params = dict(params)
        self._describe()

    def _target(self):
        return free_name(self.tool.output_name(self.src, self.params))

    def _describe(self):
        if self.tool is None:
            return
        if self.src is None:
            self.target.setText("pick a video in Inputs")
            return
        text = os.path.basename(self._target())
        describe = getattr(self.tool, "describe_output", None)
        if describe:
            text += "\n" + describe(self.src, self.params, self.fps)
        self.target.setText(text)

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
