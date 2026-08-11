"""The rest of the interface in the card's dress, in the toolkit that draws it.

`paper_cards.py` settles the step card. This settles everything around it —
buttons, fields, toggles, the ruled table, the inset-row menu, underline tabs,
banners and the transient set, status pills, the cost meter, and the type scale
— in the options chosen from the browser sheet: table A, menu A, tabs A.

Tokens and the font helper are imported from `paper_cards` rather than copied,
so the palette has one home and a change to it reaches both files. The idiom
that makes these a family rather than a light UI kit is the partial rule: a
hairline that meets the left edge of the thing it heads and stops short of the
right. It is on every section header here, on the dialog, and under the
selected tab.

Five primitives are painted rather than styled, because Qt's stylesheet cannot
express them: the focus ring (an outer glow, not a border), the checkbox tick,
the switch, the table's selection mark, and the cost meter (clipped by the
corner it runs into). Each says so where it is defined.

Run: `uv run python mockup/paper_primitives.py`
Screenshot: `uv run python mockup/paper_primitives.py --shot out.png [--height N]`
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QAction, QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from paper_cards import (
    BODY_PX,
    CARD,
    COST,
    COST_TEXT,
    CURRENT,
    FIELD_LINE,
    GROUND,
    INK,
    INK_2,
    LABEL,
    LINE,
    LINE_HOVER,
    METER,
    METER_H,
    NAME_PX,
    NAME_WEIGHT,
    RADIUS,
    RING,
    SELECT,
    TRACK,
    Figure,
    font,
)

#: The wash behind a selected row and a lit tab; the danger pair; the one dark
#: surface in the scheme, which is the tooltip.
SELECT_WASH = QColor("#eef3fd")
DANGER = QColor("#c0392b")
DANGER_WASH = QColor("#fdf0ee")
DANGER_LINE = QColor("#e6c8c3")
TIP_BG = QColor("#22262c")
TIP_INK = QColor("#f2f4f7")

RULE_W = 190  #: how far a section header's rule runs before it stops


def hexed(colour: QColor) -> str:
    return colour.name()


# ---------------------------------------------------------------------------
# Furniture


class SectionHead(QWidget):
    """A title over a rule that meets the left edge and stops short of the right."""

    def __init__(self, title: str, note: str, rule: int = RULE_W) -> None:
        super().__init__()
        self._rule = rule
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 9)
        column.setSpacing(3)
        head = QLabel(title)
        head.setFont(font(19, display=True))
        head.setStyleSheet(f"color: {hexed(INK)};")
        column.addWidget(head)
        if note:
            caption = QLabel(note)
            caption.setFont(font(12.5))
            caption.setWordWrap(True)
            caption.setStyleSheet(f"color: {hexed(LABEL)};")
            column.addWidget(caption)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setPen(QPen(LINE, 1))
        y = self.height() - 0.5
        painter.drawLine(QPointF(0, y), QPointF(self._rule, y))
        painter.end()


class Panel(QFrame):
    """One demo, in the same white card the stack is made of."""

    def __init__(self, title: str, note: str) -> None:
        super().__init__()
        self._title_w = 150
        self.setStyleSheet(
            f"Panel {{ background: {hexed(CARD)}; border: 1px solid {hexed(LINE)};"
            f" border-radius: {RADIUS}px; }}"
        )
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)

        head = QWidget()
        row = QHBoxLayout(head)
        row.setContentsMargins(16, 10, 16, 9)
        row.setSpacing(10)
        name = QLabel(title)
        name.setFont(font(NAME_PX, weight=NAME_WEIGHT, display=True))
        name.setStyleSheet(f"color: {hexed(INK)};")
        row.addWidget(name)
        caption = QLabel(note)
        caption.setFont(font(12.5))
        caption.setStyleSheet(f"color: {hexed(LABEL)};")
        row.addWidget(caption)
        row.addStretch(1)
        self._head = head
        column.addWidget(head)

        self.body = QWidget()
        self.body_layout = QHBoxLayout(self.body)
        self.body_layout.setContentsMargins(16, 18, 16, 20)
        self.body_layout.setSpacing(14)
        column.addWidget(self.body)

        self._verdict = QLabel()
        self._verdict.setWordWrap(True)
        self._verdict.setFont(font(12.5))
        self._verdict.setStyleSheet(
            f"color: {hexed(LABEL)}; border-top: 1px solid {hexed(TRACK)}; padding: 10px 16px 12px;"
        )
        self._verdict.hide()
        column.addWidget(self._verdict)

    def verdict(self, text: str) -> None:
        self._verdict.setText(text)
        self._verdict.show()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setPen(QPen(LINE, 1))
        y = self._head.geometry().bottom() + 0.5
        painter.drawLine(QPointF(24, y), QPointF(24 + self._title_w, y))
        painter.end()


# ---------------------------------------------------------------------------
# Buttons


_BUTTON_QSS = {
    "primary": (
        f"background: {hexed(SELECT)}; color: #ffffff; border: 1px solid {hexed(SELECT)};",
        "background: #2662d4; border-color: #2662d4;",
    ),
    "default": (
        f"background: {hexed(CARD)}; color: {hexed(INK)}; border: 1px solid {hexed(FIELD_LINE)};",
        f"background: #fbfbfc; border-color: {hexed(LINE_HOVER)};",
    ),
    "subtle": (
        f"background: {hexed(TRACK)}; color: {hexed(INK)}; border: 1px solid {hexed(TRACK)};",
        "background: #e4e6ea; border-color: #e4e6ea;",
    ),
    "ghost": (
        f"background: transparent; color: {hexed(INK_2)}; border: 1px solid transparent;",
        f"background: {hexed(TRACK)}; color: {hexed(INK)};",
    ),
    "danger": (
        f"background: {hexed(CARD)}; color: {hexed(DANGER)}; border: 1px solid {hexed(DANGER_LINE)};",
        f"background: {hexed(DANGER_WASH)}; border-color: #d9a9a2;",
    ),
}


def button(text: str, kind: str = "default", *, small: bool = False, enabled: bool = True) -> QPushButton:
    rest, hover = _BUTTON_QSS[kind]
    pad = "5px 10px" if small else "8px 14px"
    radius = 4 if small else RADIUS
    control = QPushButton(text)
    control.setFont(font(12 if small else 13))
    control.setCursor(Qt.CursorShape.PointingHandCursor)
    control.setEnabled(enabled)
    control.setStyleSheet(
        f"QPushButton {{ {rest} border-radius: {radius}px; padding: {pad}; }}"
        f"QPushButton:hover {{ {hover} }}"
        f"QPushButton:disabled {{ color: {hexed(LABEL)}; border-color: {hexed(TRACK)};"
        f" background: {hexed(TRACK)}; }}"
    )
    return control


class Segmented(QWidget):
    """One of a fixed set, always exactly one on — the walk's three positions."""

    def __init__(self, options: list[str], current: int = 0) -> None:
        super().__init__()
        self._current = current
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        self._buttons: list[QPushButton] = []
        for index, text in enumerate(options):
            control = QPushButton(text)
            control.setFont(font(12.5))
            control.setCursor(Qt.CursorShape.PointingHandCursor)
            control.setCheckable(True)
            control.setChecked(index == current)
            control.clicked.connect(lambda _=False, i=index: self.select(i))
            left = RADIUS if index == 0 else 0
            right = RADIUS if index == len(options) - 1 else 0
            control.setStyleSheet(
                f"QPushButton {{ background: {hexed(CARD)}; color: {hexed(INK_2)};"
                f" border: 1px solid {hexed(FIELD_LINE)};"
                f" border-left-width: {0 if index else 1}px;"
                f" border-top-left-radius: {left}px; border-bottom-left-radius: {left}px;"
                f" border-top-right-radius: {right}px; border-bottom-right-radius: {right}px;"
                f" padding: 6px 12px; }}"
                f"QPushButton:checked {{ background: {hexed(SELECT_WASH)}; color: {hexed(SELECT)}; }}"
            )
            self._buttons.append(control)
            row.addWidget(control)
        row.addStretch(1)

    def select(self, index: int) -> None:
        self._current = index
        for i, control in enumerate(self._buttons):
            control.setChecked(i == index)


