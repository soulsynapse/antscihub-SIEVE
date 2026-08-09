"""How one node is captioned: its place in the walk, and the tool it applies.

The box keeps the `Node` it was built from rather than only the text it drew,
so that a caller asking what is on screen gets the document's own value back
instead of parsing a label it wrote itself.

It was also the row of the pipeline position's list, until 09.1 made that
position a stack of cards (`chain_stack.py`) — what is left here is the caption
at the head of the step position, which is the one place a node is stated
without also being offered.
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from sieve.core.pipeline_model import Node


class NodeBox(QWidget):
    def __init__(self, position: int, node: Node, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.node = node

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(QLabel(f"{position}. {node.tool_id}"))
