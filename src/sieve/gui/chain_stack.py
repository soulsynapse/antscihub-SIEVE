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

**A gap is a position, and `AddBox` is what stands in it.** The question ADD
STEP asks first is *which gap*, and the gaps are what this stack is already
drawing — so the affordance is a card in the chain rather than a panel in the
chrome that would have to name the position in words
(`adr/a-position-is-asked-for-in-the-chain.md`). It never writes: the box is a
picker, the offer it renders is a shortlist the caller computed
(`core/tool_registry.offered_tools`), and one mutation is issued when an offer
is taken. That is what makes esc free and what keeps this module ignorant of
what a tool is — the names it draws are strings, and what comes back is which
of them was clicked.

Not the chrome: `chrome.py` holds the palette and the sheet this pane wears.
Not the stage headers the referent draws between groups — what a stage *is* has
no derivation in the tree (`todo/a-stage-header-groups-by-nothing-the-tree-declares.md`).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import partial
from math import ceil

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFontMetricsF,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from sieve.core.pipeline_model import Node
from sieve.gui.chrome import (
    ACCENT,
    DIM,
    LINE,
    PANEL,
    STACK_BG,
    TEXT,
    chrome_button,
    rgb,
    stack_stylesheet,
)


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
    #: The positions in the same stack whose output this step reads, in the
    #: document's own order. Positions rather than node ids because the picture
    #: is drawn between cards and the caller is the one holding the walk that
    #: numbered them. Required rather than defaulted to nothing: a stack whose
    #: caller forgot would draw a chain of unconnected cards and look finished.
    reads: tuple[int, ...]


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


# ---------------------------------------------------------------------------
# The outputs reaching down: the chain's edges, drawn under the cards.
#
# VISION's scene is a picture and not a diagram — an output leaves the bottom of
# the card that made it and arrives at the top of the card that reads it, and
# where the step in between reads neither, the line passes *behind* that card
# rather than around it. Occlusion is the whole of that: the cards paint an
# opaque panel, the column paints before its children, so a line crossing a card
# is hidden for exactly as long as it is not that card's business. Routing a
# skip around the stack in a gutter would say the opposite — that the output
# left the chain and came back.
#
# The lines are geometry read off the cards at paint time rather than anything
# stored, because the stack is rebuilt on every move of the walk; an edge layer
# holding its own coordinates would draw the previous selection's stack.
#
# A port is named at an arrowhead only where the destination has more than one
# input, which in this stack is the output card and nothing else: schema v1 gives
# an edge no port and refuses two edges into one node, so a name over a step's
# arrowhead would be a distinction the document cannot make. The card's inputs
# are not the document's — they are the ticks, derived
# (`adr/the-output-card-is-a-picture-of-the-write-list.md`) — and a product is
# what they are named by.

#: The trunk's inset from a card's left edge, and the step out to the next lane.
EDGE_STUB = 16.0
EDGE_LANE = 34.0
ARROW_WIDTH = 4.0
ARROW_HEIGHT = 6.0
#: Clear of the arrowhead's own shoulder, so the name reads as beside the line
#: rather than as something the head is part of.
PORT_GAP = 8.0
#: How far the name's baseline sits above the card it lands on.
PORT_RISE = 2.0


def edge_lanes(edges: Sequence[tuple[int, int]]) -> dict[tuple[int, int], int]:
    """One x per edge, so every line is vertical and none is two lines' worth.

    An edge that changed x while it was hidden would come out the far side as
    something the eye has no reason to join to what went in. Vertical is what
    makes the occlusion read as one line behind a card rather than as two stubs,
    so the offset is spent on lanes rather than on the descent: an edge holds
    its lane the whole way down, and only edges whose spans overlap need
    different ones. Shortest span first hands the trunk to the steps that read
    the one above them, which is most of the chain.
    """

    def overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
        return a[0] < b[1] and b[0] < a[1]

    lanes: dict[tuple[int, int], int] = {}
    for edge in sorted(edges, key=lambda e: (e[1] - e[0], e[0])):
        taken = {lane for other, lane in lanes.items() if overlaps(edge, other)}
        lane = 0
        while lane in taken:
            lane += 1
        lanes[edge] = lane
    return lanes