# ---------------------------------------------------------------------------
# Fields


class Field(QWidget):
    """A labelled control, with the focus ring painted around it.

    The ring is 3px outside the border at 14%, and a stylesheet cannot draw
    outside a widget's own rect — so the wrapper is what paints it. A thicker
    border on focus would have been the stylesheet answer and it moves every
    neighbour by a pixel, which in a row of five crop fields reads as a twitch.
    """

    def __init__(self, label: str, control: QWidget, hint: str = "", *, error: bool = False) -> None:
        super().__init__()
        self._control = control
        self._error = error
        column = QVBoxLayout(self)
        column.setContentsMargins(3, 3, 3, 3)
        column.setSpacing(5)
        if label:
            caption = QLabel(label)
            caption.setFont(font(11.5))
            caption.setStyleSheet(f"color: {hexed(LABEL)};")
            column.addWidget(caption)
        column.addWidget(control)
        if hint:
            note = QLabel(hint)
            note.setFont(font(11.5))
            note.setStyleSheet(f"color: {hexed(DANGER if error else LABEL)};")
            column.addWidget(note)
        control.installEventFilter(self)

    def eventFilter(self, watched, event) -> bool:
        if watched is self._control and event.type() in (
            event.Type.FocusIn, event.Type.FocusOut
        ):
            self.update()
        return False

    def paintEvent(self, event) -> None:
        del event
        if not self._control.hasFocus():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        box = QRectF(self._control.geometry()).adjusted(-1.5, -1.5, 1.5, 1.5)
        painter.setPen(QPen(RING, 3))
        painter.drawRoundedRect(box, RADIUS + 1, RADIUS + 1)
        painter.end()


def _field_qss(invalid: bool = False) -> str:
    border = DANGER if invalid else FIELD_LINE
    return (
        f"background: {hexed(CARD)}; color: {hexed(INK)}; border: 1px solid {hexed(border)};"
        f" border-radius: {RADIUS}px; padding: 6px 9px;"
    )


def line_edit(text: str, *, width: int = 170, mono: bool = False, invalid: bool = False,
              enabled: bool = True, align_right: bool = False) -> QLineEdit:
    control = QLineEdit(text)
    control.setFont(font(BODY_PX, mono=mono))
    control.setFixedWidth(width)
    control.setEnabled(enabled)
    if align_right:
        control.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    control.setStyleSheet(
        f"QLineEdit {{ {_field_qss(invalid)} }}"
        f"QLineEdit:hover {{ border-color: {hexed(LINE_HOVER if not invalid else DANGER)}; }}"
        f"QLineEdit:focus {{ border-color: {hexed(SELECT if not invalid else DANGER)}; }}"
        f"QLineEdit:disabled {{ background: {hexed(TRACK)}; color: {hexed(LABEL)}; }}"
    )
    return control


