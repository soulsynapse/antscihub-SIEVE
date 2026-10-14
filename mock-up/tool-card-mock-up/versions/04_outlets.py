"""Alternatives as numbers beside the name and outlets on the foot; one curved arrow from the viewed outlet; line counts in the gap."""
from __future__ import annotations

import sys
from dataclasses import dataclass, field

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)


GROUND = QColor("#f4f5f7")
CARD = QColor("#ffffff")
TRACK = QColor("#e9eaee")
LINE = QColor("#dcdee3")
LINE_2 = QColor("#c4c8cf")
INK = QColor("#1b1d21")
INK_2 = QColor("#565c66")
LABEL = QColor("#646a74")
FAINT = QColor("#9ca1aa")
SELECT = QColor("#2f6feb")
SELECT_SOFT = QColor(47, 111, 235, 31)
RING = QColor(47, 111, 235, 36)
AMBER_SOFT = QColor(201, 130, 12, 26)
AMBER_TEXT = QColor("#8f5a05")
THRESHOLD = QColor("#c9820c")
GATE_FILL = QColor(201, 130, 12, 46)
TRACE = QColor("#2f6feb")
ARROW = QColor("#9ca1aa")


RADIUS = 2
GAP = 52
OUTLET_D = 22
LEAD = 6
RUN = 9
HEAD_H = 6
HEADER_PAD = 6
CARD_PAD_X = 12
ROW_GAP = 6
SLIDER_H = 14
NUM_PX = 11.0
NAME_PX = 12.0
BODY_PX = 12.0
VALUE_W = 40

# what view.py lets you fiddle with: name -> (min, max, step)
TUNABLES = {
    "GAP": (30, 80, 1),
    "OUTLET_D": (14, 30, 1),
    "LEAD": (0, 20, 1),
    "RUN": (0, 20, 1),
    "HEADER_PAD": (2, 14, 1),
    "CARD_PAD_X": (6, 24, 1),
    "ROW_GAP": (2, 14, 1),
    "NUM_PX": (9, 14, 0.5),
    "NAME_PX": (10, 16, 0.5),
    "BODY_PX": (10, 14, 0.5),
    "RADIUS": (0, 10, 1),
}

NAME_WEIGHT = QFont.Weight.DemiBold

_PT = 0.75
_UI_FAMILIES = ["Segoe UI Variable Text", "Segoe UI", "system-ui", "sans-serif"]
_UI_DISPLAY = ["Segoe UI Variable Text Semibold", "Segoe UI Semibold", "Segoe UI", "sans-serif"]
_UI_FIGURE = ["Segoe UI Variable Display Semibold", "Segoe UI Semibold", "Segoe UI", "sans-serif"]
_MONO_FAMILIES = ["Consolas", "Cascadia Mono", "DejaVu Sans Mono", "monospace"]


def font(px: float, *, weight: QFont.Weight = QFont.Weight.Normal, mono: bool = False) -> QFont:
    face = QFont()
    face.setFamilies(_MONO_FAMILIES if mono else _UI_FAMILIES)
    face.setPointSizeF(px * _PT)
    face.setWeight(weight)
    face.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return face


# ---- the chain. every stage has a list of alternatives; `pick` is the one the canvas views ----
# a knob is (name, lo, hi, value, unit, decimals); a bool knob is (name, "bool", 0, value)
Knob = list


@dataclass
class Stage:
    name: str
    alts: list[list[Knob]]
    pick: int = 0
    src: bool = False
    note: str = ""
    save: str | None = None
    ext: str = ""
    plot: bool = False
    stale: bool = False


def crop(x: int = 18, y: int = 22) -> list[Knob]:
    return [["x", 0, 100, x, "%", 0], ["y", 0, 100, y, "%", 0], ["w", 1, 100, 54, "%", 0], ["h", 1, 100, 46, "%", 0]]


def rescale(f: float) -> list[Knob]:
    return [["factor", 0.1, 1.0, f, "", 2]]


STAGES: list[Stage] = [
    Stage("Video", [[]], src=True, note="arena_r1.mp4 · 462×456 · 59.94 fps"),
    Stage("Crop", [crop(), crop(40, 22), crop(18, 55), crop(40, 55)], pick=2),
    Stage("Rescale", [rescale(0.5), rescale(0.25)]),
    Stage("Threshold", [[["thresh", 0, 255, 128, "", 0], ["invert", "bool", 0, False]]], save="mask_r1", ext="avi"),
    Stage("Motion", [[["gate", 0.0, 30.0, 2.0, "", 1]]], save="motion_r1", ext="csv", plot=True),
]
MAX_ALTS = 8


