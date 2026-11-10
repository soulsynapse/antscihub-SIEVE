"""The shapes' table: one row a shape, in the editor's order, its name edited in place and its
selection the editor's. `refused` carries the reason a rename was refused, the row it was typed in
then marked until the shapes next change."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem

COLUMNS = ("Name", "Kind", "Centre", "Size")
MARKED = QColor(110, 40, 40)


def size_text(s):
    if s.kind == "circle":
        return f"r {s.r:.1f}"
    if s.kind == "square":
        return f"{s.w:.1f}"
    if s.kind == "rectangle":
        return f"{s.w:.1f} × {s.h:.1f}"
    x0, y0, x1, y1 = s.box()
    return f"{x1 - x0:.1f} × {y1 - y0:.1f} box"


def row_texts(s):
    kind = f"{s.kind} · {s.group}" if s.group else s.kind
    return (s.name, kind, f"{s.centre[0]:.1f}, {s.centre[1]:.1f}", size_text(s))


class ShapeTable(QTableWidget):
    refused = Signal(str)

    def __init__(self, editor, parent=None):
        super().__init__(0, len(COLUMNS), parent)
        self.editor = editor
        self.marked = None    # (name, the shapes when it was refused)
        self._shown = None
        self.setHorizontalHeaderLabels(COLUMNS)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed)
        self.itemSelectionChanged.connect(self._picked)
        self.itemChanged.connect(self._edited)

    def name_at(self, row):
        return self.item(row, 0).data(Qt.ItemDataRole.UserRole)

    def refresh(self):
        """Shows the editor's shapes and selection; a no-op when neither changed, so a cell being
        edited is not torn down by a cursor's move over the frame."""
        shapes = tuple(self.editor.shapes)
        if self.marked is not None and self.marked[1] != shapes:
            self.marked = None
        now = (shapes, self.editor.selected, self.marked)
        if now == self._shown:
            return
        self._shown = now
        self.blockSignals(True)
        self.setRowCount(len(shapes))
        marked = self.marked[0] if self.marked is not None else None
        for row, s in enumerate(shapes):
            for col, text in enumerate(row_texts(s)):
                item = self.item(row, col)
                if item is None:
                    item = QTableWidgetItem()
                    self.setItem(row, col, item)
                item.setText(text)
                item.setData(Qt.ItemDataRole.UserRole, s.name)
                flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                item.setFlags(flags | Qt.ItemFlag.ItemIsEditable if col == 0 else flags)
                item.setBackground(QBrush(MARKED) if s.name == marked else QBrush())
        rows = [r for r, s in enumerate(shapes) if s.name == self.editor.selected]
        if rows:
            self.selectRow(rows[0])
        else:
            self.clearSelection()
        self.blockSignals(False)

    def _picked(self):
        rows = {i.row() for i in self.selectedItems()}
        name = self.name_at(rows.pop()) if rows else None
        if name != self.editor.selected:
            self.editor.select(name)

    def _edited(self, item):
        if item.column() != 0:
            return
        old, new = item.data(Qt.ItemDataRole.UserRole), item.text()
        if self.editor.rename(old, new):
            self.marked = None
            return
        self.marked = (old, tuple(self.editor.shapes))
        self.refused.emit(f"{new!r} is already a shape's name" if new else "a name cannot be empty")
        self.refresh()
