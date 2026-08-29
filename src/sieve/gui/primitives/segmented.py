"""Segmented bar: a fixed few side by side, exactly one lit."""

from __future__ import annotations

from typing import Sequence

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QSizePolicy, QWidget

from sieve.gui import metrics, palette
from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, PANEL_HOT, TEXT, mix, rgb
from sieve.gui.primitives.field import EDGE, RADIUS, RING_GAP, RING_W, ring
from sieve.gui.primitives.nav import MARK_W

_PAD_X = 10
_PAD_Y = 6


class Segmented(QWidget):
    """A row of alternatives with one of them lit."""

    chosen = Signal(int)

    def __init__(
        self,
        options: Sequence[str],
        current: int = 0,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("segmented")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._current = -1
        self._segments: list[QPushButton] = []

        row = QHBoxLayout(self)
        # Margins reserve room for the painted focus ring.
        row.setContentsMargins(RING_GAP, RING_GAP, RING_GAP, RING_GAP)
        row.setSpacing(0)
        for index, text in enumerate(options):
            segment = QPushButton(text)
            segment.setObjectName("segment")
            segment.setCursor(Qt.CursorShape.PointingHandCursor)
            segment.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            segment.clicked.connect(lambda _=False, index=index: self.select(index))
            row.addWidget(segment)
            self._segments.append(segment)

        self._current = max(0, min(len(self._segments) - 1, current)) if self._segments else -1
        self._resize()
        # Bound methods so PySide6 drops the connection when the receiver dies.
        palette.CHANGED.connect(self._dress)
        metrics.CHANGED.connect(self._resize)

    def current(self) -> int:
        """The option that is on, or -1 while there are none."""
        return self._current

    def select(self, index: int) -> None:
        """Light an option; out of range is a no-op."""
        if not 0 <= index < len(self._segments) or index == self._current:
            return
        self._current = index
        self._dress()
        self.chosen.emit(index)

    def step(self, delta: int) -> None:
        """Move by *delta*, clamped to the ends (no wrap)."""
        if not self._segments:
            return
        self.select(max(0, min(len(self._segments) - 1, self._current + delta)))

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            self.step(-1 if key == Qt.Key.Key_Left else +1)
            event.accept()
            return
        super().keyPressEvent(event)

    def _resize(self) -> None:
        if not self._segments:
            return
        font = self.font()
        font.setPointSize(metrics.pt("name"))
        self.setFont(font)
        text = self.fontMetrics()
        width = max(text.horizontalAdvance(s.text()) for s in self._segments) + 2 * _PAD_X
        for segment in self._segments:
            segment.setFont(font)
            segment.setFixedWidth(width)
        self._dress()
        self.updateGeometry()

    def _dress(self) -> None:
        edge = rgb(mix(LINE, TEXT, EDGE))
        last = len(self._segments) - 1
        for index, segment in enumerate(self._segments):
            on = index == self._current
            left = RADIUS if index == 0 else 0
            right = RADIUS if index == last else 0
            segment.setStyleSheet(f"""
                #segment {{
                    background: {rgb(PANEL)};
                    color: {rgb(TEXT if on else DIM)};
                    border: 1px solid {edge};
                    border-left-width: {1 if index == 0 else 0}px;
                    border-bottom: {MARK_W}px solid {rgb(ACCENT if on else LINE)};
                    border-top-left-radius: {left}px;
                    border-bottom-left-radius: {left}px;
                    border-top-right-radius: {right}px;
                    border-bottom-right-radius: {right}px;
                    padding: {_PAD_Y}px {_PAD_X}px;
                    font-size: {metrics.pt("name")}pt;
                }}
                #segment:hover {{
                    background: {rgb(PANEL_HOT)};
                    color: {rgb(TEXT)};
                }}
                #segment:disabled {{
                    background: {rgb(PANEL_HOT)};
                    color: {rgb(DIM)};
                    border-bottom-color: {rgb(LINE)};
                }}
            """)

    def paintEvent(self, event) -> None:
        del event
        if not self.hasFocus():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        inset = RING_W / 2
        box = QRectF(self.rect()).adjusted(
            RING_GAP - inset,
            RING_GAP - inset,
            inset - RING_GAP,
            inset - RING_GAP,
        )
        painter.setPen(QPen(ring(), RING_W))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(box, RADIUS + inset, RADIUS + inset)
        painter.end()