def lines_out(i: int) -> int:
    """How many lines Run would send out of stage i."""
    n = 1
    for stage in STAGES[: i + 1]:
        n *= len(stage.alts)
    return n


def viewed_line() -> int:
    """Where the viewed line sits among all of them, counting from 0."""
    index, radix = 0, 1
    for stage in STAGES:
        index += stage.pick * radix
        radix *= len(stage.alts)
    return index


def suffix(i: int) -> str:
    """The file-name tag of the viewed line up to stage i: c3r1 for crop 3, rescale 1."""
    return "".join(f"{s.name[0].lower()}{s.pick + 1}" for s in STAGES[1 : i + 1] if len(s.alts) > 1)


def path_text() -> str:
    return " › ".join(f"{s.name} {s.pick + 1}" if len(s.alts) > 1 else s.name for s in STAGES)


def fmt(knob: Knob) -> str:
    name, lo, hi, value, unit, dec = knob
    return f"{value:.{dec}f}{unit}"


# ---- small widgets -------------------------------------------------------------
class TextButton(QAbstractButton):
    """A number, a +, or an x beside the name: text on a tint when it is the viewed one."""

    def __init__(self, text: str, tip: str, on_click, *, picked: bool = False, faint: bool = False) -> None:
        super().__init__()
        self._text, self._picked, self._faint, self._hover = text, picked, faint, False
        self.setToolTip(tip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setFont(font(NUM_PX, mono=True, weight=QFont.Weight.DemiBold if picked else QFont.Weight.Normal))
        width = self.fontMetrics().horizontalAdvance(text) + 10
        self.setFixedSize(max(width, 18), 18)
        self.clicked.connect(on_click)

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._hover = True
        self.update()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._hover = False
        self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        box = QRectF(self.rect())
        if self._picked:
            painter.fillRect(box, SELECT_SOFT)
        elif self._hover:
            painter.fillRect(box, TRACK)
        colour = SELECT if self._picked else (INK if self._hover else (FAINT if self._faint else INK_2))
        painter.setPen(QPen(colour))
        painter.setFont(self.font())
        painter.drawText(box, Qt.AlignmentFlag.AlignCenter, self._text)
        painter.end()


class IconButton(QAbstractButton):
    """An x, drawn as two strokes."""

    def __init__(self, tip: str, on_click, *, enabled: bool = True, faint: bool = False) -> None:
        super().__init__()
        self._hover, self._faint = False, faint
        self.setToolTip(tip)
        self.setEnabled(enabled)
        self.setFixedSize(20, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.clicked.connect(on_click)

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._hover = True
        self.update()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._hover = False
        self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._hover and self.isEnabled():
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(TRACK)
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 3, 3)
        colour = QColor(INK if self._hover else FAINT)
        if not self.isEnabled():
            colour.setAlpha(76)
        elif self._faint and not self._hover:
            colour.setAlpha(128)
        pen = QPen(colour, 1.4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        c = self.width() / 2
        painter.drawLine(QPointF(c - 3.5, c - 3.5), QPointF(c + 3.5, c + 3.5))
        painter.drawLine(QPointF(c + 3.5, c - 3.5), QPointF(c - 3.5, c + 3.5))
        painter.end()


class Figure(QWidget):
    _TRACE = [36, 30, 33, 19, 27, 24, 10, 22, 17, 30, 26, 13, 24, 20, 32, 28, 16, 25, 21, 29, 23, 18, 27, 31, 22]

    def __init__(self) -> None:
        super().__init__()
        self.setFixedHeight(64)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.fillRect(box, CARD)
        painter.setPen(QPen(LINE, 1))
        painter.drawRoundedRect(box, RADIUS, RADIUS)
        inner = box.adjusted(1, 1, -1, -1)
        n = len(self._TRACE)
        step = inner.width() / (n - 1)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(GATE_FILL)
        for i, value in enumerate(self._TRACE):
            if value < 18:
                painter.drawRect(QRectF(inner.left() + step * i - step / 2, inner.top(), step, inner.height()))
        pen = QPen(THRESHOLD, 1)
        pen.setDashPattern([4, 3])
        painter.setPen(pen)
        y = inner.top() + inner.height() * 0.41
        painter.drawLine(QPointF(inner.left(), y), QPointF(inner.right(), y))
        painter.setPen(QPen(TRACE, 1.4))
        painter.drawPolyline(QPolygonF([
            QPointF(inner.left() + step * i, inner.top() + inner.height() * value / 44)
            for i, value in enumerate(self._TRACE)
        ]))
        painter.setPen(QPen(INK, 1.5))
        x = inner.left() + inner.width() * 0.42
        painter.drawLine(QPointF(x, inner.top()), QPointF(x, inner.bottom()))
        painter.end()


def _slider(knob: Knob, on_change) -> QSlider:
    name, lo, hi, value, unit, dec = knob
    scale = 10 ** dec
    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setRange(round(lo * scale), round(hi * scale))
    slider.setValue(round(value * scale))
    slider.setFixedHeight(SLIDER_H)
    slider.setStyleSheet(
        "QSlider::groove:horizontal { height: 3px; background: %s; border-radius: 1px; }"
        "QSlider::handle:horizontal { width: 12px; height: 12px; margin: -5px 0; border-radius: 6px;"
        " background: #fff; border: 1.5px solid %s; }"
        "QSlider::handle:horizontal:hover { border-color: %s; }" % (LINE_2.name(), INK_2.name(), SELECT.name())
    )
    slider.valueChanged.connect(lambda raw: on_change(raw / scale))
    return slider


# ---- the card ------------------------------------------------------------------
class StepCard(QFrame):
    """Name, the alternatives as numbers beside it, the remove x, then the viewed alternative's knobs."""

    def __init__(self, index: int, stage: Stage, column: "ChainColumn") -> None:
        super().__init__()
        self._index, self._stage, self._column = index, stage, column
        self._selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        body = QVBoxLayout(self)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        head = QWidget()
        row = QHBoxLayout(head)
        row.setContentsMargins(CARD_PAD_X, HEADER_PAD, HEADER_PAD, HEADER_PAD)
        row.setSpacing(4)
        name = QLabel(stage.name)
        name.setFont(font(NAME_PX, weight=NAME_WEIGHT))
        name.setStyleSheet(f"color: {INK.name()};")
        row.addWidget(name)
        if not stage.src:
            n = len(stage.alts)
            if n > 1:
                for k in range(n):
                    row.addWidget(TextButton(str(k + 1), f"View the line through alternative {k + 1}",
                                             lambda _=False, k=k: column.pick(index, k), picked=k == stage.pick))
            row.addWidget(TextButton("+", "Split off an alternative: a copy of the viewed one, to change",
                                     lambda _=False: column.split(index), faint=True))
            if n > 1:
                row.addWidget(IconButton(f"Drop alternative {stage.pick + 1}",
                                         lambda _=False: column.drop(index), faint=True))
        row.addStretch(1)
        row.addWidget(IconButton("The chain has to read something" if stage.src else "Remove this step",
                                 lambda _=False: None, enabled=not stage.src))
        body.addWidget(head)

        knobs = QWidget()
        grid = QGridLayout(knobs)
        grid.setContentsMargins(CARD_PAD_X, 2, CARD_PAD_X, 12)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(ROW_GAP)
        if stage.src:
            note = QLabel(stage.note)
            note.setFont(font(BODY_PX))
            note.setStyleSheet(f"color: {FAINT.name()};")
            grid.addWidget(note, 0, 0, 1, 3)
        for r, knob in enumerate(stage.alts[stage.pick]):
            label = QLabel(knob[0])
            label.setFont(font(BODY_PX))
            label.setStyleSheet(f"color: {LABEL.name()};")
            grid.addWidget(label, r, 0)
            if knob[1] == "bool":
                from PySide6.QtWidgets import QCheckBox
                box = QCheckBox()
                box.setChecked(bool(knob[3]))
                box.stateChanged.connect(lambda _s, k=knob: column.touched(index))
                grid.addWidget(box, r, 1, 1, 2, Qt.AlignmentFlag.AlignLeft)
                continue
            value = QLabel(fmt(knob))
            value.setFont(font(BODY_PX - 1, mono=True))
            value.setFixedWidth(VALUE_W)
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            value.setStyleSheet(f"color: {INK.name()};")

            def changed(v: float, k=knob, out=value) -> None:
                k[3] = v
                out.setText(fmt(k))
                column.touched(index)

            grid.addWidget(_slider(knob, changed), r, 1)
            grid.addWidget(value, r, 2)
        grid.setColumnStretch(1, 1)
        if stage.plot:
            grid.addWidget(Figure(), grid.rowCount(), 0, 1, 3)
        body.addWidget(knobs)
        if len(stage.alts) > 1:
            body.addSpacing(OUTLET_D // 2)  # the outlets straddle the foot; keep the last knob clear of them

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            # the outlets straddle the foot, so a click on their upper half lands here first
            if not self._column.hit_outlet(self.mapToParent(event.position().toPoint())):
                self._column.select(self._index)
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        shape = QPainterPath()
        shape.addRoundedRect(box, RADIUS, RADIUS)
        if not self._stage.src:
            painter.fillPath(shape, AMBER_SOFT if self._stage.stale else CARD)
        pen = QPen(SELECT if self._selected else LINE, 1)
        if self._stage.src:
            pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(shape)
        if self._stage.stale:
            painter.setFont(font(BODY_PX))
            painter.setPen(QPen(AMBER_TEXT))
            x = CARD_PAD_X + QLabel(self._stage.name).fontMetrics().horizontalAdvance(self._stage.name)
            painter.drawText(QPointF(x + 8, HEADER_PAD + 13), "recomputing")
        painter.end()


class Overlay(QWidget):
    """Sits over the cards and paints the outlets, which straddle each card's foot."""

    def __init__(self, column: "ChainColumn") -> None:
        super().__init__(column)
        self._column = column
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        for i, stage in enumerate(STAGES):
            if len(stage.alts) > 1:
                self._column.paint_outlets(painter, i)
        painter.end()


# ---- the column: cards, and between them the outlets, the arrow and the chips ----
class ChainColumn(QWidget):
    def __init__(self, window: "Window") -> None:
        super().__init__()
        self._window = window
        self._current = 2
        self.cards: list[StepCard] = []
        self._stale_timer = QTimer(self)
        self._stale_timer.setSingleShot(True)
        self._stale_timer.setInterval(900)
        self._stale_timer.timeout.connect(self._clear_stale)
        self.setMouseTracking(True)

        column = QVBoxLayout(self)
        column.setContentsMargins(16, 16, 16, 24)
        column.setSpacing(GAP)
        for index, stage in enumerate(STAGES):
            card = StepCard(index, stage, self)
            self.cards.append(card)
            column.addWidget(card)
        column.addStretch(1)
        self.cards[self._current].set_selected(True)
        self._overlay = Overlay(self)
        self._overlay.raise_()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._overlay.setGeometry(self.rect())

    # -- state ---------------------------------------------------------------
    def select(self, index: int) -> None:
        self._current = index
        for i, card in enumerate(self.cards):
            card.set_selected(i == index)
        self._window.refresh()
        self.update()

    def pick(self, index: int, k: int) -> None:
        if STAGES[index].pick != k:
            STAGES[index].pick = k
            self._mark_stale(index)
        self._current = index
        self._window.rebuild()

    def split(self, index: int) -> None:
        stage = STAGES[index]
        if len(stage.alts) >= MAX_ALTS:
            return
        stage.alts.append([list(k) for k in stage.alts[stage.pick]])
        stage.pick = len(stage.alts) - 1
        self._current = index
        self._window.rebuild()

    def drop(self, index: int) -> None:
        stage = STAGES[index]
        del stage.alts[stage.pick]
        stage.pick = min(stage.pick, len(stage.alts) - 1)
        self._mark_stale(index)
        self._window.rebuild()

    def touched(self, index: int) -> None:
        self._mark_stale(index)
        for card in self.cards:
            card.update()

    def _mark_stale(self, index: int) -> None:
        for i, stage in enumerate(STAGES):
            stage.stale = i >= index and not stage.src
        self._stale_timer.start()

    def _clear_stale(self) -> None:
        for stage in STAGES:
            stage.stale = False
        for card in self.cards:
            card.update()

    # -- geometry ------------------------------------------------------------
    def _outlet_centre(self, index: int, k: int) -> QPointF:
        rect = self.cards[index].geometry()
        n = len(STAGES[index].alts)
        return QPointF(rect.left() + rect.width() * (k + 0.5) / n, rect.bottom() + 1)

    def hit_outlet(self, pos) -> bool:
        pos = QPointF(pos)
        for i, stage in enumerate(STAGES):
            for k in range(len(stage.alts)):
                if len(stage.alts) > 1 and (self._outlet_centre(i, k) - pos).manhattanLength() <= OUTLET_D * 0.7:
                    self.pick(i, k)
                    return True
        return False

    def mousePressEvent(self, event) -> None:
        if not self.hit_outlet(event.position()):
            super().mousePressEvent(event)

    # -- paint ---------------------------------------------------------------
    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), GROUND)

        chosen = self.cards[self._current].geometry()
        painter.setPen(QPen(RING, 3))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(chosen).adjusted(-2, -2, 2, 2), RADIUS + 2, RADIUS + 2)

        for i in range(len(STAGES)):
            self._paint_gap(painter, i)
        painter.end()
        self._overlay.update()

    def paint_outlets(self, painter: QPainter, index: int) -> None:
        stage = STAGES[index]
        r = OUTLET_D / 2
        painter.setFont(font(NUM_PX, mono=True))
        for k in range(len(stage.alts)):
            c = self._outlet_centre(index, k)
            picked = k == stage.pick
            if picked:
                painter.setPen(QPen(SELECT_SOFT, 2))
                painter.setBrush(SELECT)
                painter.drawEllipse(c, r + 1, r + 1)
                painter.setPen(QPen(SELECT, 1))
            else:
                painter.setPen(QPen(LINE_2, 1))
                painter.setBrush(CARD)
            painter.drawEllipse(c, r, r)
            painter.setPen(QPen(CARD if picked else INK_2))
            painter.drawText(QRectF(c.x() - r, c.y() - r, OUTLET_D, OUTLET_D), Qt.AlignmentFlag.AlignCenter, str(k + 1))

    def _paint_gap(self, painter: QPainter, index: int) -> None:
        stage = STAGES[index]
        rect = self.cards[index].geometry()
        n = len(stage.alts)
        last = index == len(STAGES) - 1
        count = lines_out(index)

        # the chips: file pattern times count, and the count of lines
        painter.setFont(font(10.5, mono=True))
        metrics = painter.fontMetrics()
        chips: list[tuple[str, bool]] = []
        if stage.save:
            chips.append((f"⤓ {stage.save}_{suffix(index) or '…'}.{stage.ext}" + (f" ×{count}" if count > 1 else ""), True))
        chips.append((f"{count} line{'s' if count != 1 else ''}", False))
        y_mid = rect.bottom() + 1 + (GAP / 2 if not last else 14)
        x = rect.right() if not last else rect.center().x() + sum(metrics.horizontalAdvance(t) + 18 for t, _ in chips) / 2
        for text, boxed in reversed(chips):
            w = metrics.horizontalAdvance(text) + 14
            box = QRectF(x - w, y_mid - 9, w, 18)
            painter.setPen(QPen(LINE, 1) if boxed else Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 210) if boxed else QColor(244, 245, 247, 210))
            painter.drawRoundedRect(box, RADIUS, RADIUS)
            painter.setPen(QPen(INK_2))
            painter.drawText(box, Qt.AlignmentFlag.AlignCenter, text)
            x -= w + 4
        if last:
            return

        # the arrow: straight out of the viewed outlet, an S across, straight into the head
        below = self.cards[index + 1].geometry()
        x0 = self._outlet_centre(index, stage.pick).x() if n > 1 else rect.center().x()
        x1 = below.center().x()
        top = rect.bottom() + 1 + (OUTLET_D / 2 if n > 1 else 0)
        end = below.top() - HEAD_H
        mid = (top + LEAD + end - RUN) / 2
        path = QPainterPath(QPointF(x0, top))
        path.lineTo(x0, top + LEAD)
        path.cubicTo(QPointF(x0, mid), QPointF(x1, mid), QPointF(x1, end - RUN))
        path.lineTo(x1, end)
        painter.setPen(QPen(SELECT, 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(SELECT)
        painter.drawPolygon(QPolygonF([
            QPointF(x1 - 4.5, end), QPointF(x1 + 4.5, end), QPointF(x1, end + HEAD_H),
        ]))


class Window(QWidget):
    """The chain under a strip that says which line the canvas is viewing."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SIEVE — outlets (04)")
        self.resize(560, 900)
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), GROUND)
        self.setPalette(palette)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        chrome = QWidget()
        chrome.setObjectName("chrome")
        chrome.setStyleSheet(f"#chrome {{ background: {INK.name()}; }}")
        row = QHBoxLayout(chrome)
        row.setContentsMargins(16, 8, 16, 8)
        self._path = QLabel()
        self._path.setFont(font(11, mono=True))
        self._path.setStyleSheet("color: #c6cad1;")
        row.addWidget(self._path)
        row.addStretch(1)
        layout.addWidget(chrome)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        layout.addWidget(self._scroll, 1)
        self.column: ChainColumn | None = None
        self.rebuild()

    def rebuild(self) -> None:
        current = self.column._current if self.column else 2
        self.column = ChainColumn(self)
        self.column.select(current)
        self._scroll.setWidget(self.column)
        self.refresh()

    def refresh(self) -> None:
        total = lines_out(len(STAGES) - 1)
        self._path.setText(f"viewing line {viewed_line() + 1} of {total}:  {path_text()}")


def main() -> None:
    app = QApplication(sys.argv)
    window = Window()
    if "--height" in sys.argv:
        window.resize(window.width(), int(sys.argv[sys.argv.index("--height") + 1]))
    window.show()
    if "--shot" in sys.argv:
        target = sys.argv[sys.argv.index("--shot") + 1]
        app.processEvents()
        window.grab().save(target)
        return
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
