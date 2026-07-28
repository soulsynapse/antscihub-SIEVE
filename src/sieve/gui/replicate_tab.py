"""The Replicate tab: viewport on top, replicate table below, split evenly.

Step 2 of the workflow — cut the source into replicates. The split is a real
splitter rather than a fixed ratio: the table is where the user works once the
boxes exist, and the viewport is where they work while drawing them, so which
half deserves the pixels changes within a single session.

The top half is split again, left and right. The right half is
`gui/crop_tools.py`: the draw/stamp toggle, the magnifier's reset, the selected
box's dimensions, and what the source video is. That pane is a control surface
and a provenance claim in one, which is what `REFINED-VISION.md` asks for when
it says the settings should "point to the parent".

**The left half is the picture and nothing else.** There is no seeker here and
no clip editor: both are `gui/timeline_bar.py`, one band across the bottom of
the window and outside every tab. A transport living inside a tab answers
"where am I" once per tab, and the copies drift; a transport that spans the
window answers it once. What this tab keeps is the only thing that is genuinely
about *this* tab — the frame, the boxes drawn on it, and the table of them.
The decode-format toggle is deliberately *not* here, and neither is its
effect: the stutter it fixes is felt in the tuning loop, so it lives on the
filter tab (`gui/gray_toggle.py`) and the gray decode applies only while that
tab is showing — here, colour is what identifies an arena.
"""

from __future__ import annotations

from PySide6.QtCore import QItemSelection, Qt, Signal, Slot
from PySide6.QtGui import QImage
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from sieve.core.types import ROI, VideoMetadata
from sieve.gui.crop_tools import CropToolsPanel
from sieve.gui.document import ReplicateDocument
from sieve.gui.editing_sources import EditingSources
from sieve.gui.player import VideoPlayer
from sieve.gui.replicate_table import Column, EditingAwareDelegate, ReplicateTableModel
from sieve.gui.video_view import NO_SELECTION, CropMode, VideoView

_DRAW_HINT = "Drag to cut a replicate.  Drag the selected box or its handles to adjust it."


