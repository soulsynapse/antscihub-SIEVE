"""How one node is drawn, and how the ordered list of them is built.

A `NodeBox` shows what the document holds about a node and nothing else: its
place in the walk, and the tool it applies. Its parameters are not here — the
generator that turns a tool's presentation stereotypes into widgets is the next
item (`PLAN.md`, Phase 7), and a hand-written parameter row would be the
per-tool GUI code that generator exists to make unnecessary.

The box keeps the `Node` it was built from rather than only the text it drew,
so that a caller asking what is on screen gets the document's own value back
instead of parsing a label it wrote itself.
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from sieve.core.pipeline_model import Node


class NodeBox(QWidget):
    def __init__(self, position: int, node: Node, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.node = node

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(QLabel(f"{position}. {node.tool_id}"))


def build_node_list(nodes: Sequence[Node], current: int) -> QListWidget:
    """The nodes in walk order, with `current` selected.

    Selection rather than a style of its own: it is the same fact the rail's
    current tick carries, and a list that painted its own version of it would be
    a second place to fix when the walk moves.
    """
    listing = QListWidget()
    for position, node in enumerate(nodes):
        box = NodeBox(position + 1, node)
        item = QListWidgetItem(listing)
        item.setSizeHint(box.sizeHint())
        listing.addItem(item)
        listing.setItemWidget(item, box)
    if 0 <= current < len(nodes):
        listing.setCurrentRow(current)
    return listing
