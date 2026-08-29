"""A card of sections: nav list on the left, one section's body on the right."""

from __future__ import annotations

from typing import Callable, NamedTuple, Sequence

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from sieve.gui import icons, metrics, palette
from sieve.gui.palette import DIM, LINE, PANEL, PANEL_HOT, TEXT, rgb
from sieve.gui.primitives.button import GHOST, Button
from sieve.gui.primitives.nav import SectionNav

GUTTER = 10

_CLOSE = "x"


class Section(NamedTuple):
    """A nav entry: name, gloss, optional body widget, optional reset callable."""

    name: str
    gloss: str
    body: QWidget | None = None
    reset: Callable[[], None] | None = None


def _sheet() -> str:
    return f"""
        #sections {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(LINE)};
            border-radius: {metrics.radius()}px;
        }}
        #heading {{
            color: {rgb(TEXT)};
            font-size: {metrics.pt("heading")}pt;
            font-weight: 600;
        }}
        #note {{ color: {rgb(DIM)}; font-size: {metrics.pt("gloss")}pt; }}
        #placeholder {{
            background: {rgb(PANEL_HOT)};
            border: 1px solid {rgb(LINE)};
        }}
        #name {{
            color: {rgb(TEXT)};
            font-size: {metrics.pt("name")}pt;
            font-weight: 600;
        }}
        #gloss, #empty {{ color: {rgb(DIM)}; font-size: {metrics.pt("gloss")}pt; }}
        #done {{ border: 0; padding: 0 6px; }}
    """


class SectionCard(QWidget):
    """Fixed-size card: heading, note, nav on left, one section's body on right."""

    closed = Signal()

    def __init__(
        self,
        heading: str,
        note: str,
        sections: Sequence[Section],
        width: int,
        height: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("sections")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._restyle()
        # Bound methods so PySide6 drops the connection when the widget dies.
        palette.CHANGED.connect(self._restyle)
        palette.CHANGED.connect(self._redress)
        metrics.CHANGED.connect(self._restyle)
        self.setFixedWidth(width)
        self.setFixedHeight(height)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._sections = tuple(sections)

        title = QLabel(heading)
        title.setObjectName("heading")

        done = self._done = QToolButton()
        done.setObjectName("done")
        done.setIcon(icons.icon(_CLOSE))
        done.setIconSize(QSize(icons.SIZE, icons.SIZE))
        done.setAutoRaise(True)
        done.setToolTip(f"Close {heading} (Esc)")
        done.setCursor(Qt.CursorShape.PointingHandCursor)
        done.clicked.connect(self.closed)

        self._reset: Button | None = None
        if any(section.reset is not None for section in self._sections):
            self._reset = Button("", GHOST, small=True)
            self._reset.clicked.connect(self._put_back)

        head = QHBoxLayout()
        head.setSpacing(GUTTER)
        head.addWidget(title, 1)
        if self._reset is not None:
            head.addWidget(self._reset)
        head.addWidget(done)

        subtitle = QLabel(note)
        subtitle.setObjectName("note")
        subtitle.setWordWrap(True)

        self._placeholder = _Placeholder()

        self._pages = QStackedWidget()
        self._pages.addWidget(self._placeholder)
        for section in self._sections:
            if section.body is not None:
                self._pages.addWidget(section.body)

        self.nav = SectionNav([section.name for section in self._sections])
        self.nav.chosen.connect(self._show_section)
        self._show_section(self.nav.current())

        body = QHBoxLayout()
        body.setSpacing(GUTTER)
        body.addWidget(self.nav)
        body.addWidget(self._pages, 1)

        column = QVBoxLayout(self)
        column.setContentsMargins(GUTTER, GUTTER, GUTTER, GUTTER)
        column.setSpacing(GUTTER)
        column.addLayout(head)
        column.addWidget(subtitle)
        column.addLayout(body, 1)

    def _restyle(self) -> None:
        self.setStyleSheet(_sheet())

    def _redress(self) -> None:
        self._done.setIcon(icons.icon(_CLOSE))

    def _show_section(self, index: int) -> None:
        if not 0 <= index < len(self._sections):
            return
        section = self._sections[index]
        self._offer_reset(section)
        if section.body is not None:
            self._pages.setCurrentWidget(section.body)
            return
        self._placeholder.retell(section.name, section.gloss)
        self._pages.setCurrentWidget(self._placeholder)

    def _offer_reset(self, section: Section) -> None:
        if self._reset is None:
            return
        self._reset.setVisible(section.reset is not None)
        if section.reset is None:
            return
        self._reset.setText(f"reset {section.name}")
        self._reset.setToolTip(f"Put {section.name} back to what it came with")

    def _put_back(self) -> None:
        index = self.nav.current()
        if not 0 <= index < len(self._sections):
            return
        reset = self._sections[index].reset
        if reset is not None:
            reset()


class _Placeholder(QFrame):
    """Stand-in for a section with no body yet."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("placeholder")

        self._name = QLabel()
        self._name.setObjectName("name")
        self._gloss = QLabel()
        self._gloss.setObjectName("gloss")
        self._gloss.setWordWrap(True)

        nothing = QLabel("nothing here yet")
        nothing.setObjectName("empty")

        column = QVBoxLayout(self)
        column.setContentsMargins(GUTTER, GUTTER, GUTTER, GUTTER)
        column.setSpacing(2)
        column.addWidget(self._name)
        column.addWidget(self._gloss)
        column.addSpacing(GUTTER)
        column.addWidget(nothing)
        column.addStretch(1)

    def retell(self, name: str, gloss: str) -> None:
        self._name.setText(name)
        self._gloss.setText(gloss)