def lane_x(left: float, lane: int) -> float:
    """Where `lane` runs, beside a card whose left edge is at `left`."""
    return left + EDGE_STUB + EDGE_LANE * lane


def _stroke(colour: QColor, dashed: bool) -> QPen:
    """The pen an edge is drawn with. Dashed is the accent's, and means unwritten."""
    pen = QPen(colour, 1.0)
    if dashed:
        pen.setStyle(Qt.PenStyle.DashLine)
    return pen


def arrowhead(end: QPointF) -> QPolygonF:
    """The head that lands on `end`, apex last.

    Always a descent: the two shoulders are above the point, and there is no
    variant that points any other way, because every edge in this stack runs
    from a card to one below it.
    """
    return QPolygonF(
        [
            QPointF(end.x() - ARROW_WIDTH, end.y() - ARROW_HEIGHT),
            QPointF(end.x() + ARROW_WIDTH, end.y() - ARROW_HEIGHT),
            QPointF(end.x(), end.y()),
        ]
    )


def port_label_origin(end: QPointF, lift: float = 0.0) -> QPointF:
    """The baseline the product's name is written from, beside the head at `end`.

    Right of the lane and in the gap above the card, which is the only space the
    name can take without standing on either: a name centred over the arrowhead
    would sit in the lane the next edge along may be using, and one inside the
    card would read as something the card says about itself.

    `lift` is what makes more than one of them readable. Every arrowhead into a
    card lands on the same top edge, so names sharing that baseline run into each
    other the moment two of them are wider than the lane pitch — which every
    product name is. Each name after the first is raised clear of the one below,
    up its own lane, so it still reads as belonging to the line it is written
    beside.
    """
    return QPointF(end.x() + ARROW_WIDTH + PORT_GAP, end.y() - PORT_RISE - lift)


# ---------------------------------------------------------------------------
# The branch one card makes: a numbered square per region, in the gap.
#
# A step with one output needs nothing here — the arrow out of its card is the
# whole of it. A step that cuts a region per dish branches at the card and not
# further down, so the row of squares stands in the gap between that card and
# its reader: anywhere else and it would be a legend rather than the branch.
# Every arrow into a square leaves the same run out of the card, because that
# card made all of them, and the one arrow that continues down leaves the square
# the user selected — what the stack below is drawn for is that region, and the
# others are the same chain, unwalked.
#
# What a region *is* is not this module's to say, and the fan holds none of it:
# `Fan` carries names the caller read off the document and an index into them.
# The tree's regions are the project's replicates, each one a per-replicate
# override of this step's box (`core/pipeline_model.Replicate`), and a widget
# holding its own list would be a second home for that value.

#: The square, the pitch between two of them, and the run's clearance from the
#: card above and the card below.
TILE = 24.0
TILE_GAP = 12.0
FAN_STUB = 12.0
#: Tall enough for a tile with the stub above and below it.
FAN_HEIGHT = 56
#: What a line describing an unwalked region is held back to. Alpha rather than a
#: second colour so the two weights are visibly the same line.
UNLIT_ALPHA = 150


@dataclass(frozen=True)
class Fan:
    """The regions one card's step cuts, and which of them the walk is on.

    `on_select` rides here rather than beside it on the pane, so a pane with no
    fan cannot be handed a callback for regions it has none of.
    """

    #: The position whose card the branch leaves.
    position: int
    #: One name per region, in the document's order. Drawn as its ordinal — the
    #: name is what the caller identified it by, and the square is too small to
    #: carry one.
    regions: tuple[str, ...]
    selected: int
    on_select: Callable[[int], None]


