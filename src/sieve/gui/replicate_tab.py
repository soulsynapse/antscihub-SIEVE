"""The Replicate tab: viewport on top, replicate table below, split evenly.

Step 2 of the workflow — cut the source into replicates. The split is a real
splitter rather than a fixed ratio: the table is where the user works once the
boxes exist, and the viewport is where they work while drawing them, so which
half deserves the pixels changes within a single session.
"""

from __future__ import annotations

from PySide6.QtCore import QItemSelection, QSignalBlocker, Qt, Signal, Slot
from PySide6.QtGui import QImage
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from sieve.core.types import VideoMetadata
from sieve.gui.document import ReplicateDocument
from sieve.gui.player import VideoPlayer
from sieve.gui.replicate_table import Column, EditingAwareDelegate, ReplicateTableModel
from sieve.gui.video_view import NO_SELECTION, VideoView

_PLAY_GLYPH = "▶"
_PAUSE_GLYPH = "⏸"
_DRAW_HINT = "Drag on the video to cut a replicate.  Click a box to select it."


def format_timecode(seconds: float) -> str:
    """`M:SS.mmm`, or `H:MM:SS.mmm` past an hour."""
    if seconds < 0.0:
        seconds = 0.0
    hours, remainder = divmod(int(seconds), 3600)
    minutes, whole_seconds = divmod(remainder, 60)
    milliseconds = round((seconds - int(seconds)) * 1000) % 1000
    if hours:
        return f"{hours}:{minutes:02d}:{whole_seconds:02d}.{milliseconds:03d}"
    return f"{minutes}:{whole_seconds:02d}.{milliseconds:03d}"


