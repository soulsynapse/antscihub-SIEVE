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


_DERIVED = frozenset({Column.GROUP, Column.AREA})

_GEOMETRY_FIELDS: dict[Column, str] = {
    Column.X: "x",
    Column.Y: "y",
    Column.WIDTH: "width",
    Column.HEIGHT: "height",
}


class ReplicateTableModel(QAbstractTableModel):
    def __init__(
        self, document: ReplicateDocument, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._document = document
        document.structure_changed.connect(self._on_structure_changed)
        document.replicate_changed.connect(self._on_replicate_changed)
        document.grouping_changed.connect(self._on_grouping_changed)

    def rowCount(
        self, parent: QModelIndex | QPersistentModelIndex | None = None
    ) -> int:
        if parent is not None and parent.isValid():
            return 0
        return len(self._document)

    def columnCount(
        self, parent: QModelIndex | QPersistentModelIndex | None = None
    ) -> int:
        if parent is not None and parent.isValid():
            return 0
        return len(Column)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
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
        if not index.isValid() or index.row() >= len(self._document):
            return None
        replicate = self._document.at(index.row())
        column = Column(index.column())
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if column is Column.NAME:
                return replicate.name
            if column is Column.GROUP:
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
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        row = index.row()
        column = Column(index.column())
        if column is Column.NAME:
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
            return False
        return True

    def flags(self, index: QModelIndex | QPersistentModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if Column(index.column()) in _DERIVED:
            return base
        return base | Qt.ItemFlag.ItemIsEditable

    def _on_grouping_changed(self) -> None:
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
    editing_started = Signal(str)
    editing_finished = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._keys: dict[QWidget, str] = {}
        self._opened = 0

    def createEditor(
        self,
        parent: QWidget,
        option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> QWidget:
        editor = super().createEditor(parent, option, index)
        self._opened += 1
        key = f"cell:{self._opened}:{index.row()}.{index.column()}"
        self._keys[editor] = key
        self.editing_started.emit(key)
        return editor

    def destroyEditor(
        self, editor: QWidget, index: QModelIndex | QPersistentModelIndex
    ) -> None:
        key = self._keys.pop(editor, None)
        if key is not None:
            self.editing_finished.emit(key)
        super().destroyEditor(editor, index)
