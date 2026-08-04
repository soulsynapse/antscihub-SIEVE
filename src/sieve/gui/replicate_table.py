"""Table view over the replicate document.

The model never mutates the document directly — every edit routes through
`ReplicateDocument`, which routes through the undo stack. A model that wrote
to the set itself would produce edits Ctrl+Z could not reach.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Any

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
    Signal,
)
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QWidget

from sieve.core.types import ROI
from sieve.gui.document import ReplicateDocument


class Column(IntEnum):
    """Table columns, in display order."""

    NAME = 0
    GROUP = 1
    X = 2
    Y = 3
    WIDTH = 4
    HEIGHT = 5
    AREA = 6


_HEADERS = {
    Column.NAME: "Replicate",
    Column.GROUP: "Group",
    Column.X: "X",
    Column.Y: "Y",
    Column.WIDTH: "W",
    Column.HEIGHT: "H",
    Column.AREA: "Pixels",
}

#: Columns that are read-only because they are computed from something else in
#: the document. Editing one would have to write backwards through the
#: derivation, and for `GROUP` there is nothing coherent to write: "make this
#: replicate group 2" names no parameter change.
_DERIVED = frozenset({Column.GROUP, Column.AREA})

_GEOMETRY_FIELDS: dict[Column, str] = {
    Column.X: "x",
    Column.Y: "y",
    Column.WIDTH: "width",
    Column.HEIGHT: "height",
}


class ReplicateTableModel(QAbstractTableModel):
    """Rows are replicates; geometry is editable in source pixels."""

    def __init__(self, document: ReplicateDocument, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._document = document
        document.structure_changed.connect(self._on_structure_changed)
        document.replicate_changed.connect(self._on_replicate_changed)
        document.grouping_changed.connect(self._on_grouping_changed)

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex | None = None) -> int:
        """Number of replicates."""
        if parent is not None and parent.isValid():
            return 0
        return len(self._document)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex | None = None) -> int:
        """Fixed column count."""
        if parent is not None and parent.isValid():
            return 0
        return len(Column)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Column titles, and 1-based row numbers down the side."""
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return _HEADERS.get(Column(section))
        return section + 1

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Cell contents."""
        if not index.isValid() or index.row() >= len(self._document):
            return None
        replicate = self._document.at(index.row())
        column = Column(index.column())

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if column is Column.NAME:
                return replicate.name
            if column is Column.GROUP:
                # Recomputed for the whole set on every cell read, which is a
                # dozen replicates over a handful of nodes and is not in any
                # latency budget. Caching it per row would need invalidating on
                # every parameter edit anywhere in the graph — that is "on
                # everything", which is what recomputing already does, minus a
                # class of stale-number bugs.
                return self._document.equivalence_groups()[index.row()]
            if column is Column.AREA:
                area = replicate.roi.area
                return f"{area:,}" if role == Qt.ItemDataRole.DisplayRole else area
            return getattr(replicate.roi, _GEOMETRY_FIELDS[column])

        if role == Qt.ItemDataRole.TextAlignmentRole and column is not Column.NAME:
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return None

    def setData(
        self,
        index: QModelIndex | QPersistentModelIndex,
        value: Any,
        role: int = Qt.ItemDataRole.EditRole,
    ) -> bool:
        """Route an edit into an undoable document command."""
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        row = index.row()
        column = Column(index.column())

        if column is Column.NAME:
            # `False` leaves the previous name showing, which is the whole
            # feedback the user gets that an empty or unchanged name was
            # refused. Returning `True` unconditionally tells Qt the model
            # changed and it repaints a cell that did not.
            return self._document.rename(row, str(value))
        if column in _DERIVED:
            return False

        try:
            number = int(value)
        except (TypeError, ValueError):
            return False

        roi = self._document.at(row).roi
        fields = {field: getattr(roi, field) for field in _GEOMETRY_FIELDS.values()}
        fields[_GEOMETRY_FIELDS[column]] = number
        try:
            self._document.set_roi(row, ROI(**fields))
        except ValueError:
            # A zero or negative extent is not a valid region. Reject the edit
            # and leave the previous value showing rather than half-applying.
            return False
        return True

    def flags(self, index: QModelIndex | QPersistentModelIndex) -> Qt.ItemFlag:
        """Everything but the derived columns is editable."""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if Column(index.column()) in _DERIVED:
            return base
        return base | Qt.ItemFlag.ItemIsEditable

    def _on_grouping_changed(self) -> None:
        """Repaint the group column for every row.

        Not one row: a parameter edit anywhere in the graph can move any
        replicate into or out of any group, and the numbers below a change
        shift wholesale because they are positional.
        """
        rows = len(self._document)
        if rows:
            self.dataChanged.emit(
                self.index(0, int(Column.GROUP)),
                self.index(rows - 1, int(Column.GROUP)),
            )

    def _on_structure_changed(self) -> None:
        self.beginResetModel()
        self.endResetModel()

    def _on_replicate_changed(self, row: int) -> None:
        self.dataChanged.emit(
            self.index(row, 0),
            self.index(row, len(Column) - 1),
        )


class EditingAwareDelegate(QStyledItemDelegate):
    """Reports which cell editors are open, by name.

    Playback is on the space bar and deletion is on Delete. Both are window
    shortcuts, and Qt dispatches shortcuts before the focused widget sees the
    key — so without this, typing a space into a replicate name would start
    the video and Delete would remove the row being renamed. The tab disables
    those actions while an editor is live.

    Each editor is named rather than counted because the tab aggregates these
    with the crop-tools fields into one set (`gui/editing_sources.py`), and a
    bare "an editor closed" from one source could otherwise clear another
    source's live claim. Persistent editors make this reachable: a table can
    hold several open at once, closing in any order.
    """

    #: The key of an editor that just opened, or that is about to be destroyed.
    editing_started = Signal(str)
    editing_finished = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        #: Live editors and the keys they were announced under. Held rather
        #: than recomputed, because the name has to be *the same string* on the
        #: way out as on the way in — a key derived twice from the widget is a
        #: key that can differ twice, and a close under the wrong name strands
        #: the keyboard exactly the way this item was filed for. Holding the
        #: editor also keeps its Python wrapper alive for as long as the entry
        #: it identifies, which is what makes the identity stable at all.
        self._keys: dict[QWidget, str] = {}
        #: Never reused, so no editor can inherit a name a previous one wore.
        self._opened = 0

    def createEditor(
        self,
        parent: QWidget,
        option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> QWidget:
        """Open an editor, name it, and announce it."""
        editor = super().createEditor(parent, option, index)
        self._opened += 1
        key = f"cell:{self._opened}:{index.row()}.{index.column()}"
        self._keys[editor] = key
        self.editing_started.emit(key)
        return editor

    def destroyEditor(self, editor: QWidget, index: QModelIndex | QPersistentModelIndex) -> None:
        """Announce the close, then destroy — in that order.

        The lookup needs the editor alive: after `super()` has deleted it, the
        widget is a stale wrapper and nothing can be asked of it. An editor
        this delegate never opened is not an error either — it closes nothing,
        which is the same reason `EditingSources.mark` discards rather than
        removes.
        """
        key = self._keys.pop(editor, None)
        if key is not None:
            self.editing_finished.emit(key)
        super().destroyEditor(editor, index)
