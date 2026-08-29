"""Palette chooser: every palette as a row, grouped light then dark."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from sieve.gui import metrics, palette
from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, PANEL_HOT, STACK_BG, TEXT, rgb

_GUTTER = 8

# Always present (colour changes, width doesn't) so text doesn't shift on select.
_EDGE = 3

_SWATCH = 14
_ROLES = ("stack_bg", "panel", "panel_hot", "line", "text", "accent")


def _sheet() -> str:
    """Scoped to object names so rules don't leak into the enclosing card."""
    return f"""
        #palettes {{
            background: {rgb(PANEL_HOT)};
            border: 1px solid {rgb(LINE)};
        }}
        #pscroll {{ background: {rgb(PANEL_HOT)}; border: 0; }}
        #pcolumn {{ background: {rgb(PANEL_HOT)}; }}
        #pgroup {{
            color: {rgb(DIM)};
            font-size: {metrics.pt("gloss")}pt;
            font-weight: 600;
        }}
        #prow {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(LINE)};
            border-left: {_EDGE}px solid {rgb(PANEL)};
        }}
        #prow:hover {{ background: {rgb(PANEL_HOT)}; }}
        #prow[chosen="true"] {{ border-left-color: {rgb(ACCENT)}; }}
        #pname {{
            color: {rgb(TEXT)};
            font-size: {metrics.pt("name")}pt;
            font-weight: 600;
        }}
        #pgloss {{ color: {rgb(DIM)}; font-size: {metrics.pt("gloss")}pt; }}
        QScrollBar:vertical {{
            background: {rgb(PANEL_HOT)};
            width: 8px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {rgb(LINE)};
            min-height: 24px;
        }}
        QScrollBar::handle:vertical:hover {{ background: {rgb(STACK_BG)}; }}
        QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
        QScrollBar::add-page, QScrollBar::sub-page {{ background: {rgb(PANEL_HOT)}; }}
    """


class Palettes(QWidget):
    """Scrollable palette list, grouped light then dark, with the active one marked."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("palettes")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._rows: list[_Row] = []

        column = QWidget()
        column.setObjectName("pcolumn")
        stack = QVBoxLayout(column)
        stack.setContentsMargins(_GUTTER, _GUTTER, _GUTTER, _GUTTER)
        stack.setSpacing(_GUTTER)
        for dark, heading in ((False, "light"), (True, "dark")):
            label = QLabel(heading)
            label.setObjectName("pgroup")
            stack.addWidget(label)
            for entry in palette.PALETTES:
                if entry.dark != dark:
                    continue
                row = _Row(entry)
                row.chosen.connect(palette.use)
                stack.addWidget(row)
                self._rows.append(row)
        scroll = QScrollArea()
        scroll.setObjectName("pscroll")
        scroll.setWidget(column)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        body = QVBoxLayout(self)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(scroll)

        self._restyle()
        palette.CHANGED.connect(self._restyle)
        metrics.CHANGED.connect(self._restyle)

    def _restyle(self) -> None:
        self.setStyleSheet(_sheet())
        for row in self._rows:
            row.mark(row.scheme is palette.current())


class _Row(QFrame):
    """One palette row: name, gloss, and swatch strip. Reports picks, does not mark itself."""

    chosen = Signal(object)

    def __init__(self, entry: palette.Palette, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("prow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)

        # `self.palette` would shadow QWidget.palette(), breaking Qt style internals.
        self.scheme = entry

        name = QLabel(entry.name)
        name.setObjectName("pname")
        gloss = _Gloss(entry.gloss)

        words = QVBoxLayout()
        words.setContentsMargins(0, 0, 0, 0)
        words.setSpacing(1)
        words.addWidget(name)
        words.addWidget(gloss)

        row = QHBoxLayout(self)
        row.setContentsMargins(8, 6, 8, 6)
        row.setSpacing(_GUTTER)
        row.addLayout(words, 1)
        for role in _ROLES:
            row.addWidget(_swatch(getattr(entry, role), entry.line))

    def mark(self, chosen: bool) -> None:
        # unpolish/polish is required for a dynamic property change to take effect.
        if self.property("chosen") == chosen:
            return
        self.setProperty("chosen", chosen)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.chosen.emit(self.scheme)
        super().mousePressEvent(event)


class _Gloss(QLabel):
    """Wrapping label that corrects Qt's width-unaware sizeHint for scroll layouts."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("pgloss")
        self.setWordWrap(True)
        policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)

    def sizeHint(self) -> QSize:
        hint = super().sizeHint()
        if self.width() <= 0:
            return hint
        return QSize(hint.width(), self.heightForWidth(self.width()))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Width-only: unconditional updateGeometry would loop through relayout.
        if event.size().width() != event.oldSize().width():
            self.updateGeometry()


def _swatch(colour: QColor, edge: QColor) -> QWidget:
    # Styled from literals, never restyled — shows the palette's own colours, not the active one.
    block = QFrame()
    block.setFixedSize(_SWATCH, _SWATCH)
    block.setStyleSheet(f"background: {rgb(colour)}; border: 1px solid {rgb(edge)};")
    return block
