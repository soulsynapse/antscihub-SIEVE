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

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent, QPen, QPolygonF
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from sieve.core.pipeline_model import Node
from sieve.gui.chrome import ACCENT, DIM, LINE, PANEL, STACK_BG, TEXT, rgb, stack_stylesheet


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
# One clause of the referent's is not here: the port named at an arrowhead where
# a step has more than one input. Schema v1 gives an edge no port and refuses two
# edges into one node, so there is nothing in the tree a name could be read off —
# `todo/the-output-is-a-step-and-its-ticks-are-edges.md` is where both the second
# input and the product that names it arrive together.

#: The trunk's inset from a card's left edge, and the step out to the next lane.
EDGE_STUB = 16.0
EDGE_LANE = 34.0
ARROW_WIDTH = 4.0
ARROW_HEIGHT = 6.0


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

    def __init__(self, edges: Sequence[tuple[int, int]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Only the edges that descend. A walk that puts a producer below its
        # reader has a cycle in it, which the window still has to draw
        # (`walk.py`) and which no downward line describes.
        self.edges = tuple(edge for edge in edges if edge[0] < edge[1])
        self._lanes = edge_lanes(self.edges)
        self.cards: tuple[ChainCard, ...] = ()
        self.fan: RegionFan | None = None

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

    def fanned_edge(self) -> FannedEdge:
        """Out of the fanned card into every region, and on out of the one selected.

        One run across the gap and a vertical drop off it into each square: what
        the picture has to say is that these all came from that card, and a
        shared segment says it while every arrowhead stays a descent, which is
        what an arrowhead means everywhere else in the stack. The way out
        mirrors it back onto the trunk, so the lane the rest of the stack is
        drawn in survives the branch.
        """
        assert self.fan is not None
        src, dst = self.fan.position, self.fan.reader
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
        for src, dst in self.edges:
            if (src, dst) == fanned:
                self._paint_fanned_edge(painter)
            else:
                self._paint_edge(painter, src, dst)
        painter.end()

    def _paint_fanned_edge(self, painter: QPainter) -> None:
        """The branch, with everything but the selected region's reach held back.

        The run is drawn twice so the reach to the selected square is at the
        chain's own weight and the rest of it is not, the way the drops off it
        are: what is dimmed is the part of the picture describing a chain the
        walk is not on.
        """
        assert self.fan is not None
        edge = self.fanned_edge()
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

        painter.setPen(QPen(LINE, 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for start, end in zip(edge.rejoin, edge.rejoin[1:], strict=False):
            painter.drawLine(start, end)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(LINE)
        painter.drawPolygon(arrowhead(edge.rejoin[-1]))

    def _paint_edge(self, painter: QPainter, src: int, dst: int) -> None:
        start, end = self.edge_line(src, dst)
        painter.setPen(QPen(LINE, 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(start, end)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(LINE)
        painter.drawPolygon(arrowhead(end))


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
        fan: Fan | None = None,
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

        self.column = ChainColumn(
            [(source, position) for position, step in enumerate(steps) for source in step.reads]
        )
        stack = QVBoxLayout(self.column)
        stack.setContentsMargins(6, 6, 6, 6)
        # The gap between cards is the only place an edge between neighbours
        # shows, so it is sized for the arrowhead rather than for the rhythm of
        # the cards.
        stack.setSpacing(18)
        self.fan = self._build_fan(fan, steps)
        for position, card in enumerate(self.cards):
            stack.addWidget(card)
            if self.fan is not None and position == self.fan.position:
                stack.addWidget(self.fan)
        stack.addStretch(1)
        self.column.cards = self.cards
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
