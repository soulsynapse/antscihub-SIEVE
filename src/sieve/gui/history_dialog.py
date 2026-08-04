"""File ▸ History: pick a point to roll back to.

A list and two buttons, and that is the whole design. What a user is answering
here is "which of the things I did do I want to be before", so the entries say
the action and how long ago — the two facts that make a snapshot identifiable to
the person who caused it. A file name, a byte count, or a wall-clock timestamp
would each be more precise and none of them answers that question.

Newest first, because the mistake being undone is almost always recent; the
session starts further down are what the list is for on the other, rarer day.

The dialog does not restore anything. It answers `chosen()`, and the window
turns that into an undoable command — the dialog knowing how to mutate the
document would be a second write path past `commands.py`.
"""

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

#: Shown instead of the list when nothing has been written yet. Says why rather
#: than showing an empty box, because an empty history and a broken history look
#: identical from here and only one of them is fine.
EMPTY_NOTICE = "No history yet — it is written as you edit."

#: Marks the first snapshot of a session in the list. Session starts survive
#: retention that ordinary steps do not, so the list has to say which ones they
#: are or the survivors look arbitrary.
SESSION_MARK = "  ·  session start"


class HistoryDialog(QDialog):
    def __init__(self, snapshots: list[Snapshot], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Project History")
        self.resize(460, 380)

        self._snapshots = sorted(snapshots, key=lambda snapshot: snapshot.sequence, reverse=True)

        layout = QVBoxLayout(self)
        self._list = QListWidget(self)
        now = time.time()
        for snapshot in self._snapshots:
            label = f"{snapshot.text}  ·  {age_text(max(now - snapshot.written_at, 0.0))}"
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
        # Named as the action rather than "OK", and disabled with nothing to
        # act on: a button that says what it will do is the only warning this
        # dialog gives, and it does not need another because the restore is
        # itself undoable.
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
