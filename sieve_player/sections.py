"""The chain's two terminals, the parts of the column SIEVE owns: Inputs above the pipeline,
Outputs below it.

A terminal sits on the ground, not in the pipeline's surface, named in small caps top-right; the
accent arrow runs from Inputs into the first tool and out of the last into Outputs, so the two
read as the chain's source and sink. Both look the same in every tool. Inputs is a picker, the
chosen path, and one line of what cv2 says about the file; Outputs is the target a tool would
write, an Export button that runs the tool's argv in a QProcess, and the process's last line. A
tool takes part in Outputs by defining `output_name(src, params) -> path` and
`export_command(src, dst, params, fps) -> argv`, and may add `describe_output(src, params, fps)
-> str` for the line under the target. Without them the sink says so and has no button.
"""
import os
import re
from functools import lru_cache

import cv2
from PySide6.QtCore import QProcess, Qt, Signal
from PySide6.QtGui import QFontMetrics, QPainter
from PySide6.QtWidgets import QFileDialog, QPushButton, QVBoxLayout, QWidget

from . import theme
from .theme import GAP, PAD, Form, measured, qgray, readout

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


def _column(parent):
    lay = QVBoxLayout(parent)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(GAP)
    return lay


class Terminal(QWidget):
    """An end of the chain on the ground: the widget handed in, padded, with its name in small caps
    top-right and no surface of its own. Controls inside a terminal are layer-1 wells, since the
    ground is what they would otherwise vanish into (see theme.sheet)."""

    def __init__(self, name, w, parent=None):
        super().__init__(parent)
        self.name = name
        lay = QVBoxLayout(self)
        tag = QFontMetrics(theme.eyebrow_font()).horizontalAdvance(name.upper())
        lay.setContentsMargins(PAD, PAD, PAD + tag + GAP, PAD)   # the name's column stays clear
        lay.addWidget(w)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setFont(theme.eyebrow_font())
        p.setPen(qgray(theme.INK_2))
        p.drawText(self.rect().adjusted(PAD, PAD, -PAD, -PAD), Qt.AlignRight | Qt.AlignTop, self.name.upper())


class Inputs(QWidget):
    """Standard inputs: a picker, the chosen path and what cv2 says about it."""
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
        self.path.setText(path)
        self.info.setText(f"{w}×{h} · {fps:.2f} fps · {n} frames · {n / fps:.1f} s")

    def show_error(self, path, err):
        self.path.setText(path)
        self.info.setText(f"could not open: {err}")


class Outputs(QWidget):
    """Standard outputs for the chain's exporting tool (None if it has none)."""

    def __init__(self, tool=None, parent=None):
        super().__init__(parent)
        self.tool = tool if tool is not None and hasattr(tool, "export_command") else None
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
        if self.tool is None:
            self.form.set_row_visible(0, False)   # target
            self.form.set_row_visible(2, False)   # export
            self.detail.setText("this chain has nothing to export")

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
            self.target.setText("")
            self.detail.setText("pick a video in Inputs")
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