def combo(items: list[str]) -> QComboBox:
    control = QComboBox()
    control.addItems(items)
    control.setFont(font(BODY_PX))
    control.setFixedWidth(150)
    control.setStyleSheet(
        f"QComboBox {{ {_field_qss()} }}"
        f"QComboBox:hover {{ border-color: {hexed(LINE_HOVER)}; }}"
        f"QComboBox::drop-down {{ border: 0; width: 16px; }}"
        f"QComboBox QAbstractItemView {{ background: {hexed(CARD)}; color: {hexed(INK)};"
        f" border: 1px solid {hexed(LINE)}; selection-background-color: {hexed(SELECT_WASH)};"
        f" selection-color: {hexed(SELECT)}; }}"
    )
    return control


def unit_field(value: str, unit: str) -> QWidget:
    """A number and the unit it is in, joined so the pair reads as one control."""
    wrap = QWidget()
    row = QHBoxLayout(wrap)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(0)
    number = line_edit(value, width=84, mono=True, align_right=True)
    number.setStyleSheet(
        f"QLineEdit {{ background: {hexed(CARD)}; color: {hexed(INK)};"
        f" border: 1px solid {hexed(FIELD_LINE)}; border-top-right-radius: 0;"
        f" border-bottom-right-radius: 0; border-top-left-radius: {RADIUS}px;"
        f" border-bottom-left-radius: {RADIUS}px; padding: 6px 9px; }}"
        f"QLineEdit:focus {{ border-color: {hexed(SELECT)}; }}"
    )
    suffix = QLabel(unit)
    suffix.setFont(font(11.5, mono=True))
    suffix.setStyleSheet(
        f"color: {hexed(LABEL)}; background: {hexed(TRACK)};"
        f" border: 1px solid {hexed(FIELD_LINE)}; border-left: 0;"
        f" border-top-right-radius: {RADIUS}px; border-bottom-right-radius: {RADIUS}px;"
        f" padding: 6px 9px;"
    )
    row.addWidget(number)
    row.addWidget(suffix)
    return wrap


# ---------------------------------------------------------------------------
# Toggles. Painted, because a stylesheet checkbox needs an image for its tick
# and a switch has no Qt widget at all.


class Check(QAbstractButton):
    def __init__(self, text: str, checked: bool = False, radio: bool = False) -> None:
        super().__init__()
        self.setCheckable(True)
        self.setChecked(checked)
        self._radio = radio
        self.setText(text)
        self.setFont(font(13))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        metrics = self.fontMetrics()
        self.setFixedHeight(20)
        self.setMinimumWidth(metrics.horizontalAdvance(text) + 30)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        box = QRectF(1, 3, 14, 14)
        if self._radio:
            path = QPainterPath()
            path.addEllipse(box)
        else:
            path = QPainterPath()
            path.addRoundedRect(box, 3, 3)
        painter.fillPath(path, SELECT if self.isChecked() else CARD)
        painter.setPen(QPen(SELECT if self.isChecked() else FIELD_LINE, 1))
        painter.drawPath(path)
        if self.isChecked():
            painter.setPen(QPen(QColor("#ffffff"), 1.6))
            if self._radio:
                painter.setBrush(QColor("#ffffff"))
                painter.drawEllipse(box.center(), 3, 3)
            else:
                tick = QPainterPath(QPointF(box.left() + 3.2, box.center().y()))
                tick.lineTo(box.left() + 6, box.bottom() - 4)
                tick.lineTo(box.right() - 3, box.top() + 4)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(tick)
        painter.setPen(QPen(INK))
        painter.setFont(self.font())
        painter.drawText(
            QRectF(22, 0, self.width() - 22, self.height()),
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            self.text(),
        )
        painter.end()


class Switch(QAbstractButton):
    """Only where flipping acts immediately — the scrubber's handles, not the write list."""

    def __init__(self, text: str, checked: bool = False) -> None:
        super().__init__()
        self.setCheckable(True)
        self.setChecked(checked)
        self.setText(text)
        self.setFont(font(13))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(22)
        self.setMinimumWidth(self.fontMetrics().horizontalAdvance(text) + 50)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        track = QRectF(1, 2, 32, 18)
        painter.setBrush(SELECT if self.isChecked() else TRACK)
        painter.setPen(QPen(SELECT if self.isChecked() else FIELD_LINE, 1))
        painter.drawRoundedRect(track, 9, 9)
        knob = QPointF(track.left() + (23 if self.isChecked() else 9), track.center().y())
        painter.setPen(QPen(QColor(18, 20, 24, 40), 1))
        painter.setBrush(CARD)
        painter.drawEllipse(knob, 6.5, 6.5)
        painter.setPen(QPen(INK))
        painter.setFont(self.font())
        painter.drawText(
            QRectF(42, 0, self.width() - 42, self.height()),
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            self.text(),
        )
        painter.end()


class Slider(QWidget):
    """The control the loop exists for: value above the track, never beside it,
    because beside means the track moves as the number's width changes."""

    def __init__(self, name: str, value: str, low: int, high: int, at: int) -> None:
        super().__init__()
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(5)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        caption = QLabel(name)
        caption.setFont(font(11.5))
        caption.setStyleSheet(f"color: {hexed(LABEL)};")
        self._value = QLabel(value)
        self._value.setFont(font(11.5, mono=True))
        self._value.setStyleSheet(f"color: {hexed(INK)};")
        row.addWidget(caption)
        row.addStretch(1)
        row.addWidget(self._value)
        column.addLayout(row)

        bar = QSlider(Qt.Orientation.Horizontal)
        bar.setRange(low, high)
        bar.setValue(at)
        bar.setFixedWidth(230)
        bar.setStyleSheet(
            f"QSlider::groove:horizontal {{ height: 4px; background: {hexed(TRACK)}; border-radius: 2px; }}"
            f"QSlider::sub-page:horizontal {{ background: {hexed(SELECT)}; border-radius: 2px; }}"
            f"QSlider::handle:horizontal {{ width: 13px; height: 13px; margin: -5px 0;"
            f" border-radius: 7px; background: {hexed(CARD)};"
            f" border: 1px solid {hexed(SELECT)}; }}"
        )
        column.addWidget(bar)


