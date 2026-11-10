"""The utility's window: the frame view, a row of view controls above it with the cursor's plate
position, the drawing modes as one exclusive row of buttons with the selected stamp group's link
beside them, the shapes' table on the right under the name stem and the buttons moving a row, and a
seek bar below with the frame's index and time. Its look is its own, since the player's theme is the
player's."""
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont, QFontDatabase, QKeySequence
from PySide6.QtWidgets import (QButtonGroup, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
                               QPushButton, QSlider, QVBoxLayout, QWidget)

from .editor import MODES, Editor
from .table import ShapeTable
from .video import Video
from .view import FrameView

FAMILIES = ["Inter", "Segoe UI Variable Text", "Segoe UI", "SF Pro Text", "Helvetica Neue", "Arial"]
STYLE = """
QWidget { background: rgb(31,31,31); color: rgb(200,200,200); }
QPushButton { background: rgb(49,49,49); border: 1px solid rgb(69,69,69); border-radius: 4px; padding: 3px 10px; }
QPushButton:hover { background: rgb(58,58,58); }
QPushButton:checked { background: rgb(70,62,40); border-color: rgb(255,200,80); }
QSlider::groove:horizontal { height: 4px; background: rgb(58,58,58); border-radius: 2px; }
QSlider::handle:horizontal { width: 12px; margin: -5px 0; background: rgb(140,140,140); border-radius: 6px; }
QLabel#readout { color: rgb(140,140,140); }
QLineEdit { background: rgb(24,24,24); border: 1px solid rgb(69,69,69); border-radius: 4px; padding: 2px 6px; }
QTableWidget { gridline-color: rgb(58,58,58); selection-background-color: rgb(70,62,40); }
QHeaderView::section { background: rgb(40,40,40); border: none; border-bottom: 1px solid rgb(69,69,69); padding: 3px 6px; }
"""
MODE_LABELS = {"select": "Select", "circle": "Circle", "circle3": "Circle by 3", "square": "Square",
               "rectangle": "Rectangle", "polygon": "Polygon", "stamp": "Stamp"}
VIDEO_FILTER = "Video (*.mp4 *.mov *.avi *.mts *.m2ts *.mkv *.MP4 *.MOV *.AVI *.MTS);;All files (*)"


def styled(app):
    have = set(QFontDatabase.families())
    font = QFont(next((f for f in FAMILIES if f in have), app.font().family()))
    font.setPixelSize(12)
    app.setFont(font)
    app.setStyleSheet(STYLE)


def clock(index, fps):
    t = index / fps
    return f"{int(t // 60)}:{t % 60:06.3f}"


