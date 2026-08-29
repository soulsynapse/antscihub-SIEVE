"""Two-column grid of named facts about one thing, aligned on the widest name."""

from __future__ import annotations

from typing import NamedTuple, Sequence

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QGridLayout, QLabel, QSizePolicy, QWidget

from sieve.gui import metrics, palette
from sieve.gui.palette import DIM, TEXT, rgb

ABSENT = "—"

_LEAD = 5

_GAP = 18


def sheet() -> str:
    """Label rules for callers that set an ancestor sheet (which would override these)."""
    return f"""
        #factname {{
            color: {rgb(DIM)};
            background: transparent;
            border: 0;
        }}
        #factvalue {{
            color: {rgb(TEXT)};
            background: transparent;
            border: 0;
        }}
        #factabsent {{
            color: {rgb(DIM)};
            background: transparent;
            border: 0;
        }}
    """


class Fact(NamedTuple):
    """A named datum; both sides are caller-formatted strings."""

    name: str
    value: str = ""


class Facts(QWidget):
    """Grid of name–value pairs. No gestures; values elide, names do not."""

    def __init__(
        self,
        facts: Sequence[Fact] = (),
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._facts: tuple[Fact, ...] = ()
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(_GAP)
        self._grid.setVerticalSpacing(_LEAD)
        self._grid.setColumnStretch(1, 1)

        self.set_facts(facts)
        self.setStyleSheet(sheet())
        # Bound methods so PySide6 drops the connection when the receiver dies.
        palette.CHANGED.connect(self._restyle)
        metrics.CHANGED.connect(self._resize)

    def facts(self) -> tuple[Fact, ...]:
        return self._facts

    def set_facts(self, facts: Sequence[Fact]) -> None:
        """Replace all facts at once (the widest name sets the column width)."""
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        self._facts = tuple(facts)
        for row, fact in enumerate(self._facts):
            name = QLabel(fact.name)
            name.setObjectName("factname")
            self._grid.addWidget(name, row, 0, Qt.AlignmentFlag.AlignTop)
            self._grid.addWidget(_Value(fact.value), row, 1)

        self._resize()

    def _restyle(self) -> None:
        self.setStyleSheet(sheet())
        self.update()

    def _resize(self) -> None:
        # Set as a font (not in the sheet) so _Value sees a FontChange and re-elides.
        points = metrics.pt("name")
        for index in range(self._grid.count()):
            widget = self._grid.itemAt(index).widget()
            if widget is None:
                continue
            font = widget.font()
            font.setPointSize(points)
            widget.setFont(font)
        self.updateGeometry()
        self.update()


class _Value(QLabel):
    """Eliding label that holds the full string for re-elide on resize."""

    def __init__(self, text: str) -> None:
        super().__init__()
        self._full = text
        self.setObjectName("factvalue" if text else "factabsent")
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._elide()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._elide()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.FontChange:
            self._elide()

    def _elide(self) -> None:
        text = self._full or ABSENT
        super().setText(
            self.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, self.width())
        )
