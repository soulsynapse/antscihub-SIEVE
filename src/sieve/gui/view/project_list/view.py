"""The library as a column of cards: which projects there are, and which is current.

The ground is `primitives/stack.py`'s and the head over it is
`primitives/view.py`'s, and both were this file's — the band until the card mock
up settled what a header looks like, and then the head itself once a pane that
is not a column of cards wanted the same line at its top. The title it carries
is `Projects` for now: what a pane's head says is the pane's own claim, and this
one has no library to name itself after yet. What is left here is the part that
is about the library: which projects there are, which one is being stood on, and
what the two verbs — standing and opening — mean.

The list holds the selection and the cards do not: a card that decided it was
current would have to hear about every other card to stop being it, and the one
thing that is true of the whole column — exactly one row is where the user is
standing — would then be spread across all of them. So a card reports being
chosen and the list answers by moving the accent edge.

Opening is a second verb and not what selecting does. Standing on a project is
free and reversible; opening one is what the rest of the work is then about, and
a list where arrowing down opened each row in turn would make the cheap move the
expensive one. What opening *means* is not the view's — it emits, and the frame
decides whether that slides a swipe, fills a pane, or does nothing yet.

↑ and ↓ are handled here rather than bound on the window, because they mean
"the next row of whatever I am standing in" and only the thing with focus knows
what a row is. The frame binds ← and → for exactly the opposite reason: those
mean the same thing everywhere it houses this view (`hotkeys.py`).
"""

from __future__ import annotations

from typing import Iterable, Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget

from sieve.gui.primitives import CardStack, Empty
from sieve.gui.view.project_list.card import ProjectCard
from sieve.gui.view.project_list.project import Project

#: The gap between rows, in place of the stack's own. The mockup's 26 is room for
#: the chain's edges to descend through and there are none here, so the number is
#: the one that keeps a three-line card reading as a row of one list rather than
#: as a list of its own.
_GAP = 6


class ProjectList(CardStack):
    """Every project the library remembers, one card each, one of them current.

    Handed its projects rather than fetching them: there is no library to fetch
    from yet, and a view that reached for one would be the file where the answer
    to *where does the list of projects live* had been settled by accident. It
    redraws whole on `show_projects`, because the column is small and a diff
    against the cards on screen is a second description of the same list.
    """

    #: Which project the user is standing on. Emitted on every move, including
    #: the pointer's, so anything drawn about the current project follows the
    #: keyboard and the mouse without either knowing about the other.
    selected = Signal(Project)

    #: This project is the one to work in now. The view never acts on it.
    opened = Signal(Project)

    def __init__(
        self, projects: Iterable[Project] = (), parent: QWidget | None = None
    ) -> None:
        super().__init__("Projects", gap=_GAP, parent=parent)
        # The list answers ↑/↓, so it has to be reachable by tabbing as well as
        # by clicking — a surface that only takes focus from the pointer is one
        # the keyboard cannot get back to after any other widget has had it.
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._projects: list[Project] = []
        self._cards: list[ProjectCard] = []
        self._nothing: Empty | None = None
        self._current = -1

        self.show_projects(projects)

    # -- what is on the surface ------------------------------------------

    def show_projects(self, projects: Iterable[Project]) -> None:
        """Draw this library, keeping the selection on the same project if it is
        still here — the user's place in the list survives a redraw that was not
        about them, and falls to the first card when the one they stood on is
        gone."""
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
        """The project being stood on, or nothing while the library is empty."""
        if 0 <= self._current < len(self._projects):
            return self._projects[self._current]
        return None

    def _rebuild(self) -> None:
        # The stack drops the empty-library sentence along with the cards, since
        # it stands in the same column, so `_nothing` is cleared here rather than
        # in `_empty_state` — a label left named after `clear()` deleted it is a
        # handle to a widget that is going away.
        self.clear()
        self._cards = []
        self._nothing = None
        self._current = -1

        for index, project in enumerate(self._projects):
            card = ProjectCard(project)
            card.selected.connect(lambda index=index: self.select(index))
            card.opened.connect(lambda index=index: self.open(index))
            self.add_card(card)
            self._cards.append(card)

        self.set_note(f"{len(self._projects)} remembered" if self._projects else "")
        self._empty_state()

    def _empty_state(self) -> None:
        """What an empty library says. A sentence and not a blank pane: a list
        with nothing in it and a list that failed to load look identical, and
        only one of them is worth the user waiting on.

        `primitives/empty.py`'s shape rather than this file's dim label, which is
        where that shape came from — the list said this in words before the
        section card and the canvas did, and the primitive is the three of them
        settled once. What it adds is the second line, and the second line is the
        half this copy never had: *no projects yet* is the fact, and naming the
        move that ends it is what makes an empty library different from a broken
        one. The move is named and not offered, because the verb that makes a
        project is not this view's — see the module docstring on where opening
        goes — and a button here would be a second place it lived.
        """
        if self._projects:
            return
        self._nothing = Empty(
            "No projects yet",
            "Make one to start, and it is remembered here.",
        )
        self.add_card(self._nothing)

    # -- standing, and moving -------------------------------------------

    def select(self, index: int) -> None:
        """Stand on a card. Out of range is nothing, so a caller may hand this
        the result of an arithmetic without checking the ends first."""
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
        """Move `delta` rows, stopping at the ends rather than wrapping — the
        same choice the swipe makes, and for the same reason: a held key comes
        to rest at the end of the list instead of reappearing at the far one."""
        if not self._cards:
            return
        self.select(max(0, min(len(self._cards) - 1, self._current + delta)))

    def open(self, index: int) -> None:
        """Select and then open, in that order: a card opened by double click
        was never arrowed onto, and everything drawn about the current project
        would otherwise still be about the one the user left."""
        if not 0 <= index < len(self._projects):
            return
        self.select(index)
        self.opened.emit(self._projects[index])

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
        # ← and → among them: they are the frame's, and an accepted key here is
        # one the window's shortcut never sees.
        super().keyPressEvent(event)
