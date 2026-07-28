"""The replicate tab's right half: what a box is, and what it was cut from.

`REFINED-VISION.md` asks this pane for two unrelated things, and they are
unrelated on purpose. It is where the **cropping tools** live — the draw/stamp
toggle, the stamp's dimensions, the magnifier's reset — and it is where
information "points to the parent", the source video every replicate here is a
region of. One is a control surface and the other is a read-only claim about
provenance, and putting them in one pane is what makes the answer to "how big
should this arena be?" visible next to the field that sets it.

**Nothing here is a second edit path.** Every number written goes through
`ReplicateDocument.set_roi`, exactly as the table's cells do, so it is one
undoable command over one document rather than a parallel route that Ctrl+Z
would reach unevenly. What distinguishes the two surfaces is *when* they are
useful, not what they can express: the table is for reading a rack of a dozen
arenas against each other, and these fields are for the one box being placed,
beside the picture it is being placed on.

**Nor is the draw/stamp toggle a second answer to what the tool is.** It asks
and it displays; `VideoView` holds the mode, for the reason set out in that
module's docstring. The same goes for the stamp's dimensions — the view decides
them (a drawn region, or the replicate being tuned) and these fields show what
it decided, which is why `set_stamp_size` writes without re-announcing.

The fields also announce their own focus. Space is playback and Delete removes
the selected replicate, both as *window* shortcuts, and Qt dispatches a
shortcut before the focused widget sees the key — so without the announcement,
typing into a width field would start the video and Delete would remove the
replicate being edited. `replicate_table.EditingAwareDelegate` solves the same
problem for the table and for the same reason.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFocusEvent
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

#: Upper bound on the spin boxes before a source is known. Replaced with the
#: real frame dimensions on open; a fixed ceiling would quietly refuse a legal
#: coordinate on footage larger than whatever number was guessed here.
_NO_SOURCE_MAX = 1_000_000


class _NumberField(QSpinBox):
    """A spin box that says when it holds the keyboard.

    See the module docstring: the window's single-key shortcuts have to stand
    down while this has focus, and only the widget itself knows when that is.
    """

    focus_changed = Signal(bool)

    def focusInEvent(self, event: QFocusEvent) -> None:
        """Take focus and announce it."""
        super().focusInEvent(event)
        self.focus_changed.emit(True)

    def focusOutEvent(self, event: QFocusEvent) -> None:
        """Give up focus and announce it."""
        super().focusOutEvent(event)
        self.focus_changed.emit(False)


class CropToolsPanel(QWidget):
    """Crop tools, the selected box's dimensions, and the source it came from."""

    #: The draw/stamp toggle was moved by the user, carrying a `CropMode`
    #: value. A *request*, not a statement: `VideoView` owns the mode — it is
    #: the widget that acts on it and the widget that flips to `STAMP` once a
    #: region has been drawn — and this panel repaints from `set_mode` below.
    mode_requested = Signal(str)
    #: The stamp's dimensions were typed. Not emitted when the fields are
    #: refilled from a drawn region — that would race the view that sent it.
    stamp_size_changed = Signal(int, int)
    #: The user asked for the fitted view back.
    fit_requested = Signal()
    #: "Set all" was pressed, carrying the stamp size every replicate is to
    #: take. The size travels with the signal rather than being read back off
    #: this panel by the tab, so the numbers the user was looking at when they
    #: pressed it are the numbers that get applied.
    set_all_requested = Signal(int, int)
    #: A numeric field took or gave up the keyboard.
    editor_open_changed = Signal(bool)

    def __init__(self, document: ReplicateDocument, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._document = document
        #: Set while writing the document's values into the fields, so the
        #: `valueChanged` those writes provoke are not read back as user edits.
        #: The alternative — `blockSignals` on each box — also suppresses the
        #: repaint Qt does on its own behalf, and one flag is easier to reason
        #: about than eight paired calls.
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

        # Object names, so a widget is reachable by what it *is* rather than by
        # its position in a layout. Qt styling and `findChild` both read them;
        # a test that located these by traversal order would be a test that
        # breaks when a row is inserted above them.
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

    # ---- construction ----------------------------------------------------

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
            field.focus_changed.connect(self.editor_open_changed)

        self._document.selection_changed.connect(self.refresh)
        self._document.structure_changed.connect(self.refresh)
        self._document.replicate_changed.connect(self._on_replicate_changed)
        self._document.source_changed.connect(self.refresh)

    # ---- view-facing -----------------------------------------------------

    @Slot(int, int)
    def set_stamp_size(self, width: int, height: int) -> None:
        """Show the size a drawn region established, without re-announcing it."""
        self._refreshing = True
        self._stamp_width.setValue(width)
        self._stamp_height.setValue(height)
        self._refreshing = False

    @Slot(float)
    def set_zoom(self, zoom: float) -> None:
        """Show the current magnification."""
        self._zoom_label.setText(f"{zoom:.1f}x")
        self._fit_button.setEnabled(zoom > 1.0)

    def set_source(self, metadata: VideoMetadata | None) -> None:
        """Describe the parent video, or report that there is none.

        The spin-box ranges come from here rather than from a constant: a
        coordinate outside the frame is not a number the user can mean, and a
        field that refuses it is cheaper feedback than a value silently clamped
        after the fact.
        """
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

    # ---- document -------------------------------------------------------

    @Slot()
    def refresh(self) -> None:
        """Fill the geometry fields from the replicate being tuned."""
        replicate = self._document.selected_replicate
        self._geometry_box.setEnabled(replicate is not None)
        # "Set all" is about the rack rather than about the selection, so it
        # tracks the count and not `replicate`. It stays live at one replicate:
        # resizing a rack of one is a legitimate way to type an exact size onto
        # a box that was drawn by hand.
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
        """Follow a box being dragged on the video, but only the selected one."""
        if row == self._document.selected_index:
            self.refresh()

    @Slot()
    def _on_geometry_edited(self) -> None:
        """Write the four fields back as one region.

        All four, not the one that changed: the document takes a whole `ROI`,
        and reading the other three off the widgets rather than off the
        document is what makes a keyboard tab-through of several fields land as
        the region the user is looking at.
        """
        row = self._document.selected_index
        if self._refreshing or row is None:
            return
        try:
            roi = ROI(**{name: field.value() for name, field in self._fields.items()})
        except ValueError:
            # A zero extent is not a region. The spin boxes' own minimum makes
            # this unreachable today; catching it keeps that a property of the
            # ranges rather than a thing this method assumes about them.
            return
        self._document.set_roi(row, roi)

    # ---- tools ----------------------------------------------------------

    @Slot(str)
    def set_mode(self, mode: str) -> None:
        """Show the mode the view is actually in.

        No `_refreshing` guard, unlike the numeric fields: checking a button
        emits `mode_requested`, which reaches `VideoView.set_mode`, which
        returns without a second signal because the mode is already what is
        being asked for. The round trip stops itself, and a guard here would
        only hide that it does.
        """
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
        """Announce the stamp size as the size every replicate is to take."""
        self.set_all_requested.emit(self._stamp_width.value(), self._stamp_height.value())