class GeometryWindow(QMainWindow):
    """Opens `video` when given one; `ask_video` asks for one by a file dialog."""

    def __init__(self, video=None):
        super().__init__()
        self.video = None
        self.index = 0
        self.frame = None
        self.editor = Editor()
        self.view = FrameView(self.editor)
        self.table = ShapeTable(self.editor)
        self.table.setMinimumWidth(300)
        self.stem_field = QLineEdit()
        self.stem_field.setPlaceholderText("name stem: the kind")
        self.up_button, self.down_button = QPushButton("Up"), QPushButton("Down")
        self.editor.on_change = self._drawing_changed
        self.modes = QButtonGroup(self)
        self.mode_buttons = {}
        for m in MODES:
            b = QPushButton(MODE_LABELS[m])
            b.setCheckable(True)
            self.modes.addButton(b)
            self.mode_buttons[m] = b
            b.clicked.connect(lambda _=False, m=m: self.editor.set_mode(m))
        self.mode_buttons["select"].setChecked(True)
        self.link_button = QPushButton("Link group")
        self.link_button.setCheckable(True)
        self.link_button.setEnabled(False)
        self.fit_button, self.actual_button = QPushButton("Fit"), QPushButton("100%")
        self.open_button = QPushButton("Open video…")
        self.cursor_label, self.frame_label = QLabel(), QLabel()
        self.message = QLabel()
        for lab in (self.cursor_label, self.frame_label, self.message):
            lab.setObjectName("readout")
        self.seek_bar = QSlider(Qt.Orientation.Horizontal)
        self.seek_bar.setEnabled(False)

        top = QHBoxLayout()
        for w in (self.open_button, self.fit_button, self.actual_button):
            top.addWidget(w)
        top.addWidget(self.message, 1)
        top.addWidget(self.cursor_label)
        tools = QHBoxLayout()
        for b in self.mode_buttons.values():
            tools.addWidget(b)
        tools.addWidget(self.link_button)
        tools.addStretch(1)
        bottom = QHBoxLayout()
        bottom.addWidget(self.seek_bar, 1)
        bottom.addWidget(self.frame_label)
        body = QVBoxLayout()
        body.addLayout(top)
        body.addLayout(tools)
        middle = QHBoxLayout()
        middle.addWidget(self.view, 1)
        side = QVBoxLayout()
        above = QHBoxLayout()
        for w in (self.stem_field, self.up_button, self.down_button):
            above.addWidget(w)
        side.addLayout(above)
        side.addWidget(self.table, 1)
        middle.addLayout(side)
        body.addLayout(middle, 1)
        body.addLayout(bottom)
        central = QWidget()
        central.setLayout(body)
        self.setCentralWidget(central)
        self.setWindowTitle("Geometry")
        self.resize(1100, 760)

        self.open_button.clicked.connect(self.ask_video)
        self.fit_button.clicked.connect(self.view.fit)
        self.actual_button.clicked.connect(self.view.actual)
        self.seek_bar.valueChanged.connect(self.seek)
        self.view.moved.connect(self._show_cursor)
        self.table.refused.connect(self.message.setText)
        self.stem_field.textChanged.connect(lambda t: setattr(self.editor, "stem", t.strip()))
        self.link_button.clicked.connect(lambda on: self.editor.set_link(self.editor.current.group, on))
        self.up_button.clicked.connect(lambda: self.editor.move_shape(self.editor.selected, -1))
        self.down_button.clicked.connect(lambda: self.editor.move_shape(self.editor.selected, 1))
        delete = QAction(self)
        delete.setShortcut(QKeySequence.StandardKey.Delete)
        delete.triggered.connect(self.editor.delete_selected)
        self.addAction(delete)
        for keys, act in (("Ctrl+Z", self.editor.undo), ("Ctrl+Shift+Z", self.editor.redo)):
            a = QAction(self)
            a.setShortcut(QKeySequence(keys))
            a.triggered.connect(act)
            self.addAction(a)
        if video is not None:
            self.open_video(video)

    @property
    def plate(self):
        return self.video.plate if self.video is not None else None

    def ask_video(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open a video to draw over", "", VIDEO_FILTER)
        if path:
            self.open_video(path)

    def open_video(self, path):
        """True when the video opened; otherwise the message line says why and the open one stays."""
        try:
            video = Video(path)
        except IOError as e:
            self.message.setText(str(e))
            return False
        if self.video is not None:
            self.video.close()
        self.video = video
        self.editor.plate = video.plate
        self.message.setText("")
        self.setWindowTitle(f"Geometry — {os.path.basename(video.path)}  {video.plate[1]}×{video.plate[0]}")
        self.seek_bar.blockSignals(True)
        self.seek_bar.setRange(0, video.count - 1)
        self.seek_bar.setValue(0)
        self.seek_bar.blockSignals(False)
        self.seek_bar.setEnabled(True)
        self.seek(0)
        return True

    def seek(self, index):
        try:
            self.frame = self.video.read(index)
        except IOError as e:
            self.message.setText(str(e))
            return
        self.index = min(max(0, index), self.video.count - 1)
        self.view.show_frame(self.frame)
        self.frame_label.setText(f"{self.index} / {self.video.count - 1}   {clock(self.index, self.video.fps)}")
        if self.seek_bar.value() != self.index:
            self.seek_bar.setValue(self.index)

    def _drawing_changed(self):
        self.mode_buttons[self.editor.mode].setChecked(True)
        s = self.editor.current
        self.link_button.setEnabled(s is not None and bool(s.group))
        self.link_button.setChecked(s is not None and self.editor.linked(s))
        self.view.viewport().update()
        self.table.refresh()

    def _show_cursor(self, p):
        self.cursor_label.setText("" if p is None else f"x {int(p.x())}  y {int(p.y())}")

    def closeEvent(self, e):
        if self.video is not None:
            self.video.close()
        super().closeEvent(e)
