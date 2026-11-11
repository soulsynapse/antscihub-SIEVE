"""The utility's window, each control beside what it acts on: the drawing modes and the stamp group's
link in a rail of glyphs at the left; the frame view in the middle, the video's name and seek bar
under it, and under those the message line with the cursor, the zoom and its two buttons; and at the
right three panels, File (the saved file's name and folder, opening and saving), Shapes (the name
stem, the table and the order) and Library (the kept configurations). Its look is look.py's."""
import os

from . import document, library
from .library import default_folder

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QApplication, QButtonGroup, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
                               QInputDialog, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
                               QSlider, QVBoxLayout, QWidget)

from .editor import MODES, Editor
from .look import RAIL_BUTTON, ElidedLabel, GlyphButton, Panel, label
from .table import ShapeTable
from .video import Video
from .view import FrameView

MODE_GLYPHS = {"select": ("pointer", "Select", "V"), "circle": ("circle", "Circle from its centre", "C"),
               "circle3": ("circle-3", "Circle through three points", "Shift+C"),
               "square": ("square", "Square, corner to corner; its top handle turns it", "S"),
               "rectangle": ("rectangle", "Rectangle, corner to corner", "R"),
               "polygon": ("polygon", "Polygon: click each vertex, Enter or the first closes", "P"),
               "stamp": ("rubber-stamp", "Stamp the selected shape at each click", "T")}
SIDE_W = 340
GEOMETRY_FILTER = "Geometry (*.json);;All files (*)"
VIDEO_FILTER = "Video (*.mp4 *.mov *.avi *.mts *.m2ts *.mkv *.MP4 *.MOV *.AVI *.MTS);;All files (*)"


def clock(index, fps):
    t = index / fps
    return f"{int(t // 60)}:{t % 60:06.3f}"


