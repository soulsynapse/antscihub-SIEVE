























from __future__ import annotations

from PySide6.QtCore import QItemSelection, Qt, Signal, Slot
from PySide6.QtGui import QImage
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from sieve.core.replicates import Replicate
from sieve.core.types import ROI, VideoMetadata
from sieve.gui.crop_tools import CropToolsPanel
from sieve.gui.document import ReplicateDocument
from sieve.gui.editing_sources import EditingSources
from sieve.gui.player import VideoPlayer
from sieve.gui.replicate_table import Column, EditingAwareDelegate, ReplicateTableModel
from sieve.gui.video_view import NO_SELECTION, CropMode, VideoView

_DRAW_HINT = "Drag to cut a replicate.  Drag the selected box or its handles to adjust it."


class ReplicateTab(QWidget):




















    editing_changed = Signal(bool)



    replicate_accepted = Signal(int)

    def __init__(
        self,
        player: VideoPlayer,
        document: ReplicateDocument,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._player = player
        self._document = document



        self._editing = EditingSources()

        self._view = VideoView()
        self._model = ReplicateTableModel(document, self)
        self._table = QTableView()
        self._delegate = EditingAwareDelegate(self._table)

        self._tools_panel = CropToolsPanel(document)

        self._top_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._top_splitter.addWidget(self._build_viewport_panel())
        self._top_splitter.addWidget(self._tools_panel)
        self._top_splitter.setStretchFactor(0, 1)
        self._top_splitter.setStretchFactor(1, 1)
        self._top_splitter.setSizes([500, 500])
        self._top_splitter.setChildrenCollapsible(False)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self._top_splitter)
        splitter.addWidget(self._build_table_panel())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([500, 500])
        splitter.setChildrenCollapsible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

        self._connect()
        self._hint.setEnabled(False)

    @property
    def top_splitter(self) -> QSplitter:

        return self._top_splitter

    @property
    def tools_panel(self) -> CropToolsPanel:

        return self._tools_panel



    def _build_viewport_panel(self) -> QWidget:

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._view, 1)
        return panel

    def _build_table_panel(self) -> QWidget:
        self._table.setModel(self._model)
        self._table.setItemDelegate(self._delegate)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setDefaultSectionSize(22)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(int(Column.NAME), QHeaderView.ResizeMode.Stretch)
        for column in (column for column in Column if column is not Column.NAME):
            header.setSectionResizeMode(int(column), QHeaderView.ResizeMode.ResizeToContents)

        self._delete_button = QPushButton("Delete")
        self._delete_button.setToolTip("Delete the selected replicate (Del)")
        self._delete_button.setEnabled(False)

        self._hint = QLabel(_DRAW_HINT)
        self._hint.setEnabled(False)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(8, 6, 8, 4)
        toolbar.addWidget(QLabel("Replicates"))
        toolbar.addSpacing(12)
        toolbar.addWidget(self._hint, 1)
        toolbar.addWidget(self._delete_button)

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(toolbar)
        layout.addWidget(self._table, 1)
        return panel

    def _connect(self) -> None:
        self._player.opened.connect(self._on_opened)
        self._player.frame_changed.connect(self._on_frame_changed)

        self._view.roi_drawn.connect(self._document.add_roi)
        self._view.selection_requested.connect(self._on_video_clicked)
        self._view.roi_adjusted.connect(self._on_roi_adjusted)
        self._view.roi_adjust_finished.connect(self._on_roi_adjust_finished)
        self._view.stamp_size_changed.connect(self._tools_panel.set_stamp_size)
        self._view.zoom_changed.connect(self._tools_panel.set_zoom)
        self._view.mode_changed.connect(self._tools_panel.set_mode)

        self._tools_panel.mode_requested.connect(self._on_mode_requested)
        self._tools_panel.stamp_size_changed.connect(self._view.set_stamp_size)
        self._tools_panel.fit_requested.connect(self._view.reset_zoom)
        self._tools_panel.set_all_requested.connect(self._document.set_all_to_size)
        self._tools_panel.editing_changed.connect(self._on_source_editing)

        self._document.structure_changed.connect(self._refresh_overlay)
        self._document.replicate_changed.connect(self._refresh_overlay)




        self._document.crops_changed.connect(self._refresh_overlay)
        self._document.selection_changed.connect(self._sync_selection)


        self._table.selectionModel().selectionChanged.connect(self._on_table_selection_changed)

        self._delete_button.clicked.connect(self.delete_selected)
        self._delegate.editing_started.connect(self._on_cell_editor_opened)
        self._delegate.editing_finished.connect(self._on_cell_editor_closed)



    @Slot(str)
    def _on_cell_editor_opened(self, key: str) -> None:
        self._on_source_editing(key, True)

    @Slot(str)
    def _on_cell_editor_closed(self, key: str) -> None:
        self._on_source_editing(key, False)

    @Slot(str, bool)
    def _on_source_editing(self, source: str, editing: bool) -> None:







        was_active = self._editing.active
        self._editing.mark(source, editing)
        if self._editing.active != was_active:
            self.editing_changed.emit(self._editing.active)

    def selected_row(self) -> int:






        index = self._document.selected_index
        return NO_SELECTION if index is None else index

    @Slot()
    def delete_selected(self) -> None:

        row = self.selected_row()
        if row != NO_SELECTION:
            self._document.remove(row)

    def video_closed(self) -> None:

        self._view.set_source_size(None)
        self._tools_panel.set_source(None)
        self._hint.setEnabled(False)



    @Slot(VideoMetadata)
    def _on_opened(self, metadata: VideoMetadata) -> None:
        self._view.set_source_size((metadata.width, metadata.height))
        self._view.set_replicates([])
        self._tools_panel.set_source(metadata)
        self._hint.setEnabled(True)

    @Slot(int, QImage)
    def _on_frame_changed(self, index: int, image: QImage) -> None:
        del index
        self._view.set_frame(image)



    @Slot()
    def _refresh_overlay(self) -> None:
        self._view.set_replicates(self._document.all())


        self._sync_selection()

    @Slot()
    def _sync_selection(self) -> None:

        row = self.selected_row()
        selection = self._table.selectionModel()
        if row == NO_SELECTION:
            selection.clearSelection()
        elif selection.currentIndex().row() != row or not selection.hasSelection():
            self._table.selectRow(row)
            self._table.scrollTo(self._model.index(row, 0))
        self._view.set_selected(row)
        self._delete_button.setEnabled(row != NO_SELECTION)

    @Slot(int)
    def _on_video_clicked(self, row: int) -> None:







        if row == NO_SELECTION:
            return
        self._document.select(row)
        self.replicate_accepted.emit(row)

    @Slot(int, ROI, int, str)
    def _on_roi_adjusted(self, row: int, roi: ROI, gesture: int, verb: str) -> None:






        if 0 <= row < len(self._document):
            self._document.set_roi(
                row, roi, gesture=gesture, text=f"{verb} {self._document.at(row).name}"
            )

    @Slot(int, int)
    def _on_roi_adjust_finished(self, row: int, gesture: int) -> None:






        self._document.finish_roi_gesture(row, gesture, self._confirm_locked_move)

    def _confirm_locked_move(self, replicate: Replicate) -> bool:










        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle("SIEVE")
        box.setText(f"Move {replicate.name}?")
        box.setInformativeText(
            f"{replicate.name} has been tuned at its current position.\n\n"
            "Its settings stay — every parameter you pinned re-resolves against "
            "the new region.\n"
            "Everything computed there is recomputed: the signal, the band "
            "power, and the detections come back from scratch the next time you "
            "look at it."
        )
        box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        box.button(QMessageBox.StandardButton.Ok).setText("Move it")
        box.button(QMessageBox.StandardButton.Cancel).setText("Leave it")
        box.setDefaultButton(QMessageBox.StandardButton.Cancel)
        return box.exec() == QMessageBox.StandardButton.Ok

    @Slot(str)
    def _on_mode_requested(self, mode: str) -> None:








        self._view.set_mode(CropMode(mode))

    @Slot(QItemSelection, QItemSelection)
    def _on_table_selection_changed(
        self, selected: QItemSelection, deselected: QItemSelection
    ) -> None:






        del selected, deselected
        selection = self._table.selectionModel()
        if selection.hasSelection():
            self._document.select(selection.currentIndex().row())
