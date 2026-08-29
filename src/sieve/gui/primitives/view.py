"""Titled head band and content area — the chassis every pane view stands in."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from sieve.gui import metrics, palette
from sieve.gui.palette import DIM, LINE, PANEL, STACK_BG, TEXT, rgb

# Exported: callers align content under the head to the same left margin.
PAD_X = 16
PAD_Y = 13


def sheet() -> str:
    """Head rules for callers that set an ancestor sheet (which would override these)."""
    return f"""
        #view {{ background: {rgb(STACK_BG)}; }}
        #viewhead {{
            background: {rgb(PANEL)};
            border-bottom: 1px solid {rgb(LINE)};
        }}
        #viewtitle {{
            color: {rgb(TEXT)};
            font-size: {metrics.pt("heading")}pt;
            font-weight: 600;
        }}
        #viewnote {{ color: {rgb(DIM)}; font-size: {metrics.pt("gloss")}pt; }}
    """


class View(QWidget):
    """Head band with title/note/arrows, and a body layout for the view's content."""

    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("view")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._title = QLabel(title)
        self._title.setObjectName("viewtitle")
        self._arrows: QWidget | None = None
        self._note = QLabel()
        self._note.setObjectName("viewnote")

        self._band = QWidget()
        self._band.setObjectName("viewhead")
        self._band.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._head = QHBoxLayout(self._band)
        self._head.setContentsMargins(PAD_X, PAD_Y, PAD_X, PAD_Y)
        self._head.setSpacing(12)
        self._head.addWidget(self._title)
        self._head.addStretch(1)
        self._figures = 0
        self._head.addWidget(self._note)

        # Widget, not bare layout — an empty QBoxLayout can't take stretch.
        self._room = QWidget()
        self._room.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._body = QVBoxLayout(self._room)
        self._body.setContentsMargins(0, 0, 0, 0)
        self._body.setSpacing(0)

        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        column.addWidget(self._band)
        column.addWidget(self._room, 1)

        self._restyle()
        # Bound methods so PySide6 drops the connection when the receiver dies.
        palette.CHANGED.connect(self._restyle)
        metrics.CHANGED.connect(self._restyle)

    # -- the band ----------------------------------------------------------

    def set_title(self, title: str) -> None:
        self._title.setText(title)

    def set_note(self, note: str) -> None:
        self._note.setText(note)

    def set_arrows(self, arrows: QWidget | None) -> None:
        """Place or remove navigation arrows at the band's far end."""
        if self._arrows is not None:
            self._head.removeWidget(self._arrows)
            self._arrows.setParent(None)
        self._arrows = arrows
        if arrows is not None:
            self._head.addWidget(arrows)

    def add_figure(self, figure: QWidget) -> None:
        """Insert a figure widget after the title, before the stretch."""
        self._figures += 1
        self._head.insertWidget(self._figures, figure)

    def head(self) -> QHBoxLayout:
        """The band's row layout, for placements `add_figure` doesn't cover."""
        return self._head

    # -- the room under it -------------------------------------------------

    def body(self) -> QVBoxLayout:
        """The content layout under the head band."""
        return self._body

    # -- what it wears -----------------------------------------------------

    def _sheet(self) -> str:
        """Override point for subclasses that add their own stylesheet rules."""
        return sheet()

    def _restyle(self) -> None:
        self.setStyleSheet(self._sheet())
