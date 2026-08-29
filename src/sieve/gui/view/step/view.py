"""Single-step view: header and the room its knobs will fill."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from sieve.gui.primitives import Empty, View
from sieve.gui.primitives.view import PAD_X


class Step(View):
    """Placeholder view for the step pane; content is filled by the pipeline."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Step", parent)

        room = self.body()
        room.setContentsMargins(PAD_X, PAD_X, PAD_X, PAD_X)
        room.addStretch(1)
        room.addWidget(
            Empty("No step open", "Open one from the pipeline to tune it here.")
        )
        room.addStretch(1)
