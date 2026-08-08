"""One tick per node, down the left edge, marking where the walk is.

Not which node that is — the rail is handed a position and never derives one.
Not the order the ticks are in — `walk.py` chooses that. This module only ever
lays them out.

The strip is one tick wide at every node count, including zero. A width driven
by `sizeHint` would collapse to nothing on an empty graph, and a rail that
changes width when it is rebuilt resizes the track beside it — which is enough
to interrupt a slide already in flight (`control.py`).
"""

from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

_TICK_SIZE = 8


class NodeRail(QWidget):
    def __init__(self, node_count: int, current: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(_TICK_SIZE)
        self._node_count = node_count

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        for index in range(node_count):
            layout.addWidget(self._build_tick(current=index == current))
        layout.addStretch(1)

    def tick_count(self) -> int:
        """How many ticks were drawn — one per node in the graph as read."""
        return self._node_count

    def _build_tick(self, current: bool) -> QWidget:
        tick = QWidget(self)
        tick.setFixedSize(_TICK_SIZE, _TICK_SIZE)
        # The current tick is the one thing on the rail that has to read
        # differently, and the stylesheet that will say how is not written yet.
        # A property Qt can select on costs nothing and keeps the fact where the
        # rail already knows it.
        tick.setProperty("current", current)
        return tick
