"""The pipeline position: one card per step, scrolling under a fixed project card.

The list widget this replaces wore the platform's palette, which made the surface
the user spends the session on the one surface that does not look like SIEVE
(`adr/the-mockup-is-the-gui-end-state.md`, MOCKUP-MAP row "Settings is the right
pane"). What arrives with the shape is that a card can hold something: a list row
is a line of text, and a card is where the step's own knobs go.

**A card is the walk's target as well as its display.** Clicking one is the
pointer's Up/Down — it moves the same selection the rail's ticks and the step
position read, and nothing else — so there is still exactly one answer to where
the walk is and it is still the window's (`app.py`). The arrow is the pointer's
Right: the gesture that is two keys away from the card and has no pointer
spelling otherwise, and it points the way the track travels.

**The knobs are the generated form, not a table keyed by position.** The
referent's `_knobs_for` is a dict of thunks indexed by where the step stands,
because a mockup has no specs; copying that shape into the tree would be the
`tool_id` branch `adr/gui-knows-kinds-not-tools.md` forbids. So the caller builds
a `ParamForm` per node and hands it over — the same generator the step position
uses, from the same spec.

That makes two live forms over one node's parameters, and they are not
reconciled: `param_form.py` reads the document once and never reads it back, so
a value edited on the card is stale on the step position until the next move of
the walk redraws both. The rule that makes a rebuild the only way a new value
arrives is the session layer's, and a second writer here would be exactly what it
was written to prevent — so the divergence is left standing rather than papered
over with a reconciliation this module would own.

Not the chrome: `chrome.py` holds the palette and the sheet this pane wears.
Not the stage headers the referent draws between groups — what a stage *is* has
no derivation in the tree (`todo/a-stage-header-groups-by-nothing-the-tree-declares.md`).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from sieve.core.pipeline_model import Node
from sieve.gui.chrome import ACCENT, DIM, LINE, PANEL, TEXT, rgb, stack_stylesheet


class ChainCard(QWidget):
    """One card of the stack: panel fill, hairline edge, accent when current.

    It paints its own background rather than taking the stack's sheet, because
    the sheet's `.QWidget` selector reaches exactly `QWidget` and not a subclass
    (`chrome.py`) — which is the arrangement that keeps the scrollbars the
    platform's, and this is the side of it that has to paint.
    """

    def __init__(
        self,
        selected: bool,
        on_select: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._selected = selected
        self._on_select = on_select
        if on_select is not None:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    @property
    def selected(self) -> bool:
        """Whether this card is the one the walk is standing on."""
        return self._selected

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._on_select is None or event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        event.accept()
        self._on_select()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), PANEL)
        painter.setPen(QPen(ACCENT if self._selected else LINE, 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        painter.end()


def _title(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(f"color: {rgb(TEXT)};")
    return label


def _settings_button(on_open: Callable[[], None]) -> QToolButton:
    """Open this step's settings: the selection and the slide in one click."""
    button = QToolButton()
    button.setText("→")
    button.setAutoRaise(True)
    button.setToolTip("Open this step's settings")
    button.setStyleSheet(f"color: {rgb(DIM)}; border: 0;")
    button.clicked.connect(on_open)
    return button


def _fixed_card(title: str) -> ChainCard:
    """The card that stands above the stack and does not scroll with it."""
    card = ChainCard(selected=False)
    row = QHBoxLayout(card)
    row.setContentsMargins(8, 6, 8, 6)
    row.addWidget(_title(title))
    row.addStretch(1)
    return card


class PipelinePane(QWidget):
    """The whole position: the project it belongs to, then the steps in it.

    What stands above the stack is what the stack belongs to rather than a step
    in it, so the project card is outside the scroll area: scrolling to the foot
    of a long chain must not take away the answer to which project this is.
    """

    def __init__(
        self,
        project: str,
        steps: Sequence[tuple[Node, QWidget | None]],
        current: int,
        on_select: Callable[[int], None],
        on_open: Callable[[int], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setStyleSheet(stack_stylesheet())

        self.project_card = _fixed_card(f"project — {project}")
        self.cards = tuple(
            self._build_card(position, node, knobs, current, on_select, on_open)
            for position, (node, knobs) in enumerate(steps)
        )

        # Plain `QWidget`, so the stack's sheet reaches it: a subclass here would
        # leave the gaps between the cards on the platform's grey.
        column = QWidget()
        stack = QVBoxLayout(column)
        stack.setContentsMargins(6, 6, 6, 6)
        stack.setSpacing(18)
        for card in self.cards:
            stack.addWidget(card)
        stack.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidget(column)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 0)
        layout.setSpacing(6)
        layout.addWidget(self.project_card)
        layout.addWidget(scroll)

    @staticmethod
    def _build_card(
        position: int,
        node: Node,
        knobs: QWidget | None,
        current: int,
        on_select: Callable[[int], None],
        on_open: Callable[[int], None],
    ) -> ChainCard:
        card = ChainCard(selected=position == current, on_select=lambda: on_select(position))
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(4)

        head = QHBoxLayout()
        head.addWidget(_title(f"{position + 1}. {node.tool_id}"))
        head.addStretch(1)
        head.addWidget(_settings_button(lambda: on_open(position)))
        layout.addLayout(head)
        if knobs is not None:
            layout.addWidget(knobs)
        return card
