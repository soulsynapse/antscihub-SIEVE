"""Scrolling column of named alternatives, each with a gloss and a drawing."""

from __future__ import annotations

from typing import Iterable, NamedTuple

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sieve.gui import metrics, palette
from sieve.gui.palette import DIM, LINE, PANEL, PANEL_HOT, STACK_BG, TEXT, rgb

GUTTER = 10


class Variant(NamedTuple):
    """One alternative: name, gloss, and drawing."""

    name: str
    gloss: str
    drawing: QWidget


def sheet() -> str:
    """Gallery rules for callers that set an ancestor sheet (which would override these)."""
    return f"""
        #gallery {{ background: {rgb(STACK_BG)}; border: 1px solid {rgb(LINE)}; }}
        #gscroll {{ background: {rgb(STACK_BG)}; border: 0; }}
        #gcolumn {{ background: {rgb(STACK_BG)}; }}
        #vname {{
            color: {rgb(TEXT)};
            font-size: {metrics.pt("name")}pt;
            font-weight: 600;
        }}
        #vgloss {{ color: {rgb(DIM)}; font-size: {metrics.pt("gloss")}pt; }}
        #vrule {{ background: {rgb(LINE)}; }}
        QScrollBar:vertical {{
            background: {rgb(STACK_BG)};
            width: 8px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {rgb(LINE)};
            min-height: 24px;
        }}
        QScrollBar::handle:vertical:hover {{ background: {rgb(PANEL_HOT)}; }}
        QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
        QScrollBar::add-page, QScrollBar::sub-page {{ background: {rgb(PANEL)}; }}
    """


class Gallery(QWidget):
    """Scrollable column of Variant blocks."""

    def __init__(
        self, variants: Iterable[Variant], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("gallery")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        column = QWidget()
        column.setObjectName("gcolumn")
        stack = QVBoxLayout(column)
        stack.setContentsMargins(GUTTER, GUTTER, GUTTER, GUTTER)
        stack.setSpacing(GUTTER)
        for variant in variants:
            stack.addWidget(_block(variant))
        stack.addStretch(1)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("gscroll")
        self._scroll.setWidget(column)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        body = QVBoxLayout(self)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._scroll)

        self._restyle()
        palette.CHANGED.connect(self._restyle)
        metrics.CHANGED.connect(self._restyle)

    def _restyle(self) -> None:
        # Zero-timer remeasure: Qt compresses queued LayoutRequests, so a
        # posted one is swallowed by the scroll's own stale answer.
        self.setStyleSheet(sheet())
        QTimer.singleShot(0, self, self._remeasure)

    def _remeasure(self) -> None:
        QApplication.sendEvent(self._scroll, QEvent(QEvent.Type.LayoutRequest))


def _block(variant: Variant) -> QWidget:
    block = QWidget()

    title = QLabel(variant.name)
    title.setObjectName("vname")
    note = QLabel(variant.gloss)
    note.setObjectName("vgloss")
    note.setWordWrap(True)

    rule = QFrame()
    rule.setObjectName("vrule")
    rule.setFixedHeight(1)

    stack = QVBoxLayout(block)
    stack.setContentsMargins(0, 0, 0, 0)
    stack.setSpacing(4)
    stack.addWidget(title)
    stack.addWidget(note)
    stack.addWidget(variant.drawing)
    stack.addSpacing(2)
    stack.addWidget(rule)
    return block
