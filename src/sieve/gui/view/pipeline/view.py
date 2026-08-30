"""Pipeline view: the chain of steps, starting with the source."""

from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from sieve.gui.palette import ACCENT, DIM, LINE, mix
from sieve.gui.primitives import Card, CardStack, Empty, Fact, Facts

#: The trunk's inset from a card's left edge, and the arrowhead it ends in.
_STUB = 16.0
_ARROW_W = 4.0
_ARROW_H = 6.0

#: How far out into the gutter an edge steps to pass a card it does not feed.
_LANE = 10.0

#: The head's node id, as the binding spells it.
_SOURCE = "source"


class Pipeline(CardStack):
    """Source card and the steps that follow it."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Pipeline", parent=parent)
        self._source_card: Card | None = None
        self._step_cards: list[Card] = []
        #: card index -> the index of the card feeding it, over the chain
        self._feeds: dict[int, int] = {}
        #: which step cards have produced a value. An edge is lit once
        #: something has actually flowed down *it* — with several steps off
        #: one source, only one of them is running at a time, and lighting
        #: the rest would draw work nobody did.
        self._lit: set[int] = set()
        self.clear_source()

    def show_source(
        self,
        address: str,
        tool_name: str,
        width: int,
        height: int,
        frame_count: int,
    ) -> None:
        """Place a card for the open source at the head of the chain."""
        # Everything goes, the empty state included: it is a card like any
        # other by the stack's reckoning, and leaving it stranded between the
        # source and the first step is a gap the chain would draw an edge
        # straight across.
        self.clear()
        self._source_card = None
        self._step_cards = []
        self._feeds = {}
        self._lit = set()
        name = _short_name(address)
        card = Card(name)
        card.set_removable(False, "Close the project to remove the source")
        card.set_swappable(False, "The source is chosen when the project is made")
        facts = Facts([
            Fact("tool", tool_name),
            Fact("size", f"{width} × {height}"),
            Fact("frames", f"{frame_count:,}"),
        ])
        card.add_row(facts)
        self._source_card = card
        self.add_card(card)
        self.set_note(_steps_note(0))

    def show_steps(self, steps: tuple,
                   unbound: dict[str, str] | None = None,
                   feeds: dict[str, str] | None = None) -> None:
        """Add a card for each loaded step tool after the source.

        A step the chain could not bind still gets a card, saying why. A step
        that quietly went missing is the same defect as a silently absent
        case in an experiment: it reads as a step that had nothing to say.
        """
        unbound = unbound or {}
        self._step_cards = []
        for tool in steps:
            role = tool.role
            card = Card(tool.name)
            card.set_removable(False, "Auto-registered from the tool directory")
            card.set_swappable(False)
            offered = (Fact("unbound", unbound[tool.name])
                       if tool.name in unbound else
                       # what the next card in the chain would bind to
                       Fact("offers", ", ".join(
                           f"{p.name} ({p.kind})" for p in role.produces)))
            facts = Facts([
                Fact("offsets", " ".join(str(o) for o in role.offsets)),
                Fact("reach", str(role.reach)),
                offered,
            ])
            card.add_row(facts)
            card.set_meter(0.0)
            self.add_card(card)
            self._step_cards.append(card)
        # Which card feeds which, by card index over source-then-steps. Given
        # rather than assumed: every step here is fed by the source, so a
        # column of arrows between neighbours would draw a chain that does not
        # exist. Without it, the picture is a guess that happens to be wrong.
        names = [_SOURCE] + [tool.name for tool in steps]
        self._feeds = {}
        for index, tool in enumerate(steps, start=1):
            producer = (feeds or {}).get(tool.name, _SOURCE)
            if producer in names:
                self._feeds[index] = names.index(producer)
        # The source is what the chain starts from, not a step in it.
        self.set_note(_steps_note(len(steps)))

    # -- the chain's edges -------------------------------------------------

    def paint_ground(self, painter: QPainter) -> None:
        """One arrow per binding, from the card that produces to the card fed.

        Per binding and not between neighbours: two steps off one source is a
        fan, and a column of arrows would draw a chain nobody built. A
        producer that is not the card directly above is reached down a lane in
        the left gutter, so the edge passes cards it does not touch instead of
        appearing to enter them.

        Only cards in the chain are joined — the empty state is a card by the
        stack's reckoning and nothing flows into it. The colour is mixed at
        paint time rather than held: `palette.mix` says roles mutate on a
        palette swap, and an edge held from before one would be the old
        theme's line on the new theme's ground.
        """
        chain = self._chain()
        if len(chain) < 2:
            return
        edge = mix(LINE, DIM, 0.5)
        for index, card in enumerate(chain):
            parent = self._feeds.get(index)
            if parent is None or parent >= len(chain) or parent == index:
                continue
            above, below = chain[parent].geometry(), card.geometry()
            x = below.left() + _STUB
            start = QPointF(x, above.bottom() + 1)
            end = QPointF(x, below.top())
            if end.y() - start.y() < _ARROW_H:
                continue
            live = (card in self._step_cards
                    and self._step_cards.index(card) in self._lit)
            color = ACCENT if live else edge
            painter.setPen(QPen(color, 1.4 if live else 1.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            if parent == index - 1:
                painter.drawLine(start, QPointF(x, end.y() - _ARROW_H))
            else:
                lane = below.left() - _LANE
                turn = end.y() - _ARROW_H - _LANE / 2
                painter.drawPolyline(QPolygonF([
                    start, QPointF(lane, start.y()), QPointF(lane, turn),
                    QPointF(x, turn), QPointF(x, end.y() - _ARROW_H),
                ]))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawPolygon(QPolygonF([
                QPointF(end.x() - _ARROW_W, end.y() - _ARROW_H),
                QPointF(end.x() + _ARROW_W, end.y() - _ARROW_H),
                QPointF(end.x(), end.y()),
            ]))

    def _chain(self) -> list[QWidget]:
        """Source first, then the steps, skipping the empty state."""
        head = [self._source_card] if self._source_card is not None else []
        return head + list(self._step_cards)

    def update_step(self, index: int, meter: float) -> None:
        """Update the meter on the *index*-th step card."""
        if 0 <= index < len(self._step_cards):
            self._step_cards[index].set_meter(meter)
            self._lit.add(index)
            self._ground.update()

    def clear_source(self) -> None:
        """Back to the empty state: no source, no steps, no edges."""
        self.clear()
        self._source_card = None
        self._step_cards = []
        self._feeds = {}
        self._lit = set()
        self.add_card(Empty("No steps yet", "Open a project to start the chain."))
        self.set_note("")


def _steps_note(count: int) -> str:
    """The head's note: how many steps stand under the source."""
    return "no steps" if count == 0 else f"{count} step{'s' if count != 1 else ''}"


def _short_name(address: str) -> str:
    """The last component of the address, however it is shaped."""
    for cls in (PureWindowsPath, PurePosixPath):
        try:
            return cls(address).name or address
        except Exception:
            continue
    return address