class GeometryWindow(QMainWindow):
    """Opens `video` when given one; `ask_video` asks for one by a file dialog. The file Save writes
    is `file` when given, opened when it is on disk; otherwise it is `<stem>-geometry.json` beside
    the first video opened, likewise opened when on disk. Save as and Open alone move it. Save
    writes it only when the drawing differs from it, and closing, Open and loading a configuration
    over a drawing that differs go through `ask_unsaved` first. `library` is the configurations'
    folder, by default the per-user one, made on the first configuration kept."""

    def __init__(self, video=None, file=None, library=None):
        super().__init__()
        self.library = library if library is not None else default_folder()
        self.video = None
        self.file = None
        self.source = None
        self.file_plate = None
        self.index = 0
        self.frame = None
        self.editor = Editor()
        self.view = FrameView(self.editor)
        self.table = ShapeTable(self.editor)
        self.editor.on_change = self._drawing_changed

        self.modes = QButtonGroup(self)
        self.mode_buttons = {}
        for m in MODES:
            name, tip, keys = MODE_GLYPHS[m]
            b = GlyphButton(name, f"{tip}  ({keys})", checkable=True, side=RAIL_BUTTON)
            self.modes.addButton(b)
            self.mode_buttons[m] = b
            b.clicked.connect(lambda _=False, m=m: self.editor.set_mode(m))
        self.mode_buttons["select"].setChecked(True)
        self.link_button = GlyphButton("unlink", "The selected stamp group's link: on, an edit to one member "
                                       "but a move is made to every member", checkable=True, on="link",
                                       side=RAIL_BUTTON)
        self.link_button.setEnabled(False)

        self.open_button = GlyphButton("movie", "Open a video…")
        self.video_label = ElidedLabel("no video", "name")
        self.seek_bar = QSlider(Qt.Orientation.Horizontal)
        self.seek_bar.setEnabled(False)
        self.frame_label = label()
        self.message = ElidedLabel()
        self.cursor_label, self.zoom_label = label(), label()
        self.fit_button = GlyphButton("maximize", "Fit the frame to the view")
        self.actual_button = GlyphButton("zoom-reset", "100%: one frame pixel to one screen pixel")

        self.open_file_button = GlyphButton("folder-open", "Open a geometry file…")
        self.save_button = GlyphButton("device-floppy", "Save  (Ctrl+S)")
        self.save_as_button = GlyphButton("file-export", "Save as…")
        self.name_label = ElidedLabel("", "name")
        self.folder_label = ElidedLabel()
        self.copy_name = GlyphButton("copy", "Copy the file's name, for a file node's pattern")
        self.copy_folder = GlyphButton("copy", "Copy the file's folder, for a file node's folder")

        self.stem_field = QLineEdit()
        self.stem_field.setPlaceholderText("the kind, then -1, -2…")
        self.stem_field.setToolTip("The stem a new shape is named by, with the least free index")
        self.up_button = GlyphButton("arrow-up", "Move the selected shape up: drawn earlier, picked later")
        self.down_button = GlyphButton("arrow-down", "Move the selected shape down: drawn later, picked first")
        self.delete_button = GlyphButton("trash", "Delete the selected shape  (Delete)")

        self.kept_list = QListWidget()
        self.keep_button = GlyphButton("bookmark-plus", "Keep the drawing in the library…")
        self.load_button = GlyphButton("file-import", "Load the chosen configuration onto this video")
        self.rename_kept_button = GlyphButton("pencil", "Rename the chosen configuration…")
        self.remove_kept_button = GlyphButton("trash", "Remove the chosen configuration…")

        rail = QFrame()
        rail.setObjectName("rail")
        rail_col = QVBoxLayout(rail)
        rail_col.setContentsMargins(4, 6, 4, 6)
        rail_col.setSpacing(2)
        for m in MODES:
            rail_col.addWidget(self.mode_buttons[m])
            if m == "select":
                rail_col.addSpacing(8)
        rail_col.addSpacing(8)
        rail_col.addWidget(self.link_button)
        rail_col.addStretch(1)

        transport = QHBoxLayout()
        transport.setSpacing(8)
        transport.addWidget(self.open_button)
        self.video_label.setMinimumWidth(80)
        self.video_label.setMaximumWidth(220)
        transport.addWidget(self.video_label, 1)
        transport.addWidget(self.seek_bar, 4)
        transport.addWidget(self.frame_label)
        status = QHBoxLayout()
        status.setSpacing(10)
        status.addWidget(self.message, 1)
        status.addWidget(self.cursor_label)
        status.addWidget(self.zoom_label)
        status.addWidget(self.fit_button)
        status.addWidget(self.actual_button)
        centre = QVBoxLayout()
        centre.setSpacing(6)
        centre.addWidget(self.view, 1)
        centre.addLayout(transport)
        centre.addLayout(status)

        file_panel = Panel("File")
        for b in (self.open_file_button, self.save_button, self.save_as_button):
            file_panel.head.addWidget(b)
        where = QGridLayout()
        where.setHorizontalSpacing(6)
        where.setVerticalSpacing(0)
        where.setColumnStretch(0, 1)
        where.addWidget(self.name_label, 0, 0)
        where.addWidget(self.copy_name, 0, 1)
        where.addWidget(self.folder_label, 1, 0)
        where.addWidget(self.copy_folder, 1, 1)
        file_panel.body.addLayout(where)
        shapes_panel = Panel("Shapes")
        for b in (self.up_button, self.down_button, self.delete_button):
            shapes_panel.head.addWidget(b)
        stem_row = QHBoxLayout()
        stem_row.setSpacing(8)
        stem_row.addWidget(label("New names"))
        stem_row.addWidget(self.stem_field, 1)
        shapes_panel.body.addLayout(stem_row)
        shapes_panel.body.addWidget(self.table, 1)
        library_panel = Panel("Library")
        for b in (self.keep_button, self.load_button, self.rename_kept_button, self.remove_kept_button):
            library_panel.head.addWidget(b)
        library_panel.body.addWidget(self.kept_list, 1)
        side = QVBoxLayout()
        side.setSpacing(8)
        side.addWidget(file_panel)
        side.addWidget(shapes_panel, 3)
        side.addWidget(library_panel, 2)
        side_box = QWidget()
        side_box.setFixedWidth(SIDE_W)
        side_box.setLayout(side)
        side.setContentsMargins(0, 0, 0, 0)

        root = QHBoxLayout()
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)
        root.addWidget(rail, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(centre, 1)
        root.addWidget(side_box)
        central = QWidget()
        central.setObjectName("ground")
        central.setLayout(root)
        self.setCentralWidget(central)
        self.setWindowTitle("Geometry[*]")
        self.resize(1280, 800)

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
        self.view.zoomed.connect(lambda s: self.zoom_label.setText(f"{s * 100:.0f}%"))
        self.table.refused.connect(self.message.setText)
        self.stem_field.textChanged.connect(lambda t: setattr(self.editor, "stem", t.strip()))
        self.link_button.clicked.connect(lambda on: self.editor.set_link(self.editor.current.group, on))
        self.up_button.clicked.connect(lambda: self.editor.move_shape(self.editor.selected, -1))
        self.down_button.clicked.connect(lambda: self.editor.move_shape(self.editor.selected, 1))
        self.delete_button.clicked.connect(self.editor.delete_selected)
        self.keep_button.clicked.connect(self.ask_keep)
        self.load_button.clicked.connect(lambda: self._chosen() is not None and self.load_configuration(self._chosen()))
        self.kept_list.itemDoubleClicked.connect(lambda item: self.load_configuration(item.data(Qt.ItemDataRole.UserRole)))
        self.kept_list.currentItemChanged.connect(self._show_file)
        self.rename_kept_button.clicked.connect(self.ask_rename_kept)
        self.remove_kept_button.clicked.connect(self.ask_remove_kept)
        self.refresh_library()
        self._show_file()
        delete = QAction(self)
        delete.setShortcut(QKeySequence.StandardKey.Delete)
        delete.triggered.connect(self.editor.delete_selected)
        self.addAction(delete)
        keyed = [("Ctrl+Z", self.editor.undo), ("Ctrl+Shift+Z", self.editor.redo), ("Ctrl+S", self.save)]
        keyed += [(MODE_GLYPHS[m][2], lambda _=False, m=m: self.editor.set_mode(m)) for m in MODES]
        for keys, act in keyed:
            a = QAction(self)
            a.setShortcut(QKeySequence(keys))
            a.triggered.connect(act)
            self.addAction(a)
        if file is not None:
            self._set_file(os.path.abspath(file))
        if video is not None:
            self.open_video(video)
        if file is not None and os.path.exists(file):
            self._open(file, "")

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
        self.setWindowTitle(f"Geometry — {os.path.basename(video.path)}  {video.plate[1]}×{video.plate[0]}[*]")
        self.video_label.setText(os.path.basename(video.path))
        self.video_label.setToolTip(video.path)
        self.seek_bar.blockSignals(True)
        self.seek_bar.setRange(0, video.count - 1)
        self.seek_bar.setValue(0)
        self.seek_bar.blockSignals(False)
        self.seek_bar.setEnabled(True)
        self.seek(0)
        if self.file is None:
            beside = os.path.abspath(f"{os.path.splitext(video.path)[0]}-geometry.json")
            if os.path.exists(beside):
                self._open(beside, f"opened {os.path.basename(beside)} beside the video")
            else:
                self._set_file(beside)
        self._show_file()
        return True

    def ask_file(self):
        if not self._leaving():
            return
        start = self.file or (os.path.dirname(self.video.path) if self.video is not None else "")
        path, _ = QFileDialog.getOpenFileName(self, "Open a geometry file", start, GEOMETRY_FILTER)
        if path:
            self._open(path, "")

    def open_file(self, path):
        """True when the file opened, after `ask_unsaved` where the drawing differs from the file;
        otherwise the message line says why and the drawing stays."""
        return self._leaving() and self._open(path, "")

    def _open(self, path, said):
        source = self._load_drawing(path, said)
        if source is None:
            return False
        self._set_file(os.path.abspath(path), source)
        return True

    def _load_drawing(self, path, said):
        """The Source of the file at `path` once its shapes are the drawing, or None, the message line
        saying why, with the drawing as it was."""
        try:
            plate, shapes, inferred, source = document.load(path)
        except ValueError as e:
            self.message.setText(str(e))
            return None
        self.file_plate = plate
        if self.video is None:
            self.editor.plate = plate
        self.editor.load(shapes)
        lines = [said, self._plate_line()]
        if inferred:
            lines.append(f"kind inferred from the shape for {', '.join(inferred)}")
        self.message.setText("; ".join(t for t in lines if t))
        return source

    def refresh_library(self):
        self.kept_list.clear()
        for k in library.listed(self.library):
            plate = "unreadable" if k.plate is None else f"{k.plate[1]}×{k.plate[0]}"
            item = QListWidgetItem(f"{k.name}    {plate} · {k.date:%Y-%m-%d}")
            item.setData(Qt.ItemDataRole.UserRole, k.name)
            item.setToolTip(f"{k.path}, kept {k.date:%Y-%m-%d %H:%M}")
            self.kept_list.addItem(item)
        self._show_file()

    def kept_names(self):
        return [self.kept_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.kept_list.count())]

    def _chosen(self):
        item = self.kept_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def keep_configuration(self, name, replace=False):
        """True when the drawing was kept under `name`; refused as a save is, and for a name already
        kept unless `replace`."""
        if not self._savable():
            return False
        try:
            library.keep(self.library, name, self.editor.plate, self.editor.shapes, replace)
        except (ValueError, OSError) as e:
            self.message.setText(f"not kept: {e}")
            return False
        self.refresh_library()
        self.message.setText(f"kept configuration {name}")
        return True

    def load_configuration(self, name):
        """Opens the kept configuration's shapes onto the open video under the plate check, after
        `ask_unsaved` where the drawing differs from the file; the file a save writes is unchanged,
        so a configuration is never overwritten by a save."""
        if not self._leaving():
            return False
        return self._load_drawing(os.path.join(self.library, f"{name}.json"), f"loaded configuration {name}") is not None

    def rename_configuration(self, old, new):
        try:
            library.rename(self.library, old, new)
        except (ValueError, OSError) as e:
            self.message.setText(f"not renamed: {e}")
            return False
        self.refresh_library()
        return True

    def remove_configuration(self, name):
        try:
            library.remove(self.library, name)
        except OSError as e:
            self.message.setText(f"not removed: {e}")
            return False
        self.refresh_library()
        return True

    def ask_keep(self):
        name, ok = QInputDialog.getText(self, "Keep configuration", "Name:", text=self._chosen() or "")
        name = name.strip()
        if not ok or not name:
            return
        taken = name in self.kept_names()
        if taken and QMessageBox.question(self, "Keep configuration", f"Replace the kept {name}?") \
                != QMessageBox.StandardButton.Yes:
            return
        self.keep_configuration(name, replace=taken)

    def ask_rename_kept(self):
        old = self._chosen()
        if old is None:
            return
        new, ok = QInputDialog.getText(self, "Rename configuration", "Name:", text=old)
        if ok and new.strip() != old:
            self.rename_configuration(old, new.strip())

    def ask_remove_kept(self):
        name = self._chosen()
        if name is not None and QMessageBox.question(self, "Remove configuration", f"Remove the kept {name}?") \
                == QMessageBox.StandardButton.Yes:
            self.remove_configuration(name)

    def _plate_line(self):
        if self.file_plate is None or self.video is None or tuple(self.file_plate) == tuple(self.video.plate):
            return ""
        (fh, fw), (vh, vw) = self.file_plate, self.video.plate
        out = self.editor.outside()
        past = f", {len(out)} past its edge marked until brought within" if out else ""
        return f"the file's plate is {fw}×{fh} and the video's {vw}×{vh}{past}"

    def _set_file(self, path, source=None):
        """`path` is the file Save writes, `source` what it holds, None when it is not on disk."""
        self.file, self.source = path, source
        self._show_file()

    def differs(self):
        """Whether Save would change the file: what it would write is not what the file held when
        last read or written, or the file is not on disk and the drawing holds a shape."""
        if self.source is None or self.editor.plate is None:
            return bool(self.editor.shapes)
        return document.to_json(self.editor.plate, self.editor.shapes, self.source) != self.source.top

    def _show_file(self):
        """The File panel's name and folder, the unsaved mark on the title, the name line and the
        Save button, and which file and library buttons have something to act on."""
        dirty = self.differs()
        if self.file is None:
            self.name_label.setText("no file")
            self.folder_label.setText("the first video opened settles it, or Save as")
        else:
            name = os.path.basename(self.file)
            self.name_label.setText(f"{name} — unsaved changes" if dirty else name)
            self.folder_label.setText(os.path.dirname(self.file))
        self.setWindowModified(dirty)
        self.save_button.setEnabled(dirty)
        self.folder_label.setToolTip(self.file or "")
        self.copy_name.setEnabled(self.file is not None)
        self.copy_folder.setEnabled(self.file is not None)
        chosen = self._chosen() is not None
        for b in (self.load_button, self.rename_kept_button, self.remove_kept_button):
            b.setEnabled(chosen)

    def save(self):
        """True when written; nothing is written, and the message line says so, while the drawing
        does not differ from the file, and the save is refused while a shape is past the plate's
        edge or there is no plate."""
        if self.file is None:
            self.message.setText("no file to save to: open a video, or Save as")
            return False
        if not self.differs():
            self.message.setText(f"nothing to save: {os.path.basename(self.file)} holds the drawing")
            return False
        return self.save_to(self.file)

    def save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save the geometry file", self.file or "", GEOMETRY_FILTER)
        return self.save_to(path) if path else False

    def ask_unsaved(self):
        """"save", "discard" or "cancel", asked by a dialog naming the file and what each does."""
        name = os.path.basename(self.file) if self.file is not None else "the drawing"
        box = QMessageBox(self)
        box.setWindowTitle("Unsaved changes")
        box.setText(f"{name} has unsaved changes.")
        box.setInformativeText(f"Save writes {name}, and a region wired to it re-reads it. Discard goes on and "
                               "loses every change since the file was read or saved. Cancel leaves the window as it was.")
        buttons = QMessageBox.StandardButton
        box.setStandardButtons(buttons.Save | buttons.Discard | buttons.Cancel)
        box.setDefaultButton(buttons.Save)
        box.exec()
        return {buttons.Save: "save", buttons.Discard: "discard"}.get(box.standardButton(box.clickedButton()), "cancel")

    def _leaving(self):
        """True when the drawing may be left behind: it is the file's, or the user chose Discard, or
        chose Save and the save was taken."""
        if not self.differs():
            return True
        answer = self.ask_unsaved()
        return self.save() if answer == "save" else answer == "discard"

    def _savable(self):
        if self.editor.plate is None:
            self.message.setText("nothing to save against: open a video first")
            return False
        out = self.editor.outside()
        if out:
            self.message.setText(f"not saved: {', '.join(out)} past the plate's edge")
            return False
        return True

    def save_to(self, path):
        if not self._savable():
            return False
        source = document.save(path, self.editor.plate, self.editor.shapes, self.source)
        self.file_plate = tuple(self.editor.plate)
        self._set_file(os.path.abspath(path), source)
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
        for b in (self.up_button, self.down_button, self.delete_button):
            b.setEnabled(s is not None)
        self.view.viewport().update()
        self.table.refresh()
        self._show_file()

    def _show_cursor(self, p):
        self.cursor_label.setText("" if p is None else f"x {int(p.x())}  y {int(p.y())}")

    def closeEvent(self, e):
        if not self._leaving():
            e.ignore()
            return
        if self.video is not None:
            self.video.close()
        super().closeEvent(e)
