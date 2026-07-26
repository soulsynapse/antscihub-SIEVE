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
    X = 1
    Y = 2
    WIDTH = 3
    HEIGHT = 4
    AREA = 5


_HEADERS = {
    Column.NAME: "Replicate",
    Column.X: "X",
    Column.Y: "Y",
    Column.WIDTH: "W",
    Column.HEIGHT: "H",
    Column.AREA: "Pixels",
}

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
            self._document.rename(row, str(value))
            return True
        if column is Column.AREA:
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
        """Everything but the derived area column is editable."""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if Column(index.column()) is Column.AREA:
            return base
        return base | Qt.ItemFlag.ItemIsEditable

    def _on_structure_changed(self) -> None:
        self.beginResetModel()
        self.endResetModel()

    def _on_replicate_changed(self, row: int) -> None:
        self.dataChanged.emit(
            self.index(row, 0),
            self.index(row, len(Column) - 1),
        )


class EditingAwareDelegate(QStyledItemDelegate):
    """Reports when a cell editor is open.

    Playback is on the space bar and deletion is on Delete. Both are window
    shortcuts, and Qt dispatches shortcuts before the focused widget sees the
    key — so without this, typing a space into a replicate name would start
    the video and Delete would remove the row being renamed. The tab disables
    those actions while an editor is live.
    """

    editing_started = Signal()
    editing_finished = Signal()

    def createEditor(
        self,
        parent: QWidget,
        option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> QWidget:
        """Open an editor and announce it."""
        editor = super().createEditor(parent, option, index)
        self.editing_started.emit()
        return editor

    def destroyEditor(self, editor: QWidget, index: QModelIndex | QPersistentModelIndex) -> None:
        """Close an editor and announce it."""
        super().destroyEditor(editor, index)
        self.editing_finished.emit()