# ---------------------------------------------------------------------------
# Meters. The one mark on a card that is not text: cost, and only cost.


class Meter(QWidget):
    """The bar a card wears at its foot, standing on its own.

    Painted rather than styled for the same reason it is on the card: it spans
    the full width and so runs into the corner, and a stylesheet bar inside a
    rounded frame either squares that corner off or has to be inset from it.
    Clipping is what keeps the card's radius the card's, so the bar carries no
    radius of its own — the rounded rect it is clipped by is grown upward past
    the top edge, leaving the top corners square where they meet the body.

    Neutral below the step's share of the frame, amber past it. Selection never
    reaches this bar: lighting it would make a selected cheap step and a
    selected expensive one the same colour, which is the distinction it exists
    to draw.
    """

    def __init__(self, fraction: float, hot: bool = False, *, radius: int = RADIUS) -> None:
        super().__init__()
        self._fraction = fraction
        self._hot = hot
        self._radius = radius
        self.setFixedHeight(METER_H)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        box = QRectF(self.rect())
        shape = QPainterPath()
        shape.addRoundedRect(box.adjusted(0, -self._radius, 0, 0), self._radius, self._radius)
        painter.setClipPath(shape)
        painter.fillRect(box, TRACK)
        painter.fillRect(
            QRectF(box.left(), box.top(), box.width() * self._fraction, box.height()),
            COST if self._hot else METER,
        )
        painter.end()


def meter_stub(name: str, cost: str, fraction: float, hot: bool = False) -> QFrame:
    """A card's foot and nothing above it — the meter has to be shown in a corner."""
    frame = QFrame()
    frame.setStyleSheet(
        f"QFrame {{ background: {hexed(CARD)}; border: 1px solid {hexed(LINE)};"
        f" border-radius: {RADIUS}px; }}"
    )
    column = QVBoxLayout(frame)
    column.setContentsMargins(0, 0, 0, 0)
    column.setSpacing(0)
    head = QWidget()
    row = QHBoxLayout(head)
    row.setContentsMargins(14, 10, 14, 11)
    label = QLabel(name)
    label.setFont(font(NAME_PX, weight=NAME_WEIGHT, display=True))
    label.setStyleSheet(f"color: {hexed(INK)}; border: 0;")
    ms = QLabel(cost)
    ms.setFont(font(12.5, mono=True))
    ms.setStyleSheet(f"color: {hexed(COST_TEXT if hot else LABEL)}; border: 0;")
    row.addWidget(label)
    row.addStretch(1)
    row.addWidget(ms)
    column.addWidget(head)
    column.addWidget(Meter(fraction, hot))
    return frame


# ---------------------------------------------------------------------------
# The ruled table (option A). Built from rows rather than a QTableWidget: the
# selected row's 2px left mark is the card's own selection signal, and a view's
# delegate cannot paint outside its cell rects to draw it.


class Cellbar(QWidget):
    """`Meter`'s sibling inside a cell: rounded at both ends, because it floats
    in a row rather than running into a corner."""

    def __init__(self, fraction: float, hot: bool = False) -> None:
        super().__init__()
        self._fraction = fraction
        self._hot = hot
        self.setFixedSize(84, 4)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(TRACK)
        painter.drawRoundedRect(QRectF(0, 0, self.width(), 4), 2, 2)
        painter.setBrush(COST if self._hot else METER)
        painter.drawRoundedRect(QRectF(0, 0, self.width() * self._fraction, 4), 2, 2)
        painter.end()


class Num(str):
    """A cell that belongs in the numeric column: right-aligned, mono, tabular."""



class Row(QWidget):
    picked = Signal(int)

    COLUMNS = (34, 190, 200, 90, 90, 100)

    def __init__(self, index: int, cells: list, *, header: bool = False, selected: bool = False) -> None:
        super().__init__()
        self._index = index
        self._header = header
        self._selected = selected
        self._hovered = False
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setFixedHeight(34 if header else 38)
        if not header:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 0, 14, 0)
        row.setSpacing(0)
        for width, cell in zip(self.COLUMNS, cells):
            holder = QWidget()
            holder.setFixedWidth(width)
            inner = QHBoxLayout(holder)
            inner.setContentsMargins(0, 0, 12, 0)
            inner.setSpacing(0)
            if isinstance(cell, str):
                # A column is numeric because it was declared one, not because
                # its text happens to be digits — `1.2 MB` is a quantity and
                # sniffing would have left it in the text column's alignment.
                numeric = isinstance(cell, Num)
                label = QLabel(cell)
                if header:
                    label.setFont(font(9.5, mono=True))
                    label.setStyleSheet(f"color: {hexed(LABEL)}; letter-spacing: 1.3px;")
                    label.setText(cell.upper())
                else:
                    label.setFont(font(12.5, mono=True) if numeric else font(13))
                    label.setStyleSheet(f"color: {hexed(INK)};")
                if numeric:
                    inner.addStretch(1)
                inner.addWidget(label)
                if not numeric:
                    inner.addStretch(1)
            elif cell is not None:
                inner.addWidget(cell)
                inner.addStretch(1)
            row.addWidget(holder)
        row.addStretch(1)

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._hovered = True
        self.update()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._hovered = False
        self.update()

    def mousePressEvent(self, event) -> None:
        if not self._header and event.button() == Qt.MouseButton.LeftButton:
            self.picked.emit(self._index)
            event.accept()
            return
        super().mousePressEvent(event)

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        box = QRectF(self.rect())
        if self._selected:
            painter.fillRect(box, SELECT_WASH)
        elif self._hovered and not self._header:
            painter.fillRect(box, QColor("#fafbfc"))
        painter.setPen(QPen(LINE if self._header else TRACK, 1))
        painter.drawLine(QPointF(0, box.bottom() - 0.5), QPointF(box.right(), box.bottom() - 0.5))
        if self._selected:
            painter.fillRect(QRectF(0, 0, 2, box.height()), SELECT)
        painter.end()


