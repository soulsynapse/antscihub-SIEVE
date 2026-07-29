from __future__ import annotations

import time

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from sieve.gui.history import Snapshot, age_text


EMPTY_NOTICE = "No history yet — it is written as you edit."


SESSION_MARK = "  ·  session start"


class HistoryDialog(QDialog):
    def __init__(
        self, snapshots: list[Snapshot], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Project History")
        self.resize(460, 380)
        self._snapshots = sorted(
            snapshots, key=lambda snapshot: snapshot.sequence, reverse=True
        )
        layout = QVBoxLayout(self)
        self._list = QListWidget(self)
        now = time.time()
        for snapshot in self._snapshots:
            label = (
                f"{snapshot.text}  ·  {age_text(max(now - snapshot.written_at, 0.0))}"
            )
            if snapshot.session_start:
                label += SESSION_MARK
            self._list.addItem(QListWidgetItem(label))
        if self._snapshots:
            self._list.setCurrentRow(0)
            layout.addWidget(self._list)
        else:
            notice = QLabel(EMPTY_NOTICE, self)
            notice.setAlignment(Qt.AlignmentFlag.AlignCenter)
            notice.setWordWrap(True)
            layout.addWidget(notice)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel, self)
        self._restore = QPushButton("Restore", self)
        self._restore.setEnabled(bool(self._snapshots))
        self._restore.setDefault(True)
        buttons.addButton(self._restore, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._list.itemDoubleClicked.connect(self._on_double_clicked)

    @Slot(QListWidgetItem)
    def _on_double_clicked(self, item: QListWidgetItem) -> None:
        del item
        self.accept()

    def chosen(self) -> Snapshot | None:
        row = self._list.currentRow()
        if not 0 <= row < len(self._snapshots):
            return None
        return self._snapshots[row]
