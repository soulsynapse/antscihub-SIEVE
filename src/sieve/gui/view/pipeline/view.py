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


class Pipeline(CardStack):
    """Source card and the steps that follow it."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Pipeline", parent=parent)
        self._source_card: Card | None = None
        self._step_cards: list[Card] = []
        #: whether a step has produced a value — an edge is lit once something
        #: has actually flowed down it, not merely because a card is loaded
        self._lit = False
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
        self._lit = False
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

    def show_steps(self, steps: tuple) -> None:
        """Add a card for each loaded step tool after the source."""
        self._step_cards = []
        for tool in steps:
            role = tool.role
            card = Card(tool.name)
            card.set_removable(False, "Auto-registered from the tool directory")
            card.set_swappable(False)
            facts = Facts([
                Fact("offsets", " ".join(str(o) for o in role.offsets)),
                Fact("reach", str(role.reach)),
                # what the next card in the chain would be binding to
                Fact("offers", ", ".join(
                    f"{p.name} ({p.kind})" for p in role.produces)),
            ])
            card.add_row(facts)
            card.set_meter(0.0)
            self.add_card(card)
            self._step_cards.append(card)
        # The source is what the chain starts from, not a step in it.
        self.set_note(_steps_note(len(steps)))

    # -- the chain's edges -------------------------------------------------

    def paint_ground(self, painter: QPainter) -> None:
        """An arrow down the gap from each card in the chain to the next.

        Only the cards actually in the chain are joined — the empty state is a
        card by the stack's reckoning and nothing flows into it. The colour is
        mixed at paint time rather than held: `palette.mix` says roles mutate
        on a palette swap, and an edge held from before one would be the old
        theme's line on the new theme's ground.
        """
        chain = self._chain()
        if len(chain) < 2:
            return
        edge = mix(LINE, DIM, 0.5)
        for above, below in zip(chain, chain[1:]):
            top, bottom = above.geometry(), below.geometry()
            x = top.left() + _STUB
            start = QPointF(x, top.bottom() + 1)
            end = QPointF(x, bottom.top())
            if end.y() - start.y() < _ARROW_H:
                continue
            live = below in self._step_cards and self._lit
            color = ACCENT if live else edge
            painter.setPen(QPen(color, 1.4 if live else 1.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawLine(start, QPointF(x, end.y() - _ARROW_H))
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
            if not self._lit:
                self._lit = True
            self._ground.update()

    def clear_source(self) -> None:
        """Back to the empty state: no source, no steps, no edges."""
        self.clear()
        self._source_card = None
        self._step_cards = []
        self._lit = False
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