class RuledTable(QWidget):
    def __init__(self, header: list, rows: list[list], selected: int = 0) -> None:
        super().__init__()
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        column.addWidget(Row(-1, header, header=True))
        self._rows: list[Row] = []
        for index, cells in enumerate(rows):
            row = Row(index, cells, selected=index == selected)
            row.picked.connect(self.select)
            self._rows.append(row)
            column.addWidget(row)

        foot = QWidget()
        line = QHBoxLayout(foot)
        line.setContentsMargins(14, 10, 14, 12)
        summary = QLabel("2 of 4 ticked · 1.2 MB to write")
        summary.setFont(font(12.5))
        summary.setStyleSheet(f"color: {hexed(LABEL)};")
        line.addWidget(summary)
        line.addStretch(1)
        line.addWidget(button("Run", "primary", small=True))
        column.addWidget(foot)

    def select(self, index: int) -> None:
        for i, row in enumerate(self._rows):
            row.set_selected(i == index)


# ---------------------------------------------------------------------------
# Menu (option A): inset rows, grouped, shortcuts right. Drawn as a panel so it
# is visible standing still; the same styling is given to the real QMenu the
# demo button opens, which is what the app would actually use.


def _menu_qss() -> str:
    return (
        f"QMenu {{ background: {hexed(CARD)}; border: 1px solid {hexed(LINE)};"
        f" border-radius: {RADIUS}px; padding: 5px; }}"
        f"QMenu::item {{ padding: 6px 12px; border-radius: 4px; color: {hexed(INK)}; }}"
        f"QMenu::item:selected {{ background: {hexed(TRACK)}; }}"
        f"QMenu::item:disabled {{ color: {hexed(LABEL)}; }}"
        f"QMenu::separator {{ height: 1px; background: {hexed(TRACK)}; margin: 5px 6px; }}"
        f"QMenu::right-arrow {{ width: 10px; }}"
    )


class MenuPanel(QFrame):
    def __init__(self, groups: list[tuple[str, list[tuple[str, str, str]]]]) -> None:
        super().__init__()
        self.setStyleSheet(
            f"MenuPanel {{ background: {hexed(CARD)}; border: 1px solid {hexed(LINE)};"
            f" border-radius: {RADIUS}px; }}"
        )
        self.setFixedWidth(236)
        column = QVBoxLayout(self)
        column.setContentsMargins(5, 5, 5, 6)
        column.setSpacing(1)
        for group, items in groups:
            if group:
                caption = QLabel(group.upper())
                caption.setFont(font(9, mono=True))
                caption.setStyleSheet(f"color: {hexed(LABEL)}; padding: 7px 9px 3px; letter-spacing: 1.4px;")
                column.addWidget(caption)
            for text, key, kind in items:
                column.addWidget(self._item(text, key, kind))

    def _item(self, text: str, key: str, kind: str) -> QWidget:
        colour = {"on": SELECT, "danger": DANGER, "off": LABEL}.get(kind, INK)
        item = QWidget()
        item.setFixedHeight(28)
        row = QHBoxLayout(item)
        row.setContentsMargins(9, 0, 9, 0)
        label = QLabel(text)
        label.setFont(font(13))
        label.setStyleSheet(f"color: {hexed(colour)};")
        row.addWidget(label)
        row.addStretch(1)
        if key:
            shortcut = QLabel(key)
            shortcut.setFont(font(10.5, mono=True))
            shortcut.setStyleSheet(f"color: {hexed(LABEL)};")
            row.addWidget(shortcut)
        hover = TRACK if kind != "danger" else DANGER_WASH
        item.setStyleSheet(
            f"QWidget:hover {{ background: {hexed(hover)}; border-radius: 4px; }}"
        )
        item.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        return item


# ---------------------------------------------------------------------------
# Tabs (option A): 2px accent under the selected one, a hairline floor under
# the row. Painted, because QTabBar's own drawing is the platform's.


