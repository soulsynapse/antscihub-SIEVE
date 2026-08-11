"""The Paper card, in the toolkit that has to draw it.

One runnable file holding the card design settled in the browser mockups: a
white card on a near-neutral ground, a header with no fill and a partial rule
under it, knobs inline, the step's surface as a light figure panel, and a 4px
cost meter closing the card at its foot.

Two things here are quotations rather than inventions.

The **edges** are `mockup/mockup.py`'s, transplanted unchanged in geometry:
`_EDGE_STUB`, `_EDGE_LANE`, the lane assignment that gives every edge one x for
its whole descent, and the arrowhead. That means occlusion works the way it does
there — this widget paints before its children, so a line crossing a card that
does not read it is hidden for exactly as long as it is not that card's
business. Only the two colours changed, because the ground did.

The **palette and metrics** are the settings chosen in the underline lab:
Paper's tokens, a rule inset 24px from the left ending 26px past the tool name,
1px, no fade, 2px of air above it, verbs on hover, 26px gaps, 6px radius, 4px
meter. They are written once at the top as constants rather than spread through
the widgets, so a later change is one edit and not nine.

What is mock here: the chain, the millisecond figures, and the knob values are
sample data. Per-step timing does not exist in the tree yet — the meter is a
picture of a measurement nothing currently takes, and that is the one thing on
this card that would need work in the run path before it could be true.

Run: `uv run python mockup/paper_cards.py`
Screenshot: `uv run python mockup/paper_cards.py --shot out.png`
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QComboBox,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# ---------------------------------------------------------------------------
# Paper. The neutrals carry a faint blue bias so they read as chosen; every
# colour beyond them means one thing — blue is attention, amber is cost, green
# is currency — and nothing else on a card is coloured.

GROUND = QColor("#f4f5f7")
CARD = QColor("#ffffff")
TRACK = QColor("#edeef1")
LINE = QColor("#dcdee3")
LINE_HOVER = QColor("#b8bcc4")
FIELD_LINE = QColor("#ced2d8")
INK = QColor("#1b1d21")
INK_2 = QColor("#565c66")
LABEL = QColor("#646a74")
SELECT = QColor("#2f6feb")
RING = QColor(47, 111, 235, 36)  # the 14% focus halo
CURRENT = QColor("#2e9e6b")
COST = QColor("#c9820c")
COST_TEXT = QColor("#8f5a05")
METER = QColor("#8d939d")
SCREEN = QColor("#ffffff")
GRID = QColor("#e9eaee")
TRACE = QColor("#2f6feb")
TRACE_FILL = QColor(47, 111, 235, 31)
THRESHOLD = QColor("#c9820c")
EDGE = QColor("#9ca1aa")
EDGE_LABEL = QColor("#7d828b")

#: Metrics from the underline lab, in the units they were chosen in.
RADIUS = 6
GAP = 26
METER_H = 4
UL_LEFT = 24          #: where the rule starts, measured from the card's left edge
UL_PAST = 26          #: how far past the end of the tool name it runs
UL_H = 1
UL_PAD = 2            #: air between the name's baseline box and the rule
NAME_PX = 14.0
BODY_PX = 12.5

#: The name is the one thing on the card read at a glance, so it takes weight
#: rather than colour. The weight comes from the *family* and not from
#: `setWeight`, because a weight request snaps to a cut the family ships and
#: neither neighbouring value is what was asked for: `Segoe UI` at 500 resolves
#: down to Regular, and `Segoe UI Variable Display` at 600 resolves up to Bold —
#: it carries only Regular and Bold, its semibold being a family of its own.
#: Naming the semibold family and leaving the weight alone is the only form of
#: this that gets the cut it names. Checked with QFontInfo, not assumed.
NAME_WEIGHT = QFont.Weight.Normal

#: Qt sizes fonts in points; these are the px figures above at the 96dpi Qt
#: assumes, so the card scales with the display rather than shrinking on it.
_PT = 0.75


#: Families in preference order. `Segoe UI Variable` ships on Windows 11 with
#: optical sizes — `Text` is drawn for reading at small sizes, `Display` for
#: headings — and each weight above Regular is a separate family name. The
#: semibold lists are used at their natural weight; see NAME_WEIGHT.
_UI_FAMILIES = ["Segoe UI Variable Text", "Segoe UI", "system-ui", "sans-serif"]
_UI_DISPLAY = ["Segoe UI Variable Text Semibold", "Segoe UI Semibold", "Segoe UI", "sans-serif"]
_UI_FIGURE = ["Segoe UI Variable Display Semibold", "Segoe UI Semibold", "Segoe UI", "sans-serif"]
_MONO_FAMILIES = ["Consolas", "Cascadia Mono", "DejaVu Sans Mono", "monospace"]


def font(
    px: float,
    *,
    weight: QFont.Weight = QFont.Weight.Normal,
    mono: bool = False,
    display: bool = False,
    figure: bool = False,
    tracking: float | None = None,
) -> QFont:
    face = QFont()
    if mono:
        face.setFamilies(_MONO_FAMILIES)
    elif figure:
        face.setFamilies(_UI_FIGURE)
    elif display:
        face.setFamilies(_UI_DISPLAY)
    else:
        face.setFamilies(_UI_FAMILIES)
    face.setPointSizeF(px * _PT)
    face.setWeight(weight)
    face.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    if tracking is not None:
        face.setLetterSpacing(QFont.SpacingType.PercentageSpacing, tracking)
    return face


# ---------------------------------------------------------------------------
# The chain. `reads` is by index into STEPS, which is what the edge code below
# expects; `ms` is the sample cost and `rate` is only here to keep the sample
# honest about what a step emits.


@dataclass
class Step:
    tool: str
    reads: tuple[int, ...]
    ms: float
    knobs: list[tuple[str, str, bool]] = field(default_factory=list)
    stale: bool = False
    pinned: bool = False
    fixed: bool = False
    plot: str | None = None


STEPS: list[Step] = [
    Step("source", (), 8.2, [("video", "arena_r1.mp4", True)], fixed=True),
    Step("crop", (0,), 0.4, [("regions", "2", False), ("x", "18%", False), ("y", "22%", False),
                             ("w", "54%", False), ("h", "46%", False)]),
    Step("rescale", (1,), 0.9, [("factor", "0.50", False)]),
    Step("normalize", (2,), 1.1, [("mode", "per-frame", True)]),
    Step("background", (3,), 6.7, [("estimator", "median", True), ("window", "240", False)], stale=True),
    Step("colour threshold", (3,), 1.3, [("channel", "value", True), ("floor", "0.18", False)]),
    Step("background subtract", (4, 5), 1.8, [("floor", "0.05", False)]),
    Step("block signal", (6,), 2.4, [("block", "16", False), ("signal", "mean |diff|", True)], plot="trace"),
    Step("windowed count", (7,), 0.3, [("D", "12", False)], pinned=True, plot="counts"),
]

TOTAL_MS = sum(step.ms for step in STEPS)
SLOWEST_MS = max(step.ms for step in STEPS)
SHARE_MS = TOTAL_MS / len(STEPS)

#: Named only where a step has more than one input — mockup.py's rule, and its
#: two names, because this is the same subtraction it draws.
PORT_NAMES = {(6, 5): "frames", (6, 4): "background"}

# ---------------------------------------------------------------------------
# The edges, from mockup.py. The comment there is the argument; what is kept
# here is the geometry: the trunk's inset, the step out to the next lane, one x
# per edge for its whole descent, and an arrowhead that always points down.

_EDGE_STUB = 16.0
_EDGE_LANE = 34.0
_ARROW_W = 4.0
_ARROW_H = 6.0


def _edges() -> list[tuple[int, int]]:
    return [(src, dst) for dst, step in enumerate(STEPS) for src in step.reads]


def _lanes() -> dict[tuple[int, int], int]:
    """One x per edge, shortest span first, so the trunk goes to the plain runs."""

    def overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
        return a[0] < b[1] and b[0] < a[1]

    lanes: dict[tuple[int, int], int] = {}
    for edge in sorted(_edges(), key=lambda e: (e[1] - e[0], e[0])):
        taken = {lane for other, lane in lanes.items() if overlaps(edge, other)}
        lane = 0
        while lane in taken:
            lane += 1
        lanes[edge] = lane
    return lanes


def _lane_x(left: float, lane: int) -> float:
    return left + _EDGE_STUB + _EDGE_LANE * lane


# ---------------------------------------------------------------------------
# Verbs. Drawn rather than typed: the glyphs render differently in every font
# and read as punctuation beside a tool name, so each is a path on a 16-unit
# grid, stroked at one weight.

_ICON_PATHS: dict[str, list[list[tuple[float, float]]]] = {
    "open": [[(6, 3.5), (10.5, 8), (6, 12.5)]],
    "swap": [
        [(3, 5.5), (11, 5.5)],
        [(8.5, 3), (11, 5.5), (8.5, 8)],
        [(13, 10.5), (5, 10.5)],
        [(7.5, 13), (5, 10.5), (7.5, 8)],
    ],
    "pin": [
        [(8, 10.5), (8, 14)],
        [(5, 3), (11, 3), (10.2, 7.2), (11.8, 8.7), (4.2, 8.7), (5.8, 7.2), (5, 3)],
    ],
    "cut": [
        [(3.5, 5), (12.5, 5)],
        [(6.5, 5), (6.5, 3.5), (9.5, 3.5), (9.5, 5)],
        [(5, 5), (5.6, 13), (10.4, 13), (11, 5)],
    ],
}


class IconButton(QAbstractButton):
    """One verb. Filled only for the pin, and only when this step is the pinned one."""

    def __init__(self, kind: str, tip: str, *, filled: bool = False, enabled: bool = True) -> None:
        super().__init__()
        self._kind = kind
        self._filled = filled
        self._hover = False
        self.setToolTip(tip)
        self.setEnabled(enabled)
        self.setFixedSize(23, 23)
        self.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

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
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5), 4, 4)

        colour = QColor(SELECT if self._filled else LABEL)
        if not self.isEnabled():
            colour.setAlpha(76)
        elif self._hover:
            colour = QColor(INK if not self._filled else SELECT)

        scale = 15 / 16
        offset = (self.width() - 15) / 2
        pen = QPen(colour, 1.35)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(colour if self._filled and self._kind == "pin" else Qt.BrushStyle.NoBrush)
        for run in _ICON_PATHS[self._kind]:
            path = QPainterPath(QPointF(run[0][0] * scale + offset, run[0][1] * scale + offset))
            for x, y in run[1:]:
                path.lineTo(x * scale + offset, y * scale + offset)
            painter.drawPath(path)
        painter.end()


# ---------------------------------------------------------------------------
# The surface: a light figure panel, not a dark inset. A trace needs a ground
# that is not the card, and on paper that ground is white with a rule behind
# the data — which is how the same plot is set in a figure.


class Figure(QWidget):
    _TRACE = [36, 30, 33, 19, 27, 24, 10, 22, 17, 30, 26, 13, 24, 20, 32, 28, 16, 25, 21, 29, 23]
    _COUNTS = [26, 29, 22, 30, 18, 27, 32, 24, 28, 26, 31, 21, 29, 25, 30, 23, 28, 32]
    _HITS = {8, 13}

    def __init__(self, kind: str) -> None:
        super().__init__()
        self._kind = kind
        self.setFixedHeight(50 if kind == "trace" else 46)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.fillRect(box, SCREEN)
        painter.setPen(QPen(FIELD_LINE, 1))
        painter.drawRoundedRect(box, RADIUS - 2, RADIUS - 2)

        inner = box.adjusted(3, 3, -3, -3)
        painter.setPen(QPen(GRID, 1))
        for i in range(1, 4):
            y = inner.top() + inner.height() * i / 4
            painter.drawLine(QPointF(inner.left(), y), QPointF(inner.right(), y))

        if self._kind == "trace":
            self._paint_trace(painter, inner)
        else:
            self._paint_counts(painter, inner)
        painter.end()

    def _paint_trace(self, painter: QPainter, inner: QRectF) -> None:
        points = [
            QPointF(inner.left() + inner.width() * i / (len(self._TRACE) - 1),
                    inner.top() + inner.height() * (value / 44))
            for i, value in enumerate(self._TRACE)
        ]
        area = QPolygonF(points + [QPointF(inner.right(), inner.bottom()),
                                   QPointF(inner.left(), inner.bottom())])
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(TRACE_FILL)
        painter.drawPolygon(area)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(TRACE, 1.4))
        painter.drawPolyline(QPolygonF(points))

    def _paint_counts(self, painter: QPainter, inner: QRectF) -> None:
        step = inner.width() / len(self._COUNTS)
        painter.setPen(Qt.PenStyle.NoPen)
        for i, value in enumerate(self._COUNTS):
            top = inner.top() + inner.height() * (value / 40)
            bar = QRectF(inner.left() + step * i + step * 0.18, top, step * 0.62, inner.bottom() - top)
            if i in self._HITS:
                painter.setBrush(TRACE)
                bar.setTop(inner.top() + inner.height() * 0.12)
            else:
                painter.setBrush(QColor(METER.red(), METER.green(), METER.blue(), 140))
            painter.drawRect(bar)
        pen = QPen(THRESHOLD, 1.2)
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setDashPattern([4, 3])
        painter.setPen(pen)
        y = inner.top() + inner.height() * 0.32
        painter.drawLine(QPointF(inner.left(), y), QPointF(inner.right(), y))


# ---------------------------------------------------------------------------
# The card.


class Dot(QWidget):
    """Current, or recomputing. The only green on the card, and the only place
    the amber means something other than cost."""

    def __init__(self, stale: bool) -> None:
        super().__init__()
        self._stale = stale
        self.setFixedSize(8, 8)
        self.setToolTip("Recomputing" if stale else "Current")

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(COST if self._stale else CURRENT)
        painter.drawEllipse(QRectF(1, 1, 6, 6))
        painter.end()


def _value_field(text: str, combo: bool) -> QWidget:
    """A knob's editor. Its border is one step darker than the card's, which is
    the whole of what makes it look touchable on a white card."""
    if combo:
        box = QComboBox()
        box.addItem(text)
        box.setFont(font(BODY_PX))
        box.setStyleSheet(
            f"QComboBox {{ background: {CARD.name()}; color: {INK.name()};"
            f" border: 1px solid {FIELD_LINE.name()}; border-radius: {RADIUS - 2}px;"
            f" padding: 1px 6px; }}"
            f"QComboBox::drop-down {{ border: 0; width: 14px; }}"
        )
        return box
    label = QLabel(text)
    label.setFont(font(BODY_PX))
    label.setStyleSheet(
        f"background: {CARD.name()}; color: {INK.name()};"
        f" border: 1px solid {FIELD_LINE.name()}; border-radius: {RADIUS - 2}px; padding: 2px 8px;"
    )
    return label


class StepCard(QFrame):
    """One step: header with a partial rule, knobs, surface, cost at the foot.

    The card paints its own background, border, rule and meter rather than
    wearing a stylesheet, because three of those four are geometry the
    stylesheet cannot express — the rule's length is measured off this card's
    own tool name, and the meter has to be clipped by the rounded corner it
    sits in.
    """

    def __init__(self, index: int, step: Step, on_select) -> None:
        super().__init__()
        self._index = index
        self._step = step
        self._on_select = on_select
        self._selected = False
        self._hovered = False
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAutoFillBackground(False)

        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, METER_H)
        column.setSpacing(0)

        header = QWidget()
        row = QHBoxLayout(header)
        row.setContentsMargins(12, 9, 8, UL_PAD)
        row.setSpacing(9)
        row.addWidget(Dot(step.stale))
        self._name = QLabel(step.tool)
        self._name.setFont(font(NAME_PX, weight=NAME_WEIGHT, display=True))
        self._name.setStyleSheet(f"color: {INK.name()};")
        row.addWidget(self._name)
        row.addStretch(1)
        cost = QLabel(f"{step.ms:.1f} ms")
        cost.setFont(font(BODY_PX - 1.5, mono=True))
        cost.setStyleSheet(f"color: {INK_2.name()};")
        row.addWidget(cost)

        self._verbs = QWidget()
        verbs = QHBoxLayout(self._verbs)
        verbs.setContentsMargins(0, 0, 0, 0)
        verbs.setSpacing(1)
        verbs.addWidget(IconButton("open", "Open this step's settings"))
        verbs.addWidget(IconButton("swap", "Swap for another tool of this signature"))
        verbs.addWidget(IconButton(
            "pin",
            "Pinned below the canvas" if step.pinned else "Pin below the canvas",
            filled=step.pinned,
        ))
        verbs.addWidget(IconButton(
            "cut",
            "The chain has to read something" if step.fixed else "Remove this step",
            enabled=not step.fixed,
        ))
        row.addWidget(self._verbs)
        # Opacity rather than visibility: hiding the buttons would collapse the
        # row and walk the cost figure sideways every time the pointer left.
        self._fade = QGraphicsOpacityEffect(self._verbs)
        self._fade.setOpacity(0.0)
        self._verbs.setGraphicsEffect(self._fade)

        self._header = header
        column.addWidget(header)

        body = QWidget()
        knobs = QHBoxLayout(body)
        knobs.setContentsMargins(12, 10, 12, 12)
        knobs.setSpacing(18)
        for name, value, combo in step.knobs:
            pair = QHBoxLayout()
            pair.setSpacing(8)
            label = QLabel(name)
            label.setFont(font(BODY_PX - 1.5))
            label.setStyleSheet(f"color: {LABEL.name()};")
            pair.addWidget(label)
            pair.addWidget(_value_field(value, combo))
            knobs.addLayout(pair)
        knobs.addStretch(1)
        column.addWidget(body)

        if step.stale:
            note = QLabel("Recomputing — window changed 0.4 s ago")
            note.setFont(font(BODY_PX - 1.5))
            note.setStyleSheet(f"color: {COST_TEXT.name()}; padding: 0 12px 10px 12px;")
            column.addWidget(note)

        if step.plot:
            wrap = QWidget()
            hold = QVBoxLayout(wrap)
            hold.setContentsMargins(12, 0, 12, 12)
            hold.addWidget(Figure(step.plot))
            column.addWidget(wrap)

    # -- state -------------------------------------------------------------
    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._fade.setOpacity(1.0 if (selected or self._hovered) else 0.0)
        self.update()

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._hovered = True
        self._fade.setOpacity(1.0)
        self.update()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._hovered = False
        self._fade.setOpacity(1.0 if self._selected else 0.0)
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        event.accept()
        self._on_select(self._index)

    # -- paint -------------------------------------------------------------
    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        shape = QPainterPath()
        shape.addRoundedRect(box, RADIUS, RADIUS)

        painter.fillPath(shape, CARD)

        # the meter, clipped by the corner it sits in
        painter.save()
        painter.setClipPath(shape)
        foot = QRectF(box.left(), box.bottom() - METER_H, box.width(), METER_H)
        painter.fillRect(foot, TRACK)
        filled = QRectF(foot)
        filled.setWidth(foot.width() * (self._step.ms / SLOWEST_MS))
        # The bar says cost and only cost: neutral, amber past this step's share
        # of the frame. Selection is the border and the halo, and lighting the
        # bar too would make a selected cheap step and a selected expensive one
        # the same colour — which is the one distinction the bar exists to draw.
        painter.fillRect(filled, COST if self._step.ms > SHARE_MS else METER)
        painter.restore()

        # the rule: flush at UL_LEFT, ending UL_PAST beyond the name, no fade
        y = self._header.geometry().bottom() + 0.5
        end = self._name.geometry().right() + UL_PAST
        painter.setPen(QPen(LINE, UL_H))
        painter.drawLine(QPointF(UL_LEFT, y), QPointF(min(end, box.right() - 8), y))

        edge = SELECT if self._selected else (LINE_HOVER if self._hovered else LINE)
        painter.setPen(QPen(edge, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(shape)
        painter.end()


# ---------------------------------------------------------------------------
# The column, which is also the edge layer: it paints before its children, so a
# line crossing a card that does not read it goes behind that card.


class ChainColumn(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._current = 7
        self._lanes = _lanes()
        self.cards: list[StepCard] = []

        column = QVBoxLayout(self)
        column.setContentsMargins(16, 22, 16, 24)
        column.setSpacing(GAP)
        for index, step in enumerate(STEPS):
            card = StepCard(index, step, self.select)
            self.cards.append(card)
            column.addWidget(card)
        column.addStretch(1)
        self.cards[self._current].set_selected(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def select(self, index: int) -> None:
        self._current = index
        for i, card in enumerate(self.cards):
            card.set_selected(i == index)
        self.update()

    def move(self, delta: int) -> None:
        self.select(max(0, min(len(self.cards) - 1, self._current + delta)))

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Up:
            self.move(-1)
        elif event.key() == Qt.Key.Key_Down:
            self.move(+1)
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), GROUND)

        # the selected card's halo, painted here because it lies outside the
        # card's own rect and a widget cannot draw beyond itself
        chosen = self.cards[self._current].geometry()
        painter.setPen(QPen(RING, 3))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(chosen).adjusted(-2, -2, 2, 2), RADIUS + 2, RADIUS + 2)

        for src, dst in _edges():
            self._paint_edge(painter, src, dst)
        painter.end()

    def _paint_edge(self, painter: QPainter, src: int, dst: int) -> None:
        above = self.cards[src].geometry()
        below = self.cards[dst].geometry()
        x = _lane_x(above.left(), self._lanes[(src, dst)])
        start = QPointF(x, above.bottom() + 1)
        end = QPointF(x, below.top())

        live = self._current in (src, dst)
        colour = QColor(SELECT if live else EDGE)
        painter.setPen(QPen(colour, 1.4 if live else 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(start, end)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(colour)
        painter.drawPolygon(QPolygonF([
            QPointF(end.x() - _ARROW_W, end.y() - _ARROW_H),
            QPointF(end.x() + _ARROW_W, end.y() - _ARROW_H),
            QPointF(end.x(), end.y()),
        ]))

        name = PORT_NAMES.get((dst, src))
        if name is not None:
            painter.setPen(QPen(SELECT if live else EDGE_LABEL))
            painter.setFont(font(9, mono=True))
            painter.drawText(QPointF(end.x() + _ARROW_W + 3, end.y() - _ARROW_H + 1), name)


class Window(QWidget):
    """The stack, under the line that says what the whole chain costs a frame."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SIEVE v3 — Paper")
        self.resize(560, 940)
        # Palette rather than a stylesheet: a `background:` rule set here reaches
        # every descendant, and the header and body widgets inside a card would
        # then paint the ground over the card the card just painted — taking the
        # rule and the meter with it.
        self.setAutoFillBackground(True)
        window = self.palette()
        window.setColor(self.backgroundRole(), GROUND)
        self.setPalette(window)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        chrome = QWidget()
        chrome.setObjectName("chrome")
        chrome.setStyleSheet(
            f"#chrome {{ background: {CARD.name()}; border-bottom: 1px solid {LINE.name()}; }}"
        )
        row = QHBoxLayout(chrome)
        row.setContentsMargins(16, 13, 16, 13)
        row.setSpacing(12)
        for text, px, colour, weight in (
            (f"{TOTAL_MS:.1f} ms", 18, INK, True),
            ("per frame", 11.5, LABEL, False),
            (f"{1000 / TOTAL_MS:.0f} fps", 18, INK, True),
            ("chain throughput", 11.5, LABEL, False),
        ):
            label = QLabel(text)
            label.setFont(font(px, figure=weight))
            label.setStyleSheet(f"color: {colour.name()};")
            row.addWidget(label)
        row.addStretch(1)
        recomputing = QLabel("1 step recomputing")
        recomputing.setFont(font(11.5))
        recomputing.setStyleSheet(f"color: {LABEL.name()};")
        row.addWidget(recomputing)
        layout.addWidget(chrome)

        self.column = ChainColumn()
        scroll = QScrollArea()
        scroll.setWidget(self.column)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        layout.addWidget(scroll, 1)


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
