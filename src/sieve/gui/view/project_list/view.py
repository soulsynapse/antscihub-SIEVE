"""Project library: a column of cards, a + that adds one, and per-card verbs."""

from __future__ import annotations

from typing import Iterable, Sequence

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QToolButton, QWidget

from sieve.gui import icons, palette
from sieve.gui.primitives import CardStack, Empty
from sieve.gui.primitives.stack import sheet as stack_sheet
from sieve.gui.view.project_list.card import ProjectCard
from sieve.gui.view.project_list.project import Project

_GAP = 6


def _plus_button() -> QToolButton:
    """The head's +. Sized to the title it stands beside, not to a card's row."""
    button = QToolButton()
    button.setObjectName("plus")
    button.setIcon(icons.icon("plus"))
    button.setIconSize(QSize(icons.SIZE, icons.SIZE))
    button.setAutoRaise(True)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setToolTip("Add a project — point at the recording it is about")
    return button


class ProjectList(CardStack):
    """One card per project, single selection, and the verbs that act on one.

    Nothing here reads or writes the library. The view says what was asked for
    — add one, open this, remove this — and is redrawn from whatever the
    library holds afterwards, so a refused add or a failed write cannot leave a
    card standing for a project that is not remembered.
    """

    selected = Signal(Project)
    opened = Signal(Project)
    #: the head's +: a recording is wanted, and whoever owns the library asks
    #: for one. The view does not open a file dialog and does not store a row.
    new = Signal()
    removed = Signal(Project)

    def __init__(
        self, projects: Iterable[Project] = (), parent: QWidget | None = None
    ) -> None:
        super().__init__("Projects", gap=_GAP, parent=parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._plus = _plus_button()
        self._plus.clicked.connect(self.new)
        self.add_figure(self._plus)
        # The glyph is a pixmap baked at the current palette, so it is redrawn
        # rather than restyled. Bound method: PySide6 drops it with the widget.
        palette.CHANGED.connect(self._reink)

        self._projects: list[Project] = []
        self._cards: list[ProjectCard] = []
        self._nothing: Empty | None = None
        self._current = -1

        self.show_projects(projects)

    # -- what is on the surface ------------------------------------------

    def show_projects(self, projects: Iterable[Project]) -> None:
        """Redraw the list, preserving selection when the project is still present."""
        standing = self.current()
        self._projects = list(projects)
        self._rebuild()
        if standing in self._projects:
            self.select(self._projects.index(standing))
        else:
            self.select(0 if self._projects else -1)

    def projects(self) -> Sequence[Project]:
        return tuple(self._projects)

    def current(self) -> Project | None:
        if 0 <= self._current < len(self._projects):
            return self._projects[self._current]
        return None

    def _rebuild(self) -> None:
        # clear() deletes the Empty widget too, so null the reference.
        self.clear()
        self._cards = []
        self._nothing = None
        self._current = -1

        for index, project in enumerate(self._projects):
            card = ProjectCard(project)
            card.selected.connect(lambda index=index: self.select(index))
            card.opened.connect(lambda index=index: self.open(index))
            card.removed.connect(lambda index=index: self.remove(index))
            self.add_card(card)
            self._cards.append(card)

        self.set_note(f"{len(self._projects)} remembered" if self._projects else "")
        self._empty_state()

    def _empty_state(self) -> None:
        if self._projects:
            return
        self._nothing = Empty(
            "No projects yet",
            "Use + to point at a recording; it is remembered here.",
        )
        self.add_card(self._nothing)

    # -- standing, and moving -------------------------------------------

    def select(self, index: int) -> None:
        """Stand on a card; out-of-range is a no-op."""
        if not 0 <= index < len(self._cards) or index == self._current:
            return
        if 0 <= self._current < len(self._cards):
            self._cards[self._current].set_selected(False)
        self._current = index
        card = self._cards[index]
        card.set_selected(True)
        self.ensure_visible(card)
        self.selected.emit(self._projects[index])

    def step(self, delta: int) -> None:
        """Move delta rows, clamped to the ends (no wrap)."""
        if not self._cards:
            return
        self.select(max(0, min(len(self._cards) - 1, self._current + delta)))

    def open(self, index: int) -> None:
        """Select then open, so a double-click updates the selection first."""
        if not 0 <= index < len(self._projects):
            return
        self.select(index)
        self.opened.emit(self._projects[index])

    def remove(self, index: int) -> None:
        """Ask for a row to go. The list does not drop it — the library does,
        and the list is redrawn from what the library then holds."""
        if not 0 <= index < len(self._projects):
            return
        self.removed.emit(self._projects[index])

    # -- what it wears ----------------------------------------------------

    def _reink(self) -> None:
        self._plus.setIcon(icons.icon("plus"))

    def _sheet(self) -> str:
        # No hover fill: the glyph's own Active ink is what a verb answers with
        # everywhere else in this view, and the head is not a card.
        return stack_sheet() + """
            #plus { border: 0; padding: 2px; background: transparent; }
        """

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            self.step(-1 if key == Qt.Key.Key_Up else +1)
            event.accept()
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.open(self._current)
            event.accept()
            return
        super().keyPressEvent(event)