class ReplicateTab(QWidget):
    """Viewport, transport, and replicate table for one source video."""

    #: True while a table cell editor is open. Window shortcuts that collide
    #: with typing (space, delete) are disabled for the duration.
    editor_open_changed = Signal(bool)

    def __init__(
        self,
        player: VideoPlayer,
        document: ReplicateDocument,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._player = player
        self._document = document
        self._updating_slider = False

        self._view = VideoView()
        self._model = ReplicateTableModel(document, self)
        self._table = QTableView()
        self._delegate = EditingAwareDelegate(self._table)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self._build_viewport_panel())
        splitter.addWidget(self._build_table_panel())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([500, 500])
        splitter.setChildrenCollapsible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

        self._connect()
        self._set_transport_enabled(False)

    # ---- construction ----------------------------------------------------

    def _build_viewport_panel(self) -> QWidget:
        self._play_button = QPushButton(_PLAY_GLYPH)
        self._play_button.setFixedWidth(40)
        self._play_button.setToolTip("Play / pause (Space)")

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 0)
        self._slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._timecode = QLabel("—")
        self._timecode.setTextFormat(Qt.TextFormat.PlainText)
        self._timecode.setMinimumWidth(220)
        self._timecode.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        transport = QHBoxLayout()
        transport.setContentsMargins(8, 4, 8, 6)
        transport.addWidget(self._play_button)
        transport.addWidget(self._slider)
        transport.addWidget(self._timecode)

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._view, 1)
        layout.addLayout(transport)
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
        self._player.playing_changed.connect(self._on_playing_changed)

        self._play_button.clicked.connect(self._player.toggle_play)
        self._slider.valueChanged.connect(self._on_slider_value_changed)
        self._slider.sliderReleased.connect(self._on_slider_released)

        self._view.roi_drawn.connect(self._document.add_roi)
        self._view.selection_requested.connect(self._select_row)

        self._document.structure_changed.connect(self._refresh_overlay)
        self._document.replicate_changed.connect(self._refresh_overlay)
        self._document.replicate_added.connect(self._select_row)

        # `setModel` above guarantees a selection model exists from here on.
        self._table.selectionModel().selectionChanged.connect(self._on_table_selection_changed)

        self._delete_button.clicked.connect(self.delete_selected)
        self._delegate.editing_started.connect(lambda: self.editor_open_changed.emit(True))
        self._delegate.editing_finished.connect(lambda: self.editor_open_changed.emit(False))

    # ---- window-facing actions -------------------------------------------

    def selected_row(self) -> int:
        """Currently selected replicate row, or `NO_SELECTION`."""
        selection = self._table.selectionModel()
        if not selection.hasSelection():
            return NO_SELECTION
        return selection.currentIndex().row()

    @Slot()
    def delete_selected(self) -> None:
        """Delete the selected replicate, if any."""
        row = self.selected_row()
        if row != NO_SELECTION:
            self._document.remove(row)

    def video_closed(self) -> None:
        """Return to the empty state after the source is unloaded."""
        self._view.set_source_size(None)
        self._set_transport_enabled(False)
        with QSignalBlocker(self._slider):
            self._slider.setRange(0, 0)
            self._slider.setValue(0)
        self._timecode.setText("—")

    # ---- player -----------------------------------------------------------

    @Slot(VideoMetadata)
    def _on_opened(self, metadata: VideoMetadata) -> None:
        self._view.set_source_size((metadata.width, metadata.height))
        self._view.set_replicates([])
        with QSignalBlocker(self._slider):
            self._slider.setRange(0, max(metadata.frame_count - 1, 0))
            self._slider.setValue(0)
        self._set_transport_enabled(True)
        self._update_timecode(0)

    @Slot(int, QImage)
    def _on_frame_changed(self, index: int, image: QImage) -> None:
        self._view.set_frame(image)
        if not self._slider.isSliderDown():
            with QSignalBlocker(self._slider):
                self._slider.setValue(index)
        self._update_timecode(index)

    @Slot(bool)
    def _on_playing_changed(self, playing: bool) -> None:
        self._play_button.setText(_PAUSE_GLYPH if playing else _PLAY_GLYPH)

    @Slot(int)
    def _on_slider_value_changed(self, value: int) -> None:
        """Follow the handle.

        A value change with the handle down is a drag position — a guess the
        user is still refining, which the player may approximate to keep up.
        A change with the handle up came from a click on the groove, a wheel,
        or an arrow key, and every one of those is a committed position.
        """
        if self._slider.isSliderDown():
            self._player.scrub(value)
        else:
            self._player.seek(value)

    @Slot()
    def _on_slider_released(self) -> None:
        """Land on the exact frame under the cursor, however coarse the drag was."""
        self._player.seek(self._slider.value())

    def _update_timecode(self, index: int) -> None:
        metadata = self._player.metadata
        if metadata is None:
            self._timecode.setText("—")
            return
        self._timecode.setText(
            f"{format_timecode(metadata.timestamp_of(index))} / "
            f"{format_timecode(metadata.duration_seconds)}   "
            f"frame {index:,} / {metadata.frame_count - 1:,}"
        )

    def _set_transport_enabled(self, enabled: bool) -> None:
        self._play_button.setEnabled(enabled)
        self._slider.setEnabled(enabled)
        self._hint.setEnabled(enabled)

    # ---- replicates -------------------------------------------------------

    @Slot()
    def _refresh_overlay(self) -> None:
        self._view.set_replicates(self._document.all())
        self._delete_button.setEnabled(self.selected_row() != NO_SELECTION)

    @Slot(int)
    def _select_row(self, row: int) -> None:
        selection = self._table.selectionModel()
        if row == NO_SELECTION or row >= len(self._document):
            selection.clearSelection()
            return
        self._table.selectRow(row)
        self._table.scrollTo(self._model.index(row, 0))

    @Slot(QItemSelection, QItemSelection)
    def _on_table_selection_changed(
        self, selected: QItemSelection, deselected: QItemSelection
    ) -> None:
        del selected, deselected
        row = self.selected_row()
        self._view.set_selected(row)
        self._delete_button.setEnabled(row != NO_SELECTION)
