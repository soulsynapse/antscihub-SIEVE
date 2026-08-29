"""Titled panel with four verb icons; emits signals but does not act."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal, SignalInstance
from PySide6.QtGui import QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLayout,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from sieve.gui import icons, metrics, palette
from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, TEXT, rgb
from sieve.gui.primitives import meter

_INSET = 8

_RULE_PAST = 26
_RULE_H = 1
_RULE_PAD = 2

_HOVER_EDGE = 0.22

_OPEN = "arrow-right"
_SWAP = "arrow-right-left"
_PIN = "pin"
_REMOVE = "x"


class Card(QFrame):
    """Titled panel with four verb icons and a body layout."""

    selected = Signal()
    opened = Signal()
    swapped = Signal()
    pinned = Signal()   # only emitted when not already pinned
    removed = Signal()  # only emitted when removable

    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self._pinned = False
        self._selected = False
        self._hovered = False
        self._meter: float | None = None

        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)

        self._head = QWidget()
        head = QHBoxLayout(self._head)
        head.setContentsMargins(_INSET, 6, 6, _RULE_PAD)
        head.setSpacing(4)
        self._title = QLabel(title)
        self._title.setObjectName("title")
        head.addWidget(self._title)
        # Stretch, not expanded label — rule is measured off the title's right edge.
        head.addStretch(1)

        self._open = self._button(_OPEN, "open", "Open this card's settings", self.opened)
        self._swap = self._button(_SWAP, "swap", "Swap for another tool", self.swapped)
        self._pin = self._button(_PIN, "pin", "Pin below the canvas", self.pinned)
        self._remove = self._button(_REMOVE, "remove", "Remove this", self.removed)
        self._verbs = QWidget()
        row = QHBoxLayout(self._verbs)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        for button in (self._open, self._swap, self._pin, self._remove):
            row.addWidget(button)
        head.addWidget(self._verbs)

        self._fade = QGraphicsOpacityEffect(self._verbs)
        self._fade.setOpacity(0.0)
        self._verbs.setGraphicsEffect(self._fade)
        column.addWidget(self._head)

        self._body = QVBoxLayout()
        self._body.setContentsMargins(_INSET, 8, _INSET, 8)
        self._body.setSpacing(4)
        column.addLayout(self._body)

        self._dress()
        palette.CHANGED.connect(self._restyle)
        metrics.CHANGED.connect(self._remeasure)

    def _button(
        self, glyph: str, name: str, tip: str, signal: SignalInstance
    ) -> QToolButton:
        button = QToolButton()
        button.setObjectName(name)
        button.setIcon(icons.icon(glyph))
        button.setIconSize(QSize(icons.SIZE, icons.SIZE))
        button.setAutoRaise(True)
        button.setToolTip(tip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(signal)
        return button

    # -- what it holds -----------------------------------------------------

    def body(self) -> QVBoxLayout:
        """The room under the head, for the caller to fill."""
        return self._body

    def add_row(self, row: QWidget | QLayout) -> None:
        if isinstance(row, QLayout):
            self._body.addLayout(row)
        else:
            self._body.addWidget(row)

    def set_title(self, title: str) -> None:
        self._title.setText(title)
        self.update()

    # -- what it wears -----------------------------------------------------

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._fade.setOpacity(1.0 if (selected or self._hovered) else 0.0)
        self.update()

    def is_selected(self) -> bool:
        return self._selected

    def set_meter(self, full: float | None) -> None:
        """None removes the foot entirely; 0.0 shows an empty groove."""
        self._meter = None if full is None else max(0.0, min(1.0, full))
        room = meter.HEIGHT if self._meter is not None else 0
        self.layout().setContentsMargins(0, 0, 0, room)
        self.update()

    def set_pinned(self, pinned: bool) -> None:
        # Accent the disabled pixmap too — Qt draws only the Disabled pixmap
        # when the button is disabled, so normal-only accent would go grey.
        self._pinned = pinned
        ink = ACCENT if pinned else DIM
        self._pin.setIcon(
            icons.icon(_PIN, normal=ink, disabled=ink if pinned else LINE, filled=pinned)
        )
        self._pin.setEnabled(not pinned)
        self._pin.setToolTip(
            "Already pinned below the canvas" if pinned else "Pin below the canvas"
        )

    def is_pinned(self) -> bool:
        return self._pinned

    def set_removable(self, removable: bool, reason: str = "") -> None:
        self._remove.setEnabled(removable)
        self._remove.setToolTip("Remove this" if removable else reason)

    def set_swappable(self, swappable: bool, reason: str = "") -> None:
        self._swap.setEnabled(swappable)
        self._swap.setToolTip("Swap for another tool" if swappable else reason)

    def _dress(self) -> None:
        self.setStyleSheet(f"""
            #title {{
                color: {rgb(TEXT)};
                font-size: {metrics.pt("name")}pt;
                font-weight: 600;
            }}
            QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
        """)

    def _restyle(self) -> None:
        # Icons are pixmaps baked at creation time — must be rebuilt on palette change.
        for button, glyph in (
            (self._open, _OPEN),
            (self._swap, _SWAP),
            (self._remove, _REMOVE),
        ):
            button.setIcon(icons.icon(glyph))
        self.set_pinned(self._pinned)
        self._dress()
        self.update()

    def _remeasure(self) -> None:
        # Separate from _restyle — size changes don't need icon rebuilds.
        self._dress()
        self.update()

    # -- what it draws -----------------------------------------------------

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # Inset 0.5px so a 1px pen doesn't clip at the widget edge.
        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        corner = metrics.radius()
        shape = QPainterPath()
        shape.addRoundedRect(box, corner, corner)
        painter.fillPath(shape, PANEL)

        if self._meter is not None:
            painter.save()
            painter.setClipPath(shape)
            meter.draw(
                painter,
                QRectF(box.left(), box.bottom() - meter.HEIGHT, box.width(), meter.HEIGHT),
                self._meter,
                current=self._selected,
                round_ends=False,
            )
            painter.restore()

        y = self._head.geometry().bottom() + 0.5
        end = self._title.mapTo(self, self._title.rect().topRight()).x() + _RULE_PAST
        painter.setPen(QPen(LINE, _RULE_H))
        painter.drawLine(
            QPointF(_INSET, y), QPointF(min(end, box.right() - _INSET), y)
        )

        if self._selected:
            edge = ACCENT
        elif self._hovered:
            edge = palette.mix(LINE, TEXT, _HOVER_EDGE)
        else:
            edge = LINE
        painter.setPen(QPen(edge, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(shape)
        painter.end()

    # -- what the pointer does ---------------------------------------------

    def enterEvent(self, event) -> None:
        self._hovered = True
        self._fade.setOpacity(1.0)
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self._fade.setOpacity(1.0 if self._selected else 0.0)
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.opened.emit()
        super().mouseDoubleClickEvent(event)
