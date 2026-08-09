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

**A card carries a note where the mockup's carries a plot.** The one step whose
surface is drawn is the pinned one, and it is drawn under the canvas
(`pinned.py`) — so its card says where the surface went rather than drawing it a
second time, and every other card says nothing because there is nothing of its
step to draw here. Which sentence that is arrives as `pinned_note`, because the
slot has to be saying the same thing and one of the two would otherwise be a
copy going stale against the other. That is the whole of what a card holds
beside its knobs.

**The card's three verbs are the walk's, the pin's, and the chain's.** Removal
is the third and it is unlike the other two: selecting and pinning are view
state this module's caller holds, and the ✕ mutates the document. So the button
emits a position and nothing more — what a removal *means* to the chain is the
command layer's (`session/intents.RemoveNode`), and a stack that closed the
chain on screen over a document still holding the step would be the second
answer the fence exists to prevent.

Not the chrome: `chrome.py` holds the palette and the sheet this pane wears.
Not the stage headers the referent draws between groups — what a stage *is* has
no derivation in the tree (`todo/a-stage-header-groups-by-nothing-the-tree-declares.md`).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

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


@dataclass(frozen=True)
class Step:
    """One card's worth of what the window derived about a step.

    A record rather than a tuple because none of the three is guessable from
    its position, and none of them is derivable here: the knobs are generated
    from a spec this module is not given, and whether the chain would still
    read something without this step is a fact about the graph (`app.py`).
    """

    node: Node
    #: `None` where the tool is one this install does not have.
    knobs: QWidget | None
    #: Whether the ✕ is offered live. Offered disabled otherwise rather than
    #: left out, so the buttons hold their positions down the whole stack.
    removable: bool


class ChainCard(QWidget):
    """One card of a stack: panel fill, hairline edge, accent when current.

    It paints its own background rather than taking the stack's sheet, because
    the sheet's `.QWidget` selector reaches exactly `QWidget` and not a subclass
    (`chrome.py`) — which is the arrangement that keeps the scrollbars the
    platform's, and this is the side of it that has to paint.

    `on_open` is the pointer's Right, where the card has no arrow to carry it:
    the project position hands one over (`project_select.py`) and the pipeline
    position does not, because a step's arrow is a button on the card and a
    second gesture for the same verb would be a second thing to explain.
    """

    def __init__(
        self,
        selected: bool,
        on_select: Callable[[], None] | None = None,
        on_open: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._selected = selected
        self._on_select = on_select
        self._on_open = on_open
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

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if self._on_open is None or event.button() != Qt.MouseButton.LeftButton:
            super().mouseDoubleClickEvent(event)
            return
        event.accept()
        self._on_open()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), PANEL)
        painter.setPen(QPen(ACCENT if self._selected else LINE, 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        painter.end()


def title_label(text: str) -> QLabel:
    """A card's own name, in the colour a card's name is. Shared with `project_select.py`."""
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


def _pin_button(pinned: bool, on_pin: Callable[[], None]) -> QToolButton:
    """Take the slot under the canvas, or say this step already holds it.

    Disabled on the step that holds it rather than left out: one slot means
    pinning is a move and not a toggle, and a button that unpinned would leave
    the slot with nothing in it.
    """
    button = QToolButton()
    button.setText("◆" if pinned else "◇")
    button.setAutoRaise(True)
    button.setToolTip("Already pinned below the canvas" if pinned else "Pin below the canvas")
    button.setEnabled(not pinned)
    button.setStyleSheet(f"color: {rgb(ACCENT if pinned else DIM)}; border: 0;")
    button.clicked.connect(on_pin)
    return button


def _remove_button(removable: bool, on_remove: Callable[[], None]) -> QToolButton:
    """Drop this step: the chain closes over it rather than breaking at it.

    Disabled on the step nothing may take away rather than left off, for the
    pin button's reason one row up — a chain with nothing to read is not a
    shorter chain, which is what the tooltip says instead of the button being
    missing.
    """
    button = QToolButton()
    button.setText("✕")
    button.setAutoRaise(True)
    button.setEnabled(removable)
    button.setToolTip(
        "Remove this step — what read it reads past it"
        if removable
        else "The chain has to read something"
    )
    button.setStyleSheet(f"color: {rgb(DIM)}; border: 0;")
    button.clicked.connect(on_remove)
    return button


def note_label(text: str) -> QLabel:
    """A line about a card that is not its name. Shared with `project_select.py`."""
    label = QLabel(text)
    label.setStyleSheet(f"color: {rgb(DIM)};")
    return label


def fixed_card(title: str) -> ChainCard:
    """The card that stands above a stack and does not scroll with it."""
    card = ChainCard(selected=False)
    row = QHBoxLayout(card)
    row.setContentsMargins(8, 6, 8, 6)
    row.addWidget(title_label(title))
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
        steps: Sequence[Step],
        current: int,
        pinned: int | None,
        pinned_note: str,
        on_select: Callable[[int], None],
        on_open: Callable[[int], None],
        on_pin: Callable[[int], None],
        on_remove: Callable[[int], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setStyleSheet(stack_stylesheet())

        self.project_card = fixed_card(f"project — {project}")
        self.cards = tuple(
            self._build_card(
                position,
                step,
                current,
                pinned,
                pinned_note,
                on_select,
                on_open,
                on_pin,
                on_remove,
            )
            for position, step in enumerate(steps)
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
        step: Step,
        current: int,
        pinned: int | None,
        pinned_note: str,
        on_select: Callable[[int], None],
        on_open: Callable[[int], None],
        on_pin: Callable[[int], None],
        on_remove: Callable[[int], None],
    ) -> ChainCard:
        card = ChainCard(selected=position == current, on_select=lambda: on_select(position))
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(4)

        head = QHBoxLayout()
        head.addWidget(title_label(f"{position + 1}. {step.node.tool_id}"))
        head.addStretch(1)
        head.addWidget(_settings_button(lambda: on_open(position)))
        head.addWidget(_pin_button(position == pinned, lambda: on_pin(position)))
        head.addWidget(_remove_button(step.removable, lambda: on_remove(position)))
        layout.addLayout(head)
        if step.knobs is not None:
            layout.addWidget(step.knobs)
        if position == pinned:
            # Handed over rather than chosen here: which of the three sentences
            # the pinned step gets is `pinned.card_note`'s, and the slot under
            # the canvas is filled from the same answer.
            layout.addWidget(note_label(pinned_note))
        return card
