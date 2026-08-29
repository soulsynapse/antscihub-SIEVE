"""The sections down the left of a card, and which one is being read.

Held here rather than beside the first view that wanted one: preferences and the
dev view are the same shape — a list of sections against one of them open — and
a nav that lived in `view/preferences/` would be imported back up out of it by
the second card to need it. What the names mean is the caller's; the nav is
handed strings and reports an index, and has never heard of a setting.

The nav holds the selection and the entries do not, for the reason the project
list holds it rather than its cards: the one thing true of the whole column —
exactly one section is open — would otherwise be spread across every entry, each
having to hear about the others to stop being it.

Selection is an accent edge down the leading side rather than a fill, so the
entry under the pointer and the entry being read are never the same picture.
Both can be true at once, and the fill is the pointer's answer while the edge is
the selection's (`project_list/card.py` makes the same split).

↑ and ↓ are answered here because they mean "the next section", and only the
list knows what a section is. Escape is not: it means "close what is on top" and
is the overlay's, which is why an unhandled key is passed up rather than eaten.
"""

from __future__ import annotations

from typing import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from sieve.gui import metrics, palette
from sieve.gui.palette import ACCENT, LINE, PANEL, PANEL_HOT, TEXT, rgb

#: How wide the entry's leading edge is. On every entry, with only its colour
#: changing, so the label stands still as the selection arrives.
#:
#: Public, because it is not this list's look: it is how wide the mark that says
#: *this is the current one* is drawn, and `segmented.py` wears the same mark
#: along the foot of a bar rather than down the side of a row.
MARK_W = 3

#: The gap between entries and the margin around them, one number for both, so
#: the outermost entry sits off the column's edge by the distance it sits off
#: its neighbour.
_GUTTER = 4

#: How wide the column is. The names are short and fixed, and a fixed column
#: holds the boundary between the list and what it is listing still across a
#: resize.
_WIDTH = 150


def _sheet(selected: bool) -> str:
    edge = ACCENT if selected else PANEL
    return f"""
        #entry {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(LINE)};
            border-left: {MARK_W}px solid {rgb(edge)};
        }}
        #entry:hover {{ background: {rgb(PANEL_HOT)}; }}
        #label {{ color: {rgb(TEXT)}; font-size: {metrics.pt("name")}pt; }}
    """


class SectionNav(QWidget):
    """Every section of preferences, one entry each, one of them current."""

    #: Which section is being read. Emitted on every move, the pointer's and the
    #: keyboard's alike, so the side that draws it follows both without either
    #: knowing about the other.
    chosen = Signal(int)

    def __init__(self, names: Sequence[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("nav")
        self.setFixedWidth(_WIDTH)
        # It answers ↑/↓, so the keyboard has to be able to reach it by tabbing
        # and not only by clicking.
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._current = -1
        self._entries: list[_Entry] = []

        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(_GUTTER)
        for index, name in enumerate(names):
            entry = _Entry(name)
            entry.chosen.connect(lambda index=index: self.select(index))
            column.addWidget(entry)
            self._entries.append(entry)
        # Last, and what keeps a short list at the top of the column.
        column.addStretch(1)

        self.select(0)

    def current(self) -> int:
        """The section being read, or -1 while there are none."""
        return self._current

    def select(self, index: int) -> None:
        """Open a section. Out of range is nothing, so a caller may hand this the
        result of an arithmetic without checking the ends first."""
        if not 0 <= index < len(self._entries) or index == self._current:
            return
        if 0 <= self._current < len(self._entries):
            self._entries[self._current].set_selected(False)
        self._current = index
        self._entries[index].set_selected(True)
        self.chosen.emit(index)

    def step(self, delta: int) -> None:
        """Move `delta` entries, stopping at the ends rather than wrapping — a
        held key comes to rest at the last section instead of reappearing at the
        first."""
        if not self._entries:
            return
        self.select(max(0, min(len(self._entries) - 1, self._current + delta)))

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            self.step(-1 if key == Qt.Key.Key_Up else +1)
            event.accept()
            return
        # Escape among them: it is the overlay's, and the thing on top sees only
        # what this list leaves unaccepted.
        super().keyPressEvent(event)


class _Entry(QFrame):
    """One section on the surface. It reports being picked and marks nothing."""

    chosen = Signal()

    def __init__(self, name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("entry")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        #: Held rather than read back off the sheet, because the sheet is rebuilt
        #: whenever the palette changes and it has to come back in the state the
        #: nav last put the entry in.
        self._selected = False
        self.set_selected(False)
        palette.CHANGED.connect(self._restyle)
        metrics.CHANGED.connect(self._restyle)

        label = QLabel(name)
        label.setObjectName("label")

        column = QVBoxLayout(self)
        column.setContentsMargins(8, 6, 8, 6)
        column.setSpacing(0)
        column.addWidget(label)

    def set_selected(self, selected: bool) -> None:
        """Wear the accent edge, or give it back. Re-set rather than toggled
        through a dynamic property: a property needs an unpolish/polish pair to
        take, and this is one string on one widget."""
        self._selected = selected
        self._restyle()

    def _restyle(self) -> None:
        """The same sheet again, in whatever the palette is now."""
        self.setStyleSheet(_sheet(self._selected))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.chosen.emit()
        super().mousePressEvent(event)