class ReplicateTab(QWidget):
    """Viewport and replicate table for one source video.

    The selected replicate lives on the document, not here: the filter tab
    renders whichever arena is selected, so a selection kept in this tab's
    table would be a second answer to "which arena am I looking at". The
    table pushes clicks into `ReplicateDocument.select` and repaints from
    `selection_changed` — it has to, because the model resets wholesale on
    every structure change and a reset clears the view's own selection.

    Two gestures, two meanings (REFINED-VISION, Replicates): a click on a
    table *row* selects, which is what the user wants while drawing the next
    twelve boxes; a click on a box in the *video* accepts it — selects and
    asks the window to move over to the filter tab with that arena under it.
    """

    #: True while *anything* in this tab is being typed into — a table cell
    #: editor, or a crop-tools number field between its first keystroke and its
    #: commit. Window shortcuts that collide with typing (space, delete, I, O)
    #: are disabled for the duration. One aggregate over a set of named
    #: sources, so no source's close can clear another's live claim.
    editing_changed = Signal(bool)
    #: A box on the video was clicked: the replicate at this row is accepted,
    #: and the window should show the filter tab. The selection itself has
    #: already gone through the document by the time this fires.
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
        #: Who currently claims the keyboard. Two independent sources feed it —
        #: the table's cell editors and the crop-tools fields — and the window
        #: is told only when the aggregate flips.
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
        """The horizontal split between the player and the tool pane."""
        return self._top_splitter

    @property
    def tools_panel(self) -> CropToolsPanel:
        """The crop tools and source information occupying the right half."""
        return self._tools_panel

    # ---- construction ----------------------------------------------------

    def _build_viewport_panel(self) -> QWidget:
        """The picture, and nothing under it."""
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
        self._document.selection_changed.connect(self._sync_selection)

        # `setModel` above guarantees a selection model exists from here on.
        self._table.selectionModel().selectionChanged.connect(self._on_table_selection_changed)

        self._delete_button.clicked.connect(self.delete_selected)
        self._delegate.editing_started.connect(self._on_cell_editor_opened)
        self._delegate.editing_finished.connect(self._on_cell_editor_closed)

    # ---- window-facing actions -------------------------------------------

    @Slot(str)
    def _on_cell_editor_opened(self, key: str) -> None:
        self._on_source_editing(key, True)

    @Slot(str)
    def _on_cell_editor_closed(self, key: str) -> None:
        self._on_source_editing(key, False)

    @Slot(str, bool)
    def _on_source_editing(self, source: str, editing: bool) -> None:
        """One source changed its mind; tell the window only if the answer did.

        The signal is edge-triggered on the *aggregate*, not relayed per
        source: the window's guard is "is anything being typed into", and
        re-asserting True while a second editor opens would make the two
        sources' closes look like they had to arrive in order. They do not.
        """
        was_active = self._editing.active
        self._editing.mark(source, editing)
        if self._editing.active != was_active:
            self.editing_changed.emit(self._editing.active)

    def selected_row(self) -> int:
        """Currently selected replicate row, or `NO_SELECTION`.

        Read from the document rather than from the table: the table's own
        selection dies on every model reset, and this method is what the
        window's Delete action believes.
        """
        index = self._document.selected_index
        return NO_SELECTION if index is None else index

    @Slot()
    def delete_selected(self) -> None:
        """Delete the selected replicate, if any."""
        row = self.selected_row()
        if row != NO_SELECTION:
            self._document.remove(row)

    def video_closed(self) -> None:
        """Return to the empty state after the source is unloaded."""
        self._view.set_source_size(None)
        self._tools_panel.set_source(None)
        self._hint.setEnabled(False)

    # ---- player -----------------------------------------------------------

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

    # ---- replicates -------------------------------------------------------

    @Slot()
    def _refresh_overlay(self) -> None:
        self._view.set_replicates(self._document.all())
        # The model reset that redrew the table also cleared its selection;
        # the document's answer survived, so put it back on screen.
        self._sync_selection()

    @Slot()
    def _sync_selection(self) -> None:
        """Repaint every view of the document's selection, table included."""
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
        """A click on a box accepts that replicate; empty space is a miss.

        Accept is the vision's sentence — select it, and hand the user to the
        filter tab with it under them. A miss changes nothing: "no replicate
        selected" is not a state the tuning loop has a rendering for, so
        deselection is not a gesture this tab offers.
        """
        if row == NO_SELECTION:
            return
        self._document.select(row)
        self.replicate_accepted.emit(row)

    @Slot(int, ROI, int, str)
    def _on_roi_adjusted(self, row: int, roi: ROI, gesture: int, verb: str) -> None:
        """One step of a live move or resize on the video.

        The token is passed straight through to the document, which passes it
        to the command: every step of one drag carries the same one, so sixty
        emitted geometries collapse to a single undo entry rather than sixty.
        """
        if 0 <= row < len(self._document):
            self._document.set_roi(
                row, roi, gesture=gesture, text=f"{verb} {self._document.at(row).name}"
            )

    @Slot(str)
    def _on_mode_requested(self, mode: str) -> None:
        """The tools panel's toggle, widened back into the view's enum.

        One direction of a two-way binding, and the tab carries both halves so
        neither widget has to know the other exists: the view announces
        `mode_changed` and the panel repaints from it. The view is the owner —
        see its module docstring — because it is the one that flips to `STAMP`
        of its own accord once a region has been drawn.
        """
        self._view.set_mode(CropMode(mode))

    @Slot(QItemSelection, QItemSelection)
    def _on_table_selection_changed(
        self, selected: QItemSelection, deselected: QItemSelection
    ) -> None:
        """A table click becomes the document's selection — and only a click.

        An *emptied* table selection is pushed nowhere: the model clears the
        view's selection on every reset, and treating that echo as a user
        gesture would drop the document's answer every time a box is drawn.
        """
        del selected, deselected
        selection = self._table.selectionModel()
        if selection.hasSelection():
            self._document.select(selection.currentIndex().row())
