"""Pipeline view: the chain of steps, starting with the source."""

from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath

from PySide6.QtWidgets import QWidget

from sieve.gui.primitives import Card, CardStack, Empty, Fact, Facts


class Pipeline(CardStack):
    """Source card and the steps that follow it."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Pipeline", parent=parent)
        self._source_card: Card | None = None
        self._step_cards: list[Card] = []
        self._nothing: Empty | None = Empty(
            "No steps yet", "Open a project to start the chain."
        )
        self.add_card(self._nothing)

    def show_source(
        self,
        address: str,
        tool_name: str,
        width: int,
        height: int,
        frame_count: int,
    ) -> None:
        """Place a card for the open source at the head of the chain."""
        self.clear_source()
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
        self._nothing = None
        self.insert_card(0, card)
        self.set_note("1 step")

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
            ])
            card.add_row(facts)
            card.set_meter(0.0)
            self.add_card(card)
            self._step_cards.append(card)
        total = (1 if self._source_card else 0) + len(steps)
        self.set_note(f"{total} step{'s' if total != 1 else ''}")

    def update_step(self, index: int, meter: float) -> None:
        """Update the meter on the *index*-th step card."""
        if 0 <= index < len(self._step_cards):
            self._step_cards[index].set_meter(meter)

    def clear_source(self) -> None:
        """Remove the source card, restoring the empty state."""
        if self._source_card is not None:
            self.clear()
            self._source_card = None
        self._step_cards = []
        if self._nothing is None:
            self._nothing = Empty(
                "No steps yet", "Open a project to start the chain."
            )
            self.add_card(self._nothing)
            self.set_note("")


def _short_name(address: str) -> str:
    """The last component of the address, however it is shaped."""
    for cls in (PureWindowsPath, PurePosixPath):
        try:
            return cls(address).name or address
        except Exception:
            continue
    return address