class RegionFan(QWidget):
    """One numbered square per region, left-aligned on the trunk.

    It paints its squares and nothing else. The lines are `ChainColumn`'s, drawn
    before its children, so they arrive behind these tiles the way an edge
    arrives behind a card.
    """

    def __init__(
        self, fan: Fan, reader: int, trunk_x: float, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.fan = fan
        #: The position the continuing arrow lands on: the fan hangs in that gap.
        self.reader = reader
        self._trunk_x = trunk_x
        self.setFixedHeight(FAN_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # The squares carry ordinals because a 24px tile holds nothing longer,
        # and the regions are named — so the names arrive here, numbered, rather
        # than being dropped on the way and leaving the count as the whole of
        # what the surface knows about them.
        self.setToolTip(" · ".join(f"{index + 1} {name}" for index, name in enumerate(fan.regions)))

    @property
    def position(self) -> int:
        """The position whose card this branch leaves."""
        return self.fan.position

    @property
    def selected(self) -> int:
        """Which region the stack below is drawn for."""
        return self.fan.selected

    def tile_rects(self) -> list[QRectF]:
        """One square per region, the first on the trunk and the rest to its right.

        Left-aligned off the trunk rather than centred in the row: a centred row
        sits wherever the count and the pane's width put it, and only a diagonal
        could reach it from the lane the chain descends in.
        """
        top = (self.height() - TILE) / 2.0
        left = self._trunk_x - TILE / 2.0
        return [
            QRectF(left + index * (TILE + TILE_GAP), top, TILE, TILE)
            for index in range(len(self.fan.regions))
        ]

    def tile_at(self, pos: QPointF) -> int | None:
        """Which square is under `pos`, with the slack a 24px target wants."""
        for index, tile in enumerate(self.tile_rects()):
            if tile.adjusted(-4, -4, 4, 4).contains(pos):
                return index
        return None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        index = self.tile_at(event.position())
        if index is None:
            super().mousePressEvent(event)
            return
        event.accept()
        self.fan.on_select(index)

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        for index, tile in enumerate(self.tile_rects()):
            chosen = index == self.fan.selected
            painter.fillRect(tile, PANEL)
            painter.setPen(QPen(ACCENT if chosen else LINE, 1.6 if chosen else 1.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(tile)
            painter.setPen(QPen(TEXT if chosen else DIM))
            painter.drawText(tile, Qt.AlignmentFlag.AlignCenter, str(index + 1))
        painter.end()


@dataclass(frozen=True)
class FannedEdge:
    """Where the branch out of a fanned card runs, in the column's coordinates.

    Segments rather than a painted result, for `edge_line`'s reason: what the
    picture claims is geometry, and geometry is the thing a test can read.
    """

    #: Card bottom down to the run.
    stem: tuple[QPointF, QPointF]
    #: The run itself, out to the last square.
    bus: tuple[QPointF, QPointF]
    #: The run down into each square's top, in the regions' own order.
    drops: tuple[tuple[QPointF, QPointF], ...]
    #: Selected square's bottom, back onto the trunk, and down onto the reader.
    rejoin: tuple[QPointF, ...]


# ---------------------------------------------------------------------------
# What leaves the chain: a card at the foot of it, drawn and never modeled.
#
# The write list is that card's param, and a ticked product *is* an edge into it
# — derived on every redraw rather than held, so the picture cannot come to
# disagree with what the document says the run keeps. No output node enters the
# tool contract for this and writing stays the run's own act
# (`adr/the-output-card-is-a-picture-of-the-write-list.md`): a node whose inputs
# were the ticks would make every tick a graph mutation, and a tick may not reach
# a cache key.
#
# It is the one card in the stack with more than one input, so it is the one
# whose arrowheads are named — by product, which is the word the user ticked.


@dataclass(frozen=True)
class Write:
    """One product the run keeps, as the picture draws it.

    A position rather than a node id, for `Step.reads`' reason: the line is drawn
    between cards and the caller is the one holding the walk that numbered them.
    """

    position: int
    #: What the arrowhead is named. The product the step's own parameters select,
    #: in the tool's words — derived by the caller from the same document the
    #: form's ticks are read from (`save_screen.kept_products`).
    product: str


@dataclass(frozen=True)
class Outputs:
    """The card at the foot of the chain, and the writes reaching into it.

    `on_open` rides here rather than beside it on the pane for `Fan`'s reason: a
    pane drawing no output card cannot be handed the way into a form it has no
    card to open.
    """

    writes: tuple[Write, ...]
    on_open: Callable[[], None]


# ---------------------------------------------------------------------------
# The box in the gap: which position, and what could stand in it.
#
# It is a `ChainCard` so the column's edge painters reach it by the one path they
# reach everything — a geometry read off `cards[slot]` — and so it wears the fill
# and the numbering the chain wears. Dashed for the same reason its edges are:
# nothing has been written, and the solid chain around it is still what the
# document holds.
#
# It builds none of its own contents. The offer is the *gap's*, computed above
# this module and handed down as names; which of them is lit is the window's
# state, so the box is rebuilt as the site moves rather than holding a selection
# that could disagree with it. The walk cannot stand on it, because there is no
# step there to stand on.

#: How many offers stand in a row before the next one wraps.
OFFER_COLUMNS = 3
#: What a box with nothing to offer says where the offer would be. Most gaps on
#: today's shelf are in this state, so it is a sentence the surface owes rather
#: than a blank.
EMPTY_OFFER_NOTE = "nothing on the shelf declares it could stand here"
KEY_NOTE = "↑↓ move the box · ←→ the offer · enter takes it · esc cancels"


@dataclass(frozen=True)
class Adding:
    """The box standing in a gap: which gap, what is offered there, which is lit.

    `on_take` rides here rather than beside it on the pane for `Fan`'s reason: a
    pane with no box open cannot be handed the way to fill one. It is given the
    *position* in the offer rather than the name, so nothing about a tool makes
    the round trip through a widget.
    """

    #: The position whose card the gap is under.
    site: int
    #: What could stand there, in the order the caller scored them. Empty is a
    #: real answer and the common one (`core/tool_registry.offered_tools`).
    offer: tuple[str, ...]
    lit: int
    on_take: Callable[[int], None]


def _offer_button(name: str, lit: bool, on_take: Callable[[], None]) -> QPushButton:
    """One offer, in the chrome's dress, with the lit one wearing the accent."""
    button = chrome_button(name, f"Put {name} in this gap")
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    # Its own width rather than a share of the box's: the offering is a set of
    # names, and a grid of equal bars would read as a set of slots.
    button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
    if lit:
        button.setStyleSheet(
            button.styleSheet()
            + f"QPushButton {{ border-color: {rgb(ACCENT)}; color: {rgb(ACCENT)}; }}"
        )
    button.clicked.connect(on_take)
    return button


class AddBox(ChainCard):
    """The step that is not one yet, standing in the gap it would fill."""

    def __init__(
        self, adding: Adding, number: int, note: str, parent: QWidget | None = None
    ) -> None:
        super().__init__(selected=False, parent=parent)
        self.site = adding.site
        #: The number the step would carry, which is the gap's own place in the
        #: chain — so the box reads as the position rather than as a panel
        #: about one.
        self.number = number
        self.offer = adding.offer
        self.lit = adding.lit
        #: What the splice would do, in the names the picture cannot show until
        #: it happens.
        self.note = note
        #: What stands where the offer would, when there is none. Empty string
        #: where there is one, so the two are never both on screen.
        self.offer_note = "" if adding.offer else EMPTY_OFFER_NOTE

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(4)

        head = QHBoxLayout()
        title = title_label(f"{number}. new step")
        title.setStyleSheet(f"color: {rgb(ACCENT)};")
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(note_label(note))
        layout.addLayout(head)

        self.offer_buttons = tuple(
            _offer_button(name, position == adding.lit, partial(adding.on_take, position))
            for position, name in enumerate(adding.offer)
        )
        if self.offer_buttons:
            grid = QGridLayout()
            grid.setContentsMargins(0, 2, 0, 0)
            grid.setSpacing(4)
            for position, button in enumerate(self.offer_buttons):
                grid.addWidget(button, position // OFFER_COLUMNS, position % OFFER_COLUMNS)
            grid.setColumnStretch(OFFER_COLUMNS, 1)
            layout.addLayout(grid)
        else:
            layout.addWidget(note_label(self.offer_note))
        layout.addWidget(note_label(KEY_NOTE))

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        tint = QColor(ACCENT)
        tint.setAlpha(14)
        painter.fillRect(self.rect(), PANEL)
        painter.fillRect(self.rect(), tint)
        pen = QPen(ACCENT, 1)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        painter.end()


class ChainColumn(QWidget):
    """The stack's column, with the chain's edges drawn under its cards.

    It fills its own background: the stack's sheet reaches plain `QWidget` and
    not a subclass — deliberately, so the scrollbars keep the platform's
    (`chrome.py`) — and a column that inherited nothing would leave the edges on
    the platform's grey.

    `cards` and `fan` are set by the caller after both are in the layout,
    because what this paints is where they landed and it has no part in putting
    them there.
    """

    def __init__(
        self,
        edges: Sequence[tuple[int, int]],
        labels: Mapping[tuple[int, int], str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        # Only the edges that descend. A walk that puts a producer below its
        # reader has a cycle in it, which the window still has to draw
        # (`walk.py`) and which no downward line describes.
        self.edges = tuple(edge for edge in edges if edge[0] < edge[1])
        self._lanes = edge_lanes(self.edges)
        fan_in = Counter(dst for _src, dst in self.edges)
        # A name only where the destination has a choice to name: one line into a
        # card came from the one place it could have, and a label on it would be
        # a word the picture did not need.
        self._labels = {
            edge: text
            for edge, text in (labels or {}).items()
            if edge in self._lanes and fan_in[edge[1]] > 1
        }
        # Measured once, here, because the caller reserves room for these lifts in
        # the layout (`label_headroom`) and a box measured against a second
        # reading would describe a name the gap was not opened for. The stack is
        # rebuilt on every move of the walk, so a font that changes is picked up
        # by the next one.
        self._metrics = QFontMetricsF(self.font())
        # A line apart, by the font's own answer to how far apart two lines are:
        # stacked names are set the way any two lines of text are, and a gap
        # chosen here would be a second answer to that question. Outer lanes ride
        # higher — a lane's number is how far back up the stack its edge reached,
        # so lifting in that order puts the names in the same top-to-bottom order
        # as the cards they came from.
        self._lifts = {
            edge: rank * self._metrics.lineSpacing()
            for rank, edge in enumerate(sorted(self._labels, key=lambda e: self._lanes[e]))
        }
        self.cards: tuple[ChainCard, ...] = ()
        self.fan: RegionFan | None = None
        self._box: tuple[int, int, tuple[int, ...]] | None = None

    def hold_box(self, slot: int, site: int, readers: Sequence[int]) -> None:
        """Give the box at `cards[slot]` the lanes the edges it interrupts had.

        Its lanes are borrowed rather than assigned, so the picture does not
        shift sideways when the box opens: an edge that moved to enter the box
        would be saying the chain had been rerouted rather than interrupted.

        Called by the caller once the box is in the layout and in `cards`, for
        the reason `cards` itself is.
        """
        self._box = (slot, site, tuple(readers))
        trunk = min((lane for (src, _), lane in self._lanes.items() if src == site), default=0)
        self._lanes[(site, slot)] = trunk
        for reader in readers:
            self._lanes[(slot, reader)] = self._lanes.get((site, reader), trunk)

    @property
    def box_slot(self) -> int | None:
        """Which of `cards` the box is, or `None` while none is open."""
        return None if self._box is None else self._box[0]

    def provisional_edges(self) -> tuple[tuple[int, int], ...]:
        """The edges the box would be spliced onto, which are the ones drawn dashed.

        Out of the gap's step into the box, and out of the box into whatever read
        past the gap — `Step.reads` inverted, and the picture of what taking an
        offer would write.
        """
        if self._box is None:
            return ()
        slot, site, readers = self._box
        return ((site, slot),) + tuple((slot, reader) for reader in readers)

    def painted_edges(self) -> tuple[tuple[int, int], ...]:
        """The chain's own edges that are still drawn solid while a box stands in it.

        An edge the box interrupts is not one of them: what is on screen has to
        be one chain, and a solid line running past the box beside the dashed
        pair replacing it would be the picture saying both. Only the edges into
        *steps* are interrupted — a write into the output card names its node
        and survives the splice untouched
        (`adr/the-output-card-is-a-picture-of-the-write-list.md`), so a box that
        dimmed it would be claiming a rewiring the mutation does not make.
        """
        if self._box is None:
            return self.edges
        _slot, site, readers = self._box
        interrupted = {(site, reader) for reader in readers}
        return tuple(edge for edge in self.edges if edge not in interrupted)

    def port_labels(self) -> dict[tuple[int, int], str]:
        """The product written beside each arrowhead that is named at all."""
        return dict(self._labels)

    def label_rect(self, src: int, dst: int) -> QRectF:
        """The box that edge's name occupies, for edges that have one.

        Advance width rather than the glyphs' own bounding box: what has to not
        be another name's is the run the pen makes, and the ink of a name with no
        descender stops short of where the next one may start.
        """
        origin = port_label_origin(self.edge_line(src, dst)[1], self._lifts[(src, dst)])
        return QRectF(
            origin.x(),
            origin.y() - self._metrics.ascent(),
            self._metrics.horizontalAdvance(self._labels[(src, dst)]),
            self._metrics.ascent() + self._metrics.descent(),
        )

    def label_headroom(self) -> float:
        """How far above the ordinary gap the highest of a card's names reaches.

        The gap the rest of the stack leaves between cards is one name tall, so a
        card whose names are stacked needs the layout to open it further — a
        lifted name is drawn before the cards are and would otherwise be painted
        under the one above it, which is the same as not being drawn.
        """
        return max(self._lifts.values(), default=0.0)

    def edge_line(self, src: int, dst: int) -> tuple[QPointF, QPointF]:
        """Where the edge from `src` to `dst` starts and ends, in this widget."""
        above, below = self.cards[src].geometry(), self.cards[dst].geometry()
        x = lane_x(above.left(), self._lanes[(src, dst)])
        return QPointF(x, above.bottom() + 1), QPointF(x, below.top())

    def lane_of(self, src: int, dst: int) -> int:
        """Which lane that edge runs in — the fan reads it to stand on the trunk."""
        return self._lanes[(src, dst)]

    def fan_tiles(self) -> list[QRectF]:
        """The fan's squares in this widget's coordinates, where the lines are."""
        assert self.fan is not None
        origin = self.fan.geometry().topLeft()
        return [tile.translated(origin) for tile in self.fan.tile_rects()]

    def fanned_edge(self, dst: int | None = None) -> FannedEdge:
        """Out of the fanned card into every region, and on out of the one selected.

        One run across the gap and a vertical drop off it into each square: what
        the picture has to say is that these all came from that card, and a
        shared segment says it while every arrowhead stays a descent, which is
        what an arrowhead means everywhere else in the stack. The way out
        mirrors it back onto the trunk, so the lane the rest of the stack is
        drawn in survives the branch.

        `dst` is where the way out lands, and it is the fan's reader unless a
        box is standing in the gap the fan hangs in — the branch itself is the
        card's and is not provisional, but where it continues to is exactly what
        the box is asking about.
        """
        assert self.fan is not None
        src = self.fan.position
        dst = self.fan.reader if dst is None else dst
        above, below = self.cards[src].geometry(), self.cards[dst].geometry()
        tiles = self.fan_tiles()
        x = lane_x(above.left(), self._lanes[(src, dst)])
        bus_y = above.bottom() + 1 + FAN_STUB
        chosen = tiles[self.fan.selected]
        rejoin_y = below.top() - FAN_STUB
        return FannedEdge(
            stem=(QPointF(x, above.bottom() + 1), QPointF(x, bus_y)),
            bus=(QPointF(x, bus_y), QPointF(tiles[-1].center().x(), bus_y)),
            drops=tuple(
                (QPointF(tile.center().x(), bus_y), QPointF(tile.center().x(), tile.top()))
                for tile in tiles
            ),
            rejoin=(
                QPointF(chosen.center().x(), chosen.bottom()),
                QPointF(chosen.center().x(), rejoin_y),
                QPointF(x, rejoin_y),
                QPointF(x, below.top()),
            ),
        )

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), STACK_BG)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        fanned = None if self.fan is None else (self.fan.position, self.fan.reader)
        for src, dst in self.painted_edges():
            if (src, dst) == fanned:
                self._paint_fanned_edge(painter)
            else:
                self._paint_edge(painter, src, dst)
        self._paint_provisional(painter)
        painter.end()

    def _paint_provisional(self, painter: QPainter) -> None:
        """The edges the box would be spliced onto, dashed because it is not.

        Drawn after the chain's own, so the pair replacing an interrupted edge
        lands over the cards the interruption exposed rather than under them.
        """
        if self._box is None:
            return
        slot, site, readers = self._box
        if self.fan is not None and site == self.fan.position:
            self._paint_fanned_edge(painter, slot, provisional=True)
        else:
            self._paint_edge(painter, site, slot, dashed=True)
        for reader in readers:
            self._paint_edge(painter, slot, reader, dashed=True)

    def _paint_fanned_edge(
        self, painter: QPainter, dst: int | None = None, provisional: bool = False
    ) -> None:
        """The branch, with everything but the selected region's reach held back.

        The run is drawn twice so the reach to the selected square is at the
        chain's own weight and the rest of it is not, the way the drops off it
        are: what is dimmed is the part of the picture describing a chain the
        walk is not on.

        `provisional` dashes the way out and nothing else. The branch is the
        card's own and is real whether or not a box is open; what is not yet
        written is where the selected region's chain continues to, which is the
        one segment the box is standing in the way of.
        """
        assert self.fan is not None
        edge = self.fanned_edge(dst)
        unlit = QColor(LINE)
        unlit.setAlpha(UNLIT_ALPHA)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        painter.setPen(QPen(LINE, 1.0))
        painter.drawLine(*edge.stem)
        painter.setPen(QPen(unlit, 1.0))
        painter.drawLine(*edge.bus)
        painter.setPen(QPen(LINE, 1.0))
        painter.drawLine(edge.bus[0], QPointF(edge.rejoin[0].x(), edge.bus[0].y()))

        for index, drop in enumerate(edge.drops):
            chosen = index == self.fan.selected
            colour = LINE if chosen else unlit
            painter.setPen(QPen(colour, 1.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawLine(*drop)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(colour)
            painter.drawPolygon(arrowhead(drop[1]))

        painter.setPen(_stroke(LINE if not provisional else ACCENT, provisional))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for start, end in zip(edge.rejoin, edge.rejoin[1:], strict=False):
            painter.drawLine(start, end)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(ACCENT if provisional else LINE)
        painter.drawPolygon(arrowhead(edge.rejoin[-1]))

    def _paint_edge(self, painter: QPainter, src: int, dst: int, dashed: bool = False) -> None:
        start, end = self.edge_line(src, dst)
        colour = ACCENT if dashed else LINE
        painter.setPen(_stroke(colour, dashed))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(start, end)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(colour)
        painter.drawPolygon(arrowhead(end))
        label = self._labels.get((src, dst))
        if label is not None:
            painter.setPen(QPen(DIM))
            painter.drawText(port_label_origin(end, self._lifts[(src, dst)]), label)


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
        on_add: Callable[[], None] | None = None,
        fan: Fan | None = None,
        adding: Adding | None = None,
        outputs: Outputs | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setStyleSheet(stack_stylesheet())

        self.project_card = fixed_card(f"project — {project}")
        if on_add is not None:
            # On the project card and not at the foot of the stack, for the
            # library card's reason (`project_select.py`): a step is added to
            # this chain, and the gap it goes in is asked for afterwards rather
            # than fixed by where the button stands. Absent where the caller
            # offered no way to add, which is the only honest alternative to a
            # button that would refuse whenever it was pressed.
            add = chrome_button("ADD STEP", "Add a step — the box asks which gap")
            add.clicked.connect(on_add)
            self.project_card.layout().addWidget(add)
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

        foot = len(steps)
        self.output_card = None if outputs is None else self._build_output_card(outputs)
        writes = () if outputs is None else outputs.writes
        self.column = ChainColumn(
            [(source, position) for position, step in enumerate(steps) for source in step.reads]
            + [(write.position, foot) for write in writes],
            {(write.position, foot): write.product for write in writes},
        )
        stack = QVBoxLayout(self.column)
        stack.setContentsMargins(6, 6, 6, 6)
        # The gap between cards is the only place an edge between neighbours
        # shows, so it is sized for the arrowhead rather than for the rhythm of
        # the cards.
        stack.setSpacing(18)
        self.fan = self._build_fan(fan, steps)
        self.add_box = self._build_add_box(adding, steps)
        for position, card in enumerate(self.cards):
            stack.addWidget(card)
            if self.fan is not None and position == self.fan.position:
                stack.addWidget(self.fan)
            # Below the fan where there is one, because the box stands in the
            # gap that step's output crosses and the fan is the first thing in it.
            if self.add_box is not None and position == self.add_box.site:
                stack.addWidget(self.add_box)
        if self.output_card is not None:
            stack.addSpacing(ceil(self.column.label_headroom()))
            stack.addWidget(self.output_card)
        stack.addStretch(1)
        # The output card is a card of the column and not of the pane: the lines
        # are drawn between cards by position and its position is the foot of the
        # stack, while `cards` is the walk's own list and the walk never stands
        # on a card no node is behind. The box is past both, for the second half
        # of that reason and for a further one — it holds no node at all, so
        # numbering it as a position would put it in the walk's own list.
        self.column.cards = self.cards + (() if self.output_card is None else (self.output_card,))
        if self.add_box is not None:
            self.column.hold_box(
                len(self.column.cards),
                self.add_box.site,
                tuple(
                    position
                    for position, step in enumerate(steps)
                    if self.add_box.site in step.reads
                ),
            )
            self.column.cards += (self.add_box,)
        self.column.fan = self.fan

        scroll = QScrollArea()
        scroll.setWidget(self.column)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 0)
        layout.setSpacing(6)
        layout.addWidget(self.project_card)
        layout.addWidget(scroll)

    @staticmethod
    def _build_output_card(outputs: Outputs) -> ChainCard:
        """The foot of the chain: what leaves it, and the way into the write list.

        Never selected, and with no ✕ or ◆: the walk is over the document's nodes
        and there is no node here to stand on, pin or drop. What it carries is the
        arrow every other card carries, because the pane behind it is this card's
        form like any other step's (`save_screen.py`).
        """
        card = ChainCard(selected=False)
        row = QHBoxLayout(card)
        row.setContentsMargins(8, 6, 8, 6)
        row.addWidget(title_label("output"))
        row.addStretch(1)
        row.addWidget(_settings_button(outputs.on_open))
        return card

    @staticmethod
    def _build_add_box(adding: Adding | None, steps: Sequence[Step]) -> AddBox | None:
        """The box in the gap under `adding.site`, or nothing where none is open.

        The note it carries is the splice in the two names the picture cannot
        show until it happens: what the new step would read, and what would read
        it. Read off `Step.reads` inverted, which is the same list the dashed
        edges are drawn from, so the words and the lines cannot disagree.
        """
        if adding is None:
            return None
        site = steps[adding.site]
        readers = [
            step.node.node_id for position, step in enumerate(steps) if adding.site in step.reads
        ]
        note = f"after {site.node.node_id}" + (
            f" · {', '.join(readers)} would read it" if readers else ""
        )
        return AddBox(adding, adding.site + 2, note)

    def _build_fan(self, fan: Fan | None, steps: Sequence[Step]) -> RegionFan | None:
        """The branch below `fan.position`, or nothing where there is no gap for it.

        The gap is the one between that card and the nearest card reading it. A
        fan below the foot of the chain would be a row of squares with nothing
        to continue into — a legend, and what the picture claims is that it is
        the branch itself. Nothing is drawn for a step whose regions the caller
        found none of, either: a branch of nothing is the plain arrow the rest
        of the stack already draws.
        """
        if fan is None or not fan.regions:
            return None
        readers = [
            position
            for position, step in enumerate(steps)
            if fan.position in step.reads and position > fan.position
        ]
        if not readers:
            return None
        reader = min(readers)
        # The trunk in the fan's own coordinates: the cards and the fan are rows
        # of one column layout, so they share a left edge and a lane offset
        # carries across unchanged.
        return RegionFan(fan, reader, lane_x(0.0, self.column.lane_of(fan.position, reader)))

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
