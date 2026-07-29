











































from __future__ import annotations

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QHideEvent, QKeyEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from sieve.core.types import ROI, VideoMetadata
from sieve.gui.document import ReplicateDocument
from sieve.gui.video_view import CropMode




_NO_SOURCE_MAX = 1_000_000


class _NumberField(QSpinBox):



















    editing_changed = Signal(str, bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setKeyboardTracking(False)
        self._editing = False
        self.lineEdit().textEdited.connect(self._on_text_edited)



        self.editingFinished.connect(self._end_edit)

    @Slot(str)
    def _on_text_edited(self, text: str) -> None:

        del text
        if not self._editing:
            self._editing = True
            self.editing_changed.emit(self.objectName(), True)

    @Slot()
    def _end_edit(self) -> None:

        if self._editing:
            self._editing = False
            self.editing_changed.emit(self.objectName(), False)

    def keyPressEvent(self, event: QKeyEvent) -> None:







        if event.key() == Qt.Key.Key_Escape and self._editing:
            committed = self.prefix() + self.textFromValue(self.value()) + self.suffix()
            self.lineEdit().setText(committed)
            self.lineEdit().selectAll()
            self._end_edit()
            event.accept()
            return
        super().keyPressEvent(event)

    def hideEvent(self, event: QHideEvent) -> None:






        super().hideEvent(event)
        self._end_edit()


class CropToolsPanel(QWidget):






    mode_requested = Signal(str)


    stamp_size_changed = Signal(int, int)

    fit_requested = Signal()




    set_all_requested = Signal(int, int)




    editing_changed = Signal(str, bool)

    def __init__(self, document: ReplicateDocument, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._document = document





        self._refreshing = False

        self._draw_button = QRadioButton("Draw")
        self._stamp_button = QRadioButton("Stamp")
        self._mode_group = QButtonGroup(self)
        self._stamp_width = _NumberField()
        self._stamp_height = _NumberField()
        self._set_all_button = QPushButton("Set all to this size")
        self._fit_button = QPushButton("Fit")
        self._zoom_label = QLabel("1.0x")
        self._geometry_box = QGroupBox("Selected replicate")
        self._name_label = QLabel("—")
        self._fields: dict[str, _NumberField] = {
            field: _NumberField() for field in ("x", "y", "width", "height")
        }
        self._source_label = QLabel("No video open")





        self._draw_button.setObjectName("mode-draw")
        self._stamp_button.setObjectName("mode-stamp")
        self._stamp_width.setObjectName("stamp-width")
        self._stamp_height.setObjectName("stamp-height")
        self._set_all_button.setObjectName("set-all")
        self._name_label.setObjectName("replicate-name")
        self._source_label.setObjectName("source-summary")
        for name, field in self._fields.items():
            field.setObjectName(f"roi-{name}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)
        layout.addWidget(self._build_tools_box())
        layout.addWidget(self._build_geometry_box())
        layout.addWidget(self._build_source_box())
        layout.addStretch(1)

        self._connect()
        self.set_source(None)
        self.refresh()



    def _build_tools_box(self) -> QGroupBox:
        box = QGroupBox("Crop tool")
        self._draw_button.setChecked(True)
        self._draw_button.setToolTip("Drag on the video to cut a new replicate.")
        self._stamp_button.setToolTip(
            "Click to place a replicate of the size below. Draw one first, or type it."
        )
        self._mode_group.addButton(self._draw_button)
        self._mode_group.addButton(self._stamp_button)

        modes = QHBoxLayout()
        modes.setContentsMargins(0, 0, 0, 0)
        modes.addWidget(self._draw_button)
        modes.addWidget(self._stamp_button)
        modes.addStretch(1)

        for field in (self._stamp_width, self._stamp_height):
            field.setRange(1, _NO_SOURCE_MAX)
            field.setValue(100)

        stamp = QHBoxLayout()
        stamp.setContentsMargins(0, 0, 0, 0)
        stamp.addWidget(QLabel("W"))
        stamp.addWidget(self._stamp_width, 1)
        stamp.addWidget(QLabel("H"))
        stamp.addWidget(self._stamp_height, 1)

        self._set_all_button.setToolTip(
            "Give every replicate the size above, each keeping its own centre.\n"
            "A rack is arenas of one size; boxes drawn by hand are not."
        )

        self._fit_button.setToolTip("Return to the fitted view. Scroll on the video to magnify.")
        zoom = QHBoxLayout()
        zoom.setContentsMargins(0, 0, 0, 0)
        zoom.addWidget(QLabel("Zoom"))
        zoom.addWidget(self._zoom_label, 1)
        zoom.addWidget(self._fit_button)

        layout = QVBoxLayout(box)
        layout.addLayout(modes)
        layout.addWidget(QLabel("Stamp size"))
        layout.addLayout(stamp)
        layout.addWidget(self._set_all_button)
        layout.addLayout(zoom)
        return box

    def _build_geometry_box(self) -> QGroupBox:
        for field in self._fields.values():
            field.setRange(0, _NO_SOURCE_MAX)

        layout = QFormLayout(self._geometry_box)
        layout.addRow("Name", self._name_label)
        layout.addRow("X", self._fields["x"])
        layout.addRow("Y", self._fields["y"])
        layout.addRow("W", self._fields["width"])
        layout.addRow("H", self._fields["height"])
        return self._geometry_box

    def _build_source_box(self) -> QGroupBox:
        box = QGroupBox("Source")
        self._source_label.setWordWrap(True)
        self._source_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout = QVBoxLayout(box)
        layout.addWidget(self._source_label)
        return box

    def _connect(self) -> None:
        self._draw_button.toggled.connect(self._on_mode_toggled)
        self._stamp_width.valueChanged.connect(self._on_stamp_edited)
        self._stamp_height.valueChanged.connect(self._on_stamp_edited)
        self._fit_button.clicked.connect(self.fit_requested)
        self._set_all_button.clicked.connect(self._on_set_all_clicked)

        for field in self._fields.values():
            field.valueChanged.connect(self._on_geometry_edited)
        for field in (self._stamp_width, self._stamp_height, *self._fields.values()):
            field.editing_changed.connect(self.editing_changed)

        self._document.selection_changed.connect(self.refresh)
        self._document.structure_changed.connect(self.refresh)
        self._document.replicate_changed.connect(self._on_replicate_changed)
        self._document.source_changed.connect(self.refresh)



    @Slot(int, int)
    def set_stamp_size(self, width: int, height: int) -> None:

        self._refreshing = True
        self._stamp_width.setValue(width)
        self._stamp_height.setValue(height)
        self._refreshing = False

    @Slot(float)
    def set_zoom(self, zoom: float) -> None:

        self._zoom_label.setText(f"{zoom:.1f}x")
        self._fit_button.setEnabled(zoom > 1.0)

    def set_source(self, metadata: VideoMetadata | None) -> None:







        if metadata is None:
            self._source_label.setText("No video open")
            for field in (self._stamp_width, self._stamp_height, *self._fields.values()):
                field.setMaximum(_NO_SOURCE_MAX)
            self.refresh()
            return

        seconds = metadata.duration_seconds
        self._source_label.setText(
            f"{metadata.path.name}\n"
            f"{metadata.width} x {metadata.height} · {metadata.fps:.2f} fps\n"
            f"{metadata.frame_count:,} frames · {seconds:.1f} s"
        )
        for field, ceiling in (
            (self._stamp_width, metadata.width),
            (self._stamp_height, metadata.height),
            (self._fields["x"], metadata.width),
            (self._fields["y"], metadata.height),
            (self._fields["width"], metadata.width),
            (self._fields["height"], metadata.height),
        ):
            field.setMaximum(max(ceiling, 1))
        self.refresh()



    @Slot()
    def refresh(self) -> None:

        replicate = self._document.selected_replicate
        self._geometry_box.setEnabled(replicate is not None)




        self._set_all_button.setEnabled(len(self._document) > 0)
        self._name_label.setText(replicate.name if replicate is not None else "—")
        if replicate is None:
            return

        self._refreshing = True
        for name, field in self._fields.items():
            field.setValue(getattr(replicate.roi, name))
        self._refreshing = False

    @Slot(int)
    def _on_replicate_changed(self, row: int) -> None:

        if row == self._document.selected_index:
            self.refresh()

    @Slot()
    def _on_geometry_edited(self) -> None:







        row = self._document.selected_index
        if self._refreshing or row is None:
            return
        try:
            roi = ROI(**{name: field.value() for name, field in self._fields.items()})
        except ValueError:



            return
        self._document.set_roi(row, roi)



    @Slot(str)
    def set_mode(self, mode: str) -> None:








        button = self._draw_button if CropMode(mode) is CropMode.DRAW else self._stamp_button
        button.setChecked(True)

    @Slot(bool)
    def _on_mode_toggled(self, drawing: bool) -> None:
        self.mode_requested.emit(CropMode.DRAW if drawing else CropMode.STAMP)

    @Slot()
    def _on_stamp_edited(self) -> None:
        if self._refreshing:
            return
        self.stamp_size_changed.emit(self._stamp_width.value(), self._stamp_height.value())

    @Slot()
    def _on_set_all_clicked(self) -> None:

        self.set_all_requested.emit(self._stamp_width.value(), self._stamp_height.value())
