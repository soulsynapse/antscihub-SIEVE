"""Pipeline view: head and the room its steps will stand in."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from sieve.gui.primitives import Empty, View
from sieve.gui.primitives.view import PAD_X


class Pipeline(View):
    """Empty-state pipeline view; steps will fill the body."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Pipeline", parent)

        room = self.body()
        room.setContentsMargins(PAD_X, PAD_X, PAD_X, PAD_X)
        room.addStretch(1)
        room.addWidget(
            Empty("No steps yet", "Add the first one to start the chain.")
        )
        room.addStretch(1)
