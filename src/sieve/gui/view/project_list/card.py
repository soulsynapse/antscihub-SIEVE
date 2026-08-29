"""Project card: select, open, or reveal on disk."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QSize, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
)

from sieve.gui import icons, metrics, palette
from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, PANEL_HOT, TEXT, rgb
from sieve.gui.view.project_list.project import Project

_EDGE = 3


def _sheet(selected: bool) -> str:
    """The card's dress. The edge carries the selection; the fill, the pointer."""
    edge = ACCENT if selected else PANEL
    return f"""
        #card {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(LINE)};
            border-left: {_EDGE}px solid {rgb(edge)};
            border-radius: {metrics.radius()}px;
        }}
        #card:hover {{ background: {rgb(PANEL_HOT)}; }}
        #name {{
            color: {rgb(TEXT)};
            font-size: {metrics.pt("name")}pt;
            font-weight: 600;
        }}
        #line {{ color: {rgb(DIM)}; font-size: {metrics.pt("gloss")}pt; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _button(glyph: str, tip: str) -> QToolButton:
    button = QToolButton()
    button.setIcon(icons.icon(glyph))
    button.setIconSize(QSize(icons.SIZE, icons.SIZE))
    button.setAutoRaise(True)
    button.setToolTip(tip)
    return button


class ProjectCard(QFrame):
    """A project on the surface: select it, open it, or go to it on disk."""

    selected = Signal()
    opened = Signal()

    def __init__(self, project: Project, parent=None) -> None:
        super().__init__(parent)
        self.project = project
        self.setObjectName("card")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Held because the sheet is rebuilt on palette change and must restore this.
        self._selected = False
        self.set_selected(False)

        column = QVBoxLayout(self)
        column.setContentsMargins(8, 6, 8, 8)
        column.setSpacing(4)

        head = QHBoxLayout()
        head.setSpacing(4)
        head.addWidget(_Line(project.name, "name"), 1)
        # Icons are pixmaps baked at current palette; must be rebuilt on change.
        self._open = self._open_button()
        self._reveal = self._reveal_button()
        head.addWidget(self._open)
        head.addWidget(self._reveal)
        column.addLayout(head)

        column.addWidget(_Line(project.holds, "line"))
        column.addWidget(_Line(project.opened, "line"))

        palette.CHANGED.connect(self._restyle)
        metrics.CHANGED.connect(self._remeasure)

    def _remeasure(self) -> None:
        self.setStyleSheet(_sheet(self._selected))

    def _open_button(self) -> QToolButton:
        button = _button("arrow-right", "Open this project")
        button.clicked.connect(self.opened)
        return button

    def _reveal_button(self) -> QToolButton:
        button = _button("folder-open", f"Show {self.project.folder} on disk")
        button.clicked.connect(self._reveal)
        return button

    def _reveal(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.project.folder))

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.setStyleSheet(_sheet(selected))

    def _restyle(self) -> None:
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
    """Single-line elided label that takes the card's width, not the text's."""

    def __init__(self, text: str, name: str) -> None:
        super().__init__(text)
        self._full = text
        self.setObjectName(name)
        self.setToolTip(text)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._elide()

    def changeEvent(self, event) -> None:
        # FontChange doesn't trigger resizeEvent, so re-elide here.
        super().changeEvent(event)
        if event.type() == QEvent.Type.FontChange:
            self._elide()

    def _elide(self) -> None:
        self.setText(
            self.fontMetrics().elidedText(
                self._full, Qt.TextElideMode.ElideRight, self.width()
            )
        )