class Tabs(QWidget):
    def __init__(self, labels: list[str], current: int = 0) -> None:
        super().__init__()
        self._labels = labels
        self._current = current
        self._hover = -1
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)
        self.setFixedHeight(36)
        self._font = font(13)
        self._font_on = font(13, display=True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _spans(self) -> list[tuple[float, float]]:
        spans: list[tuple[float, float]] = []
        x = 0.0
        for index, text in enumerate(self._labels):
            metrics = self.fontMetrics()
            width = metrics.horizontalAdvance(text) + 24
            spans.append((x, width))
            x += width + 2
            del index
        return spans

    def _at(self, x: float) -> int:
        for index, (left, width) in enumerate(self._spans()):
            if left <= x <= left + width:
                return index
        return -1

    def mouseMoveEvent(self, event) -> None:
        self._hover = self._at(event.position().x())
        self.update()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._hover = -1
        self.update()

    def mousePressEvent(self, event) -> None:
        index = self._at(event.position().x())
        if index >= 0:
            self._current = index
            self.update()
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        floor = self.height() - 0.5
        painter.setPen(QPen(LINE, 1))
        painter.drawLine(QPointF(0, floor), QPointF(self.width(), floor))
        for index, (left, width) in enumerate(self._spans()):
            chosen = index == self._current
            painter.setFont(self._font_on if chosen else self._font)
            painter.setPen(QPen(INK if chosen or index == self._hover else INK_2))
            painter.drawText(
                QRectF(left, 0, width, self.height() - 6),
                int(Qt.AlignmentFlag.AlignCenter),
                self._labels[index],
            )
            if chosen:
                painter.setPen(QPen(SELECT, 2))
                y = self.height() - 1
                painter.drawLine(QPointF(left + 8, y), QPointF(left + width - 8, y))
        painter.end()


# ---------------------------------------------------------------------------
# Feedback


def banner(kind: str, title: str, body: str) -> QFrame:
    colour = {"info": SELECT, "warn": COST, "error": DANGER, "ok": CURRENT}[kind]
    frame = QFrame()
    frame.setStyleSheet(
        f"QFrame {{ background: {hexed(CARD)}; border: 1px solid {hexed(LINE)};"
        f" border-left: 3px solid {hexed(colour)}; border-radius: {RADIUS}px; }}"
    )
    row = QHBoxLayout(frame)
    row.setContentsMargins(13, 11, 13, 12)
    row.setSpacing(11)
    column = QVBoxLayout()
    column.setSpacing(2)
    head = QLabel(title)
    head.setFont(font(13, display=True))
    head.setStyleSheet(f"color: {hexed(INK)}; border: 0;")
    text = QLabel(body)
    text.setWordWrap(True)
    text.setFont(font(13))
    text.setStyleSheet(f"color: {hexed(INK_2)}; border: 0;")
    column.addWidget(head)
    column.addWidget(text)
    row.addLayout(column, 1)
    return frame


def pill(text: str, kind: str) -> QLabel:
    colour = {"ok": CURRENT, "busy": COST, "off": METER}.get(kind, LABEL)
    # The dot carries the state colour and the word carries the meaning, so a
    # pill is never colour alone. Fixed height, because a label in a row layout
    # stretches to the tallest thing beside it and a stretched pill is a box.
    label = QLabel(f"<span style='color:{hexed(colour)}'>●</span>&nbsp; {text}")
    label.setFont(font(11.5))
    label.setFixedHeight(22)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    label.setStyleSheet(
        f"color: {hexed(INK_2)}; border: 1px solid {hexed(LINE)}; border-radius: 11px;"
        f" padding: 0 10px;"
    )
    return label


# ---------------------------------------------------------------------------
# The sheet


class Sheet(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SIEVE v3 — Paper primitives")
        self.resize(1060, 1000)
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), GROUND)
        self.setPalette(palette)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        body = QWidget()
        column = QVBoxLayout(body)
        column.setContentsMargins(30, 28, 30, 60)
        column.setSpacing(0)

        title = QLabel("Paper primitives")
        title.setFont(font(30, display=True))
        title.setStyleSheet(f"color: {hexed(INK)};")
        column.addWidget(title)
        lede = QLabel(
            "Everything around the step card, in its dress: white on a near-neutral ground, "
            "6px radius, a border one shade darker on anything editable, blue for attention, "
            "amber for cost, green for current — and the partial rule wherever a header has to "
            "separate itself without dividing what it heads."
        )
        lede.setWordWrap(True)
        lede.setFont(font(14))
        lede.setStyleSheet(f"color: {hexed(INK_2)}; padding: 6px 0 0;")
        column.addWidget(lede)

        for head, panels in (
            (SectionHead("Buttons", "One filled button per screen; on the pipeline that is Run.", 150),
             [self._buttons()]),
            (SectionHead("Fields", "A field's border is one step darker than a card's — that is the whole of what makes it look editable.", 130),
             [self._fields()]),
            (SectionHead("Toggles and sliders", "A checkbox states a fact; a switch performs an action; a slider is what the loop exists for.", 200),
             [self._toggles()]),
            (SectionHead("Table", "Option A, ruled: hairlines per row, selection as the card's own 2px left mark.", 120),
             [self._table()]),
            (SectionHead("Menu and tabs", "Option A for both: inset rows with groups, and a 2px underline on the selected tab.", 175),
             [self._menu_and_tabs()]),
            (SectionHead("Feedback", "Blue informs, amber is working, red failed, green finished — the card's meanings, unchanged.", 130),
             [self._feedback()]),
            (SectionHead("Data and text", "The cost meter, status pills, key–value, a figure panel, and every size the app uses.", 155),
             [self._meters(), self._data(), self._text()]),
        ):
            column.addSpacing(34)
            column.addWidget(head)
            column.addSpacing(10)
            for panel in panels:
                column.addWidget(panel)
                column.addSpacing(14)

        column.addStretch(1)

        self.body = body  # kept so `--full` can grab the sheet past the screen's height
        scroll = QScrollArea()
        scroll.setWidget(body)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        outer.addWidget(scroll)

    # -- panels ------------------------------------------------------------
    def _buttons(self) -> Panel:
        panel = Panel("Emphasis", "filled · bordered · subtle · ghost · danger")
        for control in (
            button("Run", "primary"),
            button("Add step", "default"),
            button("Duplicate", "subtle"),
            button("Cancel", "ghost"),
            button("Remove step", "danger"),
            button("Save", "default", enabled=False),
        ):
            panel.body_layout.addWidget(control)
        panel.body_layout.addSpacing(10)
        panel.body_layout.addWidget(Segmented(["Project", "Pipeline", "Step"], 1))
        panel.body_layout.addStretch(1)
        panel.verdict(
            "The filled blue is scarce enough to mean something, and the danger button stays "
            "outlined so a destructive action is never the loudest thing on screen."
        )
        return panel

    def _fields(self) -> Panel:
        panel = Panel("Text, number, unit, invalid, disabled", "focus is a 3px ring, not a thicker border")
        # A grid rather than a row: six fields in one line is wider than any pane
        # they would really stand in, and the wrap is what a form does anyway.
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(14)
        fields = [
            Field("Project name", line_edit("colony-A shading")),
            Field("Block", line_edit("16", width=84, mono=True, align_right=True)),
            Field("Estimator", combo(["median", "mean", "minimum"])),
            Field("Window", unit_field("240", "frames")),
            Field("Floor", line_edit("-0.2", width=84, mono=True, align_right=True, invalid=True),
                  "Between 0 and 1.", error=True),
            Field("Source", line_edit("arena_r1.mp4", enabled=False)),
        ]
        for index, control in enumerate(fields):
            grid.addWidget(control, index // 3, index % 3, Qt.AlignmentFlag.AlignLeft)
        grid.setColumnStretch(3, 1)
        holder = QWidget()
        holder.setLayout(grid)
        panel.body_layout.addWidget(holder, 1)
        panel.verdict(
            "A border that grows on focus shifts everything beside it by a pixel — in a row of five "
            "crop fields that reads as the row twitching, so the ring is painted outside instead."
        )
        return panel

    def _toggles(self) -> Panel:
        panel = Panel("Choice and range", "checkbox · radio · switch · slider")
        panel.body_layout.addWidget(Check("Write the event table", True))
        panel.body_layout.addWidget(Check("Write the block series"))
        panel.body_layout.addWidget(Check("Per frame", True, radio=True))
        panel.body_layout.addWidget(Check("Windowed", radio=True))
        panel.body_layout.addWidget(Switch("Handles", True))
        panel.body_layout.addStretch(1)
        panel.body_layout.addWidget(Slider("Block size", "16 px", 4, 64, 16))
        panel.verdict(
            "Checkboxes for the write list, because it is a set of facts about what gets written; "
            "switches only where flipping acts immediately."
        )
        return panel

    def _table(self) -> Panel:
        panel = Panel("The write list", "option A · ruled")
        panel.body_layout.setContentsMargins(0, 0, 0, 0)
        table = RuledTable(
            ["", "Product", "From", Num("Rows"), Num("Size"), "Share"],
            [
                [Check("", True), "windowed count", "10 · windowed count", Num("18 442"), Num("1.2 MB"), Cellbar(0.09)],
                [Check("", True), "event table", "10 · windowed count", Num("96"), Num("12 KB"), Cellbar(0.04)],
                [Check(""), "block series", "8 · block signal", Num("1 297 K"), Num("84 MB"), Cellbar(0.74, hot=True)],
                [Check(""), "band power", "9 · morlet band", Num("432 K"), Num("27 MB"), Cellbar(0.31)],
            ],
        )
        panel.body_layout.addWidget(table)
        panel.verdict(
            "Hairlines are enough to track a row across six columns, and the selected row wears the "
            "card's signal — a 2px mark on the left edge — so selection means one thing app-wide."
        )
        return panel

    def _menu_and_tabs(self) -> Panel:
        panel = Panel("Context menu and view tabs", "option A · inset rows, underline")
        left = QVBoxLayout()
        left.setSpacing(12)
        left.addWidget(MenuPanel([
            ("This step", [("Open settings", "→", ""), ("Swap tool…", "S", ""),
                           ("Pinned below canvas", "P", "on")]),
            ("Chain", [("Add step after…", "A", ""), ("Move up", "", "off"),
                       ("Remove step", "Del", "danger")]),
        ]))
        opener = button("Right-click me for the real QMenu", "default")
        opener.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        menu = QMenu(opener)
        menu.setStyleSheet(_menu_qss())
        menu.addSection("This step")
        menu.addAction(QAction("Open settings", menu))
        menu.addAction(QAction("Swap tool…", menu))
        menu.addSeparator()
        remove = QAction("Remove step", menu)
        menu.addAction(remove)
        opener.customContextMenuRequested.connect(
            lambda point: menu.exec(opener.mapToGlobal(point))
        )
        left.addWidget(opener)
        left.addStretch(1)

        right = QVBoxLayout()
        right.setSpacing(14)
        right.addWidget(Tabs(["Pipeline", "Sources", "Output", "Notes"], 0))
        right.addWidget(banner("info", "Reading 6 sources",
                               "The chain runs once per source. Sources are replicates, not takes."))
        right.addStretch(1)

        panel.body_layout.addLayout(left)
        panel.body_layout.addSpacing(20)
        panel.body_layout.addLayout(right, 1)
        panel.verdict(
            "Group labels earn their line because the two groups act on different things — this "
            "step, and the chain around it."
        )
        return panel

    def _feedback(self) -> Panel:
        panel = Panel("Banners and the transient set", "colour on the left edge only")
        column = QVBoxLayout()
        column.setSpacing(9)
        column.addWidget(banner("warn", "Background is recomputing",
                                "Its window changed. Steps below it show their last result until it finishes."))
        column.addWidget(banner("error", "Nothing to write",
                                "Tick at least one product on the output step before running."))
        column.addWidget(banner("ok", "Wrote 2 files",
                                "windowed count · event table — in projects/colony-A/out"))

        side = QVBoxLayout()
        side.setSpacing(12)
        tip = QLabel("Swap for another image → image tool")
        tip.setFont(font(12))
        tip.setStyleSheet(
            f"background: {hexed(TIP_BG)}; color: {hexed(TIP_INK)}; border-radius: 4px; padding: 5px 9px;"
        )
        side.addWidget(tip)
        empty = QLabel("No steps yet\nAdd the first one to start the chain.")
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.setFont(font(13))
        empty.setStyleSheet(
            f"color: {hexed(LABEL)}; background: #fbfbfc; border: 1px dashed {hexed(FIELD_LINE)};"
            f" border-radius: {RADIUS}px; padding: 22px;"
        )
        side.addWidget(empty)
        side.addStretch(1)

        panel.body_layout.addLayout(column, 1)
        panel.body_layout.addSpacing(18)
        panel.body_layout.addLayout(side)
        panel.verdict(
            "The tooltip is the one dark surface in the scheme, because a white tooltip on a white "
            "card needs a shadow to be seen at all."
        )
        return panel

    def _meters(self) -> Panel:
        panel = Panel("Cost meter", "the card's foot · neutral under its share, amber past it")
        # Fractions are of the slowest step, the way the card scales it; the
        # colour turns on the mean, so the amber one is not simply the longest.
        for name, cost, fraction, hot in (
            ("background subtract", "2.4 ms", 0.11, False),
            ("morlet band", "9.8 ms", 0.44, False),
            ("block signal", "23.1 ms", 1.0, True),
        ):
            panel.body_layout.addWidget(meter_stub(name, cost, fraction, hot), 1)
        panel.verdict(
            "The bar is the only ink on a card that is not text, so it says one thing: cost. It is "
            "the same mark as the table's share column at another scale — full width and clipped by "
            "the corner there, rounded at both ends in a cell here."
        )
        return panel

    def _data(self) -> Panel:
        panel = Panel("Status and figure", "state as shape and colour, never colour alone")
        panel.body_layout.addWidget(pill("Current", "ok"))
        panel.body_layout.addWidget(pill("Recomputing", "busy"))
        panel.body_layout.addWidget(pill("Not run", "off"))

        pairs = QGridLayout()
        pairs.setHorizontalSpacing(18)
        pairs.setVerticalSpacing(5)
        for rowi, (key, value) in enumerate((
            ("Emits", "32 × 22 blocks"), ("Cost", "2.4 ms · 10% of frame"),
            ("Reads", "background subtract"), ("Written", "no"),
        )):
            name = QLabel(key)
            name.setFont(font(13))
            name.setStyleSheet(f"color: {hexed(LABEL)};")
            val = QLabel(value)
            val.setFont(font(13))
            val.setStyleSheet(f"color: {hexed(INK)};")
            pairs.addWidget(name, rowi, 0)
            pairs.addWidget(val, rowi, 1)
        holder = QWidget()
        holder.setLayout(pairs)
        panel.body_layout.addSpacing(10)
        panel.body_layout.addWidget(holder)

        figure = Figure("trace")
        figure.setMinimumWidth(240)
        figure.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        panel.body_layout.addWidget(figure, 1)
        panel.verdict(
            "Figures keep a white ground and a hairline border: a plot is a figure set into the "
            "page, not a screen embedded in it."
        )
        return panel

    def _text(self) -> Panel:
        panel = Panel("Scale", "weight comes from the family, never from a number")
        panel.body_layout.setContentsMargins(16, 16, 16, 18)
        column = QVBoxLayout()
        column.setSpacing(7)
        for note, text, sizer in (
            ("display / 18", "23.1 ms", font(18, display=True)),
            ("title / 16", "Remove background subtract?", font(16, display=True)),
            ("name / 14 semi", "background subtract", font(NAME_PX, display=True)),
            ("body / 13", "The chain closes over a removed step.", font(13)),
            ("value / 12.5 mono", "0.05", font(12.5, mono=True)),
            ("label / 11.5", "estimator", font(11.5)),
            ("eyebrow / 9.5 mono", "SPATIAL PREP", font(9.5, mono=True)),
        ):
            line = QHBoxLayout()
            tag = QLabel(note)
            tag.setFont(font(10.5, mono=True))
            tag.setStyleSheet(f"color: {hexed(LABEL)};")
            tag.setFixedWidth(120)
            sample = QLabel(text)
            sample.setFont(sizer)
            sample.setStyleSheet(f"color: {hexed(LABEL if 'eyebrow' in note or 'label' in note else INK)};")
            line.addWidget(tag)
            line.addWidget(sample)
            line.addStretch(1)
            column.addLayout(line)
        holder = QWidget()
        holder.setLayout(column)
        panel.body_layout.addWidget(holder, 1)
        panel.verdict(
            "Asking Segoe UI for 500 gets 400 and asking Variable Display for 600 gets 700 — the "
            "semibold is a family of its own, so name it and leave setWeight alone."
        )
        return panel


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(
        f"QToolTip {{ background: {hexed(TIP_BG)}; color: {hexed(TIP_INK)};"
        f" border: 0; padding: 5px 8px; }}"
    )
    sheet = Sheet()
    if "--height" in sys.argv:
        sheet.resize(sheet.width(), int(sys.argv[sys.argv.index("--height") + 1]))
    sheet.show()
    if "--shot" in sys.argv:
        target = sys.argv[sys.argv.index("--shot") + 1]
        app.processEvents()
        # A window's grab is clipped to the screen it is on; the scrolled body
        # is a widget of its own and renders at whatever height it wants.
        subject = sheet.body if "--full" in sys.argv else sheet
        subject.grab().save(target)
        return
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
