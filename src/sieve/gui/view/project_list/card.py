"""One project, as a card the pointer and the keyboard reach the same way.

The card is the target: clicking anywhere on it selects, double-clicking opens,
and the arrow button is the same open offered to a pointer that has no way to
know the double click is there. Selection is an accent edge down the leading
side rather than a fill, so a card that is current and a card that is hovered
are never the same picture — the fill is the pointer's answer and the edge is
the selection's, and both can be true at once.

The card paints nothing itself and wears a stylesheet scoped to its own widget:
these rules are set on the card, so they reach the labels inside it and nothing
outside, which is the arrangement `chrome.py` refuses to do from the window.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
)

from sieve.gui import icons, palette
from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, PANEL_HOT, TEXT, rgb
from sieve.gui.view.project_list.project import Project

#: How wide the selected card's leading edge is. Wide enough to read from the
#: far side of the pane without the card's contents moving when it appears —
#: which is why the edge is on every card and only its colour changes.
_EDGE = 3


def _sheet(selected: bool) -> str:
    """The card's dress. The edge carries the selection; the fill, the pointer."""
    edge = ACCENT if selected else PANEL
    return f"""
        #card {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(LINE)};
            border-left: {_EDGE}px solid {rgb(edge)};
        }}
        #card:hover {{ background: {rgb(PANEL_HOT)}; }}
        #name {{ color: {rgb(TEXT)}; font-weight: 600; }}
        #line {{ color: {rgb(DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _button(glyph: str, tip: str) -> QToolButton:
    """One of the row's icons. The colours are the icon's three modes and not a
    stylesheet rule, since `color:` reaches text and an icon is a pixmap —
    `gui/icons` says the rest of it."""
    button = QToolButton()
    button.setIcon(icons.icon(glyph))
    button.setIconSize(QSize(icons.SIZE, icons.SIZE))
    button.setAutoRaise(True)
    button.setToolTip(tip)
    return button


class ProjectCard(QFrame):
    """A project on the surface: select it, open it, or go to it on disk."""

    #: The card was chosen — clicked, or arrowed onto. Selection is the list's
    #: to hold, so the card asks rather than marking itself.
    selected = Signal()

    #: Open this project: double click, or the arrow. Same verb from both, and
    #: neither says what opening does — that is the frame's.
    opened = Signal()

    def __init__(self, project: Project, parent=None) -> None:
        super().__init__(parent)
        self.project = project
        self.setObjectName("card")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        #: Held rather than read back off the sheet, which is rebuilt whenever
        #: the palette changes and has to come back in the state the list last
        #: put the card in.
        self._selected = False
        self.set_selected(False)

        column = QVBoxLayout(self)
        column.setContentsMargins(8, 6, 8, 8)
        column.setSpacing(4)

        head = QHBoxLayout()
        head.setSpacing(4)
        # The name takes the row's remainder rather than a stretch sitting after
        # it: the label reports no width of its own, so a stretch would be the
        # only thing in the row asking for room and would get all of it.
        head.addWidget(_Line(project.name, "name"), 1)
        #: Held so the icons can be drawn again when the palette changes — a
        #: `QIcon` is pixmaps at the colours in force when it was made, and a
        #: stylesheet cannot reach one.
        self._open = self._open_button()
        self._reveal = self._reveal_button()
        head.addWidget(self._open)
        head.addWidget(self._reveal)
        column.addLayout(head)

        column.addWidget(_Line(project.holds, "line"))
        column.addWidget(_Line(project.opened, "line"))

        palette.CHANGED.connect(self._restyle)

    def _open_button(self) -> QToolButton:
        button = _button("arrow-right", "Open this project")
        button.clicked.connect(self.opened)
        return button

    def _reveal_button(self) -> QToolButton:
        """The folder in the system's file manager.

        On every card and not the selected one alone: it acts on the project the
        row is about, not on the selection, so hiding it until a card is current
        would make the user select a project to do something that never touches
        the selection.
        """
        button = _button("folder-open", f"Show {self.project.folder} on disk")
        button.clicked.connect(self._reveal)
        return button

    def _reveal(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.project.folder))

    def set_selected(self, selected: bool) -> None:
        """Wear the accent edge, or give it back. Re-set rather than toggled
        through a dynamic property: a property would need an unpolish/polish
        pair to take, and this is one string on one widget."""
        self._selected = selected
        self.setStyleSheet(_sheet(selected))

    def _restyle(self) -> None:
        """The sheet and both icons again, in the palette now in use."""
        self.setStyleSheet(_sheet(self._selected))
        self._open.setIcon(icons.icon("arrow-right"))
        self._reveal.setIcon(icons.icon("folder-open"))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.opened.emit()
        super().mouseDoubleClickEvent(event)


class _Line(QLabel):
    """A line of the card: one row, cut to the width it is given.

    A pane is as narrow as the user drags the splitter, and a label that took
    the width its text wants would push the card out under the column and take
    the buttons at its right with it — a project whose name is long would be a
    project whose → cannot be reached. Wrapping does not save it: a name is
    usually one unbreakable word, and a label that cannot break still asks for
    the whole of it.

    So the width is the card's to give and the text is cut to fit, which also
    keeps every card the same height — the list is walked with ↑ and ↓, and rows
    that changed height as their text got longer would move under the key.
    """

    def __init__(self, text: str, name: str) -> None:
        super().__init__(text)
        self._full = text
        self.setObjectName(name)
        self.setToolTip(text)
        # Ignored, not Preferred: the label's own idea of its width is exactly
        # what must not reach the layout, since that is the thing widening the
        # card. It takes what the row has and reports nothing back.
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.setText(
            self.fontMetrics().elidedText(
                self._full, Qt.TextElideMode.ElideRight, self.width()
            )
        )
