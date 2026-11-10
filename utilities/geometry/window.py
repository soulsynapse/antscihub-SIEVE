"""The utility's window: the frame view, a row of view controls above it with the cursor's plate
position, the drawing modes as one exclusive row of buttons with the selected stamp group's link
beside them, the shapes' table on the right under the name stem and the buttons moving a row, and a
seek bar below with the frame's index and time, over the saved file's folder and name. Opening and
saving the file sit with the view controls. Its look is its own, since the player's theme is the
player's."""
import os

from . import document

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont, QFontDatabase, QKeySequence
from PySide6.QtWidgets import (QApplication, QButtonGroup, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
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
GEOMETRY_FILTER = "Geometry (*.json);;All files (*)"
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
    """Opens `video` when given one; `ask_video` asks for one by a file dialog. `file` is opened
    when it is on disk and is otherwise where the first save lands; with none the first save asks,
    beside the video by default."""

    def __init__(self, video=None, file=None):
        super().__init__()
        self.video = None
        self.file = None
        self.file_plate = None
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
        self.open_file_button, self.save_button = QPushButton("Open file…"), QPushButton("Save")
        self.save_as_button = QPushButton("Save as…")
        self.folder_label, self.name_label = QLabel(), QLabel()
        self.copy_folder, self.copy_name = QPushButton("Copy folder"), QPushButton("Copy name")
        self.cursor_label, self.frame_label = QLabel(), QLabel()
        self.message = QLabel()
        for lab in (self.cursor_label, self.frame_label, self.message, self.folder_label, self.name_label):
            lab.setObjectName("readout")
        self.seek_bar = QSlider(Qt.Orientation.Horizontal)
        self.seek_bar.setEnabled(False)

        top = QHBoxLayout()
        for w in (self.open_button, self.open_file_button, self.save_button, self.save_as_button,
                  self.fit_button, self.actual_button):
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
        saved = QHBoxLayout()
        for w in (self.folder_label, self.copy_folder, self.name_label, self.copy_name):
            saved.addWidget(w)
        saved.addStretch(1)
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
        body.addLayout(saved)
        central = QWidget()
        central.setLayout(body)
        self.setCentralWidget(central)
        self.setWindowTitle("Geometry")
        self.resize(1100, 760)

        self.open_button.clicked.connect(self.ask_video)
        self.open_file_button.clicked.connect(self.ask_file)
        self.save_button.clicked.connect(self.save)
        self.save_as_button.clicked.connect(self.save_as)
        self.copy_folder.clicked.connect(lambda: QApplication.clipboard().setText(os.path.dirname(self.file or "")))
        self.copy_name.clicked.connect(lambda: QApplication.clipboard().setText(os.path.basename(self.file or "")))
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
        for keys, act in (("Ctrl+Z", self.editor.undo), ("Ctrl+Shift+Z", self.editor.redo), ("Ctrl+S", self.save)):
            a = QAction(self)
            a.setShortcut(QKeySequence(keys))
            a.triggered.connect(act)
            self.addAction(a)
        if video is not None:
            self.open_video(video)
        if file is not None:
            if os.path.exists(file):
                self.open_file(file)
            else:
                self._set_file(os.path.abspath(file))

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
        self.message.setText(self._plate_line())
        self.view.viewport().update()
        self.setWindowTitle(f"Geometry — {os.path.basename(video.path)}  {video.plate[1]}×{video.plate[0]}")
        self.seek_bar.blockSignals(True)
        self.seek_bar.setRange(0, video.count - 1)
        self.seek_bar.setValue(0)
        self.seek_bar.blockSignals(False)
        self.seek_bar.setEnabled(True)
        self.seek(0)
        return True

    def ask_file(self):
        start = self.file or (os.path.dirname(self.video.path) if self.video is not None else "")
        path, _ = QFileDialog.getOpenFileName(self, "Open a geometry file", start, GEOMETRY_FILTER)
        if path:
            self.open_file(path)

    def open_file(self, path):
        """True when the file opened; otherwise the message line says why and the drawing stays."""
        try:
            plate, shapes, inferred = document.load(path)
        except ValueError as e:
            self.message.setText(str(e))
            return False
        self.file_plate = plate
        if self.video is None:
            self.editor.plate = plate
        self.editor.load(shapes)
        self._set_file(os.path.abspath(path))
        lines = [self._plate_line()]
        if inferred:
            lines.append(f"kind inferred from the shape for {', '.join(inferred)}")
        self.message.setText("; ".join(t for t in lines if t))
        return True

    def _plate_line(self):
        if self.file_plate is None or self.video is None or tuple(self.file_plate) == tuple(self.video.plate):
            return ""
        (fh, fw), (vh, vw) = self.file_plate, self.video.plate
        out = self.editor.outside()
        past = f", {len(out)} past its edge marked until brought within" if out else ""
        return f"the file's plate is {fw}×{fh} and the video's {vw}×{vh}{past}"

    def _set_file(self, path):
        self.file = path
        self.folder_label.setText(os.path.dirname(path))
        self.name_label.setText(os.path.basename(path))

    def save(self):
        """True when written; refused while a shape is past the plate's edge or there is no plate."""
        if self.file is None:
            return self.save_as()
        return self.save_to(self.file)

    def save_as(self):
        start = self.file
        if start is None and self.video is not None:
            stem = os.path.splitext(self.video.path)[0]
            start = f"{stem}-geometry.json"
        path, _ = QFileDialog.getSaveFileName(self, "Save the geometry file", start or "", GEOMETRY_FILTER)
        return self.save_to(path) if path else False

    def save_to(self, path):
        if self.editor.plate is None:
            self.message.setText("nothing to save against: open a video first")
            return False
        out = self.editor.outside()
        if out:
            self.message.setText(f"not saved: {', '.join(out)} past the plate's edge")
            return False
        document.save(path, self.editor.plate, self.editor.shapes)
        self.file_plate = tuple(self.editor.plate)
        self._set_file(os.path.abspath(path))
        self.message.setText(f"saved {os.path.basename(path)}")
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
