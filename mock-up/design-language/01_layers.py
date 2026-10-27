"""Design language from first principles, dark first.

    python 01_layers.py

Three rules on show, each with a knob so the number is found by eye and read
off the bottom line:

  1. Ground is a dark gray. Everything sits on it.
  2. Each thing layered on top is a lighter gray by one fixed step. Nothing
     is inset more than three times, so there are exactly four grays: ground
     and layers 1-3. The right-hand stack shows what a fourth would cost.
  3. Rows read as a table: descriptions left-aligned in one column, every
     dropdown the same width and left-aligned in the next, so the eye scans
     straight down either column.
"""
from __future__ import annotations

import ctypes
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontDatabase, QFontMetrics, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

GROUND = 31        # ground gray, 0-255
STEP = 9           # how much lighter each layer is
MAX_DEPTH = 3      # layers above ground
LABEL_MIN = 40     # a form's description column is its widest label, clamped to these, px
LABEL_MAX = 160
SELECTOR_W = 160   # every dropdown, px
ROW_H = 22         # every form row and every control in it, px, whatever the control is
PAD = 8            # inset per layer, px
GAP = 8            # between blocks inside a layer, px
ROW_GAP = 2        # between rows of a form, px
HEAD_GAP = 14      # below a section title, px; the room that makes it read as a title
RADIUS = 4
HEAD = 255         # section names, the only pure white on screen
INK = 200          # everything inside a section: descriptions and values alike
INK_2 = 140        # tertiary: readout, slider handles, unchecked boxes
LINE_LIFT = 14     # a layer's hairline edge is this much lighter than the layer
MEASURED_LIFT = 18 # a measured result is a flat field this much lighter than the surface it sits on
FONT_PX = 12       # integer pixels, never points, so glyphs sit on the grid under display scaling
FONT_WEIGHT = 500  # regular Inter reads thin on dark; 500 fills the stroke without reading bold
HINTING = 3        # QFont.HintingPreference: 0 default, 1 none, 2 vertical, 3 full. DirectWrite ignores it
ACCENT = QColor(88, 146, 255)   # the one hue: the viewed line, the selected card
AMBER = QColor(222, 160, 56)    # the one warning: stale, and the gate in a figure
CARD_W = 0         # a chain card, px; 0 means just wide enough for the two columns
SCROLL_W = 8       # the scrollbar beside the chain
CARD_GAP = 44      # between cards: room for the arrow and the chips
OUTLET_D = 20      # an alternative's outlet on the card foot
VALUE_W = 36       # a slider's mono readout
MONO = ["Cascadia Mono", "Consolas", "Menlo", "DejaVu Sans Mono", "monospace"]
GLYPHS = Path(__file__).parent / "glyphs"
FONTS = Path(__file__).parent / "fonts"   # bundled faces load first, so both platforms match
FAMILIES = ["Inter", "Segoe UI Variable Text", "Segoe UI", "SF Pro Text", "Helvetica Neue", "Helvetica", "Arial"]


def gray(v: int) -> str:
    v = max(0, min(255, v))
    return f"rgb({v},{v},{v})"


def layer(depth: int) -> int:
    return GROUND + STEP * depth


def install_font(app: QApplication) -> str:
    """Bundled TTFs first, then the first family the platform has; returns what was chosen."""
    for ttf in sorted(FONTS.glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(ttf))
    have = set(QFontDatabase.families())
    family = next((f for f in FAMILIES if f in have), app.font().family())
    app.setFont(ui_font(family))
    return family


def ui_font(family: str | None = None) -> QFont:
    font = QFont(family or QApplication.font().family())
    font.setPixelSize(FONT_PX)
    font.setWeight(QFont.Weight(FONT_WEIGHT))
    font.setHintingPreference(QFont.HintingPreference(HINTING))
    return font


def paint_caption(w: QWidget) -> None:
    """Windows 11: make the title bar the ground gray too. Elsewhere a no-op."""
    if sys.platform != "win32":
        return
    hwnd = int(w.winId())
    dwm = ctypes.windll.dwmapi
    colorref = ctypes.c_int((GROUND << 16) | (GROUND << 8) | GROUND)
    dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(colorref), 4)   # DWMWA_CAPTION_COLOR
    text = ctypes.c_int((INK << 16) | (INK << 8) | INK)
    dwm.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(text), 4)       # DWMWA_TEXT_COLOR


def sheet() -> str:
    ctl = GROUND   # a control is a well: the ground shows through it at every depth
    return f"""
    QWidget {{ color: {gray(INK)}; }}
    QLabel[role="desc"] {{ color: {gray(INK)}; }}
    QLabel[role="name"] {{ color: {gray(HEAD)}; }}
    QLabel[role="readout"] {{ color: {gray(INK_2)}; }}
    QLabel[role="measured"] {{ border: none; border-radius: {RADIUS}px; padding: 0px 6px; }}
    """ + "".join(
        f'Layer[depth="{d}"] QLabel[role="measured"] {{ background: {gray(layer(d) + MEASURED_LIFT)}; }} '
        for d in range(MAX_DEPTH + 2)   # deepest rule last, so the nearest layer wins
    ) + f"""
    QComboBox, QSpinBox, QLineEdit {{
        background: {gray(ctl)};
        border: none;
        border-radius: {RADIUS}px;
        padding: 0px 6px;
    }}
    QComboBox::drop-down {{ border: none; width: 18px; }}
    QSpinBox::up-button, QSpinBox::down-button {{ subcontrol-origin: padding; width: 18px; border: none; }}
    QComboBox QAbstractItemView {{
        background: {gray(layer(2))};
        border: 1px solid {gray(layer(2) + LINE_LIFT)};
        selection-background-color: {gray(layer(3))};
        outline: none;
    }}
    QCheckBox::indicator {{
        width: 14px; height: 14px; border-radius: 3px;
        background: {gray(ctl)}; border: none;
    }}
    QCheckBox::indicator:checked {{
        background: {ACCENT.name()}; image: url("{(GLYPHS / 'check.svg').as_posix()}");
    }}
    QSlider::groove:horizontal {{
        height: 4px; border-radius: 2px; background: {gray(layer(MAX_DEPTH) + LINE_LIFT)};
    }}
    QSlider::sub-page:horizontal {{ height: 4px; border-radius: 2px; background: {gray(INK_2)}; }}
    QSlider::handle:horizontal {{
        width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; background: {gray(INK)};
    }}
    QSlider::handle:horizontal:hover {{ background: {gray(HEAD)}; }}
    """


class Layer(QFrame):
    """A surface one step lighter than whatever it sits on."""

    def __init__(self, depth: int, name: str = "") -> None:
        super().__init__()
        self.setProperty("depth", str(depth))
        v = layer(depth)
        self.setStyleSheet(
            f"Layer {{ background: {gray(v)}; border-radius: {RADIUS}px;"
            f" border: 1px solid {gray(v + LINE_LIFT if depth else v)}; }}"
        )
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(PAD, PAD, PAD, PAD)
        self.body.setSpacing(GAP)
        if name:
            lab = QLabel(name[0].upper() + name[1:])
            lab.setProperty("role", "name")
            self.body.addWidget(lab)
            self.body.addSpacing(max(0, HEAD_GAP - GAP))


def label_col(texts: list[str]) -> int:
    """Wide enough for the widest description, so the control sits one gap from it."""
    metrics = QFontMetrics(ui_font())
    widest = max((metrics.horizontalAdvance(t) for t in texts), default=0)
    return max(LABEL_MIN, min(LABEL_MAX, widest + 2))


def desc_label(text: str, width: int) -> QLabel:
    lab = QLabel(text)
    lab.setProperty("role", "desc")
    lab.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    lab.setFixedWidth(width)
    return lab


def measured(text: str) -> QLabel:
    """A result the pipeline produced. Same slot as a control, flat and lighter, no edge, no hand cursor."""
    lab = QLabel(text)
    lab.setProperty("role", "measured")
    lab.setFont(mono_font())
    lab.setFixedWidth(SELECTOR_W)
    lab.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    lab.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return lab


def form(rows: list[tuple[str, list[str] | QWidget]]) -> QWidget:
    """A table: descriptions in one left-aligned column, controls in the next."""
    w = QWidget()
    g = QGridLayout(w)
    g.setContentsMargins(0, 0, 0, 0)
    g.setHorizontalSpacing(GAP)
    g.setVerticalSpacing(ROW_GAP)
    col = label_col([desc for desc, _ in rows])
    for r, (desc, ctl) in enumerate(rows):
        if isinstance(ctl, list):
            items, ctl = ctl, QComboBox()
            ctl.addItems(items)
        ctl.setFixedHeight(ROW_H)
        if isinstance(ctl, (QComboBox, QSpinBox, QLineEdit)):
            ctl.setFixedWidth(SELECTOR_W)
        g.setRowMinimumHeight(r, ROW_H)
        g.addWidget(desc_label(desc, col), r, 0)
        g.addWidget(ctl, r, 1, Qt.AlignmentFlag.AlignLeft)
    g.setColumnStretch(2, 1)
    return w


# ---- the chain: the tool cards of the superseded card-column UI, in this language -------------
# a knob is [name, lo, hi, value, unit, decimals]; a bool knob is [name, "bool", 0, value]
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


def _crop(x: int = 18, y: int = 22) -> list[Knob]:
    return [["x", 0, 100, x, "%", 0], ["y", 0, 100, y, "%", 0], ["w", 1, 100, 54, "%", 0], ["h", 1, 100, 46, "%", 0]]


def _rescale(f: float) -> list[Knob]:
    return [["factor", 0.1, 1.0, f, "", 2]]


STAGES: list[Stage] = [
    Stage("Video", [[]], src=True, note="arena_r1.mp4 · 462×456 · 59.94 fps"),
    Stage("Crop", [_crop(), _crop(40, 22), _crop(18, 55), _crop(40, 55)], pick=2),
    Stage("Rescale", [_rescale(0.5), _rescale(0.25)]),
    Stage("Threshold", [[["thresh", 0, 255, 128, "", 0], ["invert", "bool", 0, False]]], save="mask_r1", ext="avi"),
    Stage("Motion", [[["gate", 0.0, 30.0, 2.0, "", 1]]], save="motion_r1", ext="csv", plot=True),
]
MAX_ALTS = 8
_current = 2   # the selected card survives a rebuild


def lines_out(i: int) -> int:
    """How many lines Run would send out of stage i."""
    n = 1
    for stage in STAGES[: i + 1]:
        n *= len(stage.alts)
    return n


def viewed_line() -> int:
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


def card_w() -> int:
    return max(CARD_W, LABEL_MAX // 2 + GAP + SELECTOR_W + 2 * PAD)


def mono_font() -> QFont:
    font = QFont()
    font.setFamilies(MONO)
    font.setPixelSize(FONT_PX)
    font.setHintingPreference(QFont.HintingPreference(HINTING))
    return font


def qgray(v: int, alpha: int = 255) -> QColor:
    v = max(0, min(255, v))
    return QColor(v, v, v, alpha)


class GlyphButton(QAbstractButton):
    """A + or an x beside a name: tertiary ink, lifts to the next layer on hover."""

    def __init__(self, glyph: str, tip: str, on_click, *, enabled: bool = True) -> None:
        super().__init__()
        self._glyph, self._hover = glyph, False
        self.setToolTip(tip)
        self.setEnabled(enabled)
        self.setFixedSize(ROW_H - 4, ROW_H - 4)
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
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        box = QRectF(self.rect())
        if self._hover and self.isEnabled():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(qgray(layer(2)))
            p.drawRoundedRect(box, RADIUS - 1, RADIUS - 1)
        colour = qgray(INK if self._hover else INK_2, 255 if self.isEnabled() else 80)
        pen = QPen(colour, 1.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        c, a = box.center(), 3.0
        if self._glyph == "+":
            p.drawLine(QPointF(c.x() - a, c.y()), QPointF(c.x() + a, c.y()))
            p.drawLine(QPointF(c.x(), c.y() - a), QPointF(c.x(), c.y() + a))
        else:
            p.drawLine(QPointF(c.x() - a, c.y() - a), QPointF(c.x() + a, c.y() + a))
            p.drawLine(QPointF(c.x() + a, c.y() - a), QPointF(c.x() - a, c.y() + a))
        p.end()


class Figure(QWidget):
    """The motion trace: one layer deeper than the card it sits in."""
    _TRACE = [36, 30, 33, 19, 27, 24, 10, 22, 17, 30, 26, 13, 24, 20, 32, 28, 16, 25, 21, 29, 23, 18, 27, 31, 22]

    def __init__(self) -> None:
        super().__init__()
        self.setFixedHeight(ROW_H * 3)

    def paintEvent(self, event) -> None:
        del event
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QPen(qgray(layer(2) + LINE_LIFT), 1))
        p.setBrush(qgray(layer(2)))
        p.drawRoundedRect(box, RADIUS, RADIUS)
        inner = box.adjusted(1, 1, -1, -1)
        n = len(self._TRACE)
        step = inner.width() / (n - 1)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(AMBER.red(), AMBER.green(), AMBER.blue(), 50))
        for i, value in enumerate(self._TRACE):
            if value < 18:
                p.drawRect(QRectF(inner.left() + step * i - step / 2, inner.top(), step, inner.height()))
        pen = QPen(AMBER, 1)
        pen.setDashPattern([4, 3])
        p.setPen(pen)
        y = inner.top() + inner.height() * 0.41
        p.drawLine(QPointF(inner.left(), y), QPointF(inner.right(), y))
        p.setPen(QPen(ACCENT, 1.4))
        p.drawPolyline(QPolygonF([
            QPointF(inner.left() + step * i, inner.top() + inner.height() * value / 44)
            for i, value in enumerate(self._TRACE)
        ]))
        p.setPen(QPen(qgray(HEAD), 1.5))
        x = inner.left() + inner.width() * 0.42
        p.drawLine(QPointF(x, inner.top()), QPointF(x, inner.bottom()))
        p.end()


def knob_row(knob: Knob, on_change) -> QWidget:
    """Slider and its mono readout together fill the one control width."""
    name, lo, hi, value, unit, dec = knob
    scale = 10 ** dec
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(GAP)
    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setRange(round(lo * scale), round(hi * scale))
    slider.setValue(round(value * scale))
    slider.setFixedWidth(SELECTOR_W - VALUE_W - GAP)
    out = QLabel(fmt(knob))
    out.setFont(mono_font())
    out.setFixedWidth(VALUE_W)
    out.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def changed(raw: int) -> None:
        knob[3] = raw / scale
        out.setText(fmt(knob))
        on_change()

    slider.valueChanged.connect(changed)
    h.addWidget(slider)
    h.addWidget(out)
    w.setFixedWidth(SELECTOR_W)
    return w


class StepCard(QFrame):
    """A layer-1 card: name with + and x beside it, remove at the right, the viewed alternative's knobs."""

    def __init__(self, index: int, stage: Stage, column: "ChainColumn") -> None:
        super().__init__()
        self._index, self._stage, self._column = index, stage, column
        self._selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        body = QVBoxLayout(self)
        body.setContentsMargins(PAD, PAD, PAD, PAD)
        body.setSpacing(GAP)

        head = QHBoxLayout()
        head.setSpacing(4)
        name = QLabel(stage.name)
        name.setProperty("role", "name")
        head.addWidget(name)
        if not stage.src:
            head.addSpacing(4)
            head.addWidget(GlyphButton("+", "Split off an alternative: a copy of the viewed one, to change",
                                       lambda _=False: column.split(index)))
            if len(stage.alts) > 1:
                head.addWidget(GlyphButton("x", f"Drop alternative {stage.pick + 1}",
                                           lambda _=False: column.drop(index)))
        if stage.stale:
            busy = QLabel("recomputing")
            busy.setStyleSheet(f"color: {AMBER.name()};")
            head.addSpacing(4)
            head.addWidget(busy)
        head.addStretch(1)
        head.addWidget(GlyphButton("x", "The chain has to read something" if stage.src else "Remove this step",
                                   lambda _=False: None, enabled=not stage.src))
        body.addLayout(head)
        body.addSpacing(max(0, HEAD_GAP - GAP))

        if stage.src:
            note = QLabel(stage.note)
            note.setProperty("role", "readout")
            body.addWidget(note)
        rows: list[tuple[str, QWidget]] = []
        for knob in stage.alts[stage.pick]:
            if knob[1] == "bool":
                box = QCheckBox()
                box.setChecked(bool(knob[3]))
                box.stateChanged.connect(lambda _s: column.touched(index))
                rows.append((knob[0], box))
            else:
                rows.append((knob[0], knob_row(knob, lambda: column.touched(index))))
        if rows:
            body.addWidget(form(rows))
        if stage.plot:
            body.addWidget(Figure())
        if len(stage.alts) > 1:
            body.addSpacing(OUTLET_D // 2)  # the outlets straddle the foot; keep the last row clear

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            if not self._column.hit_outlet(self.mapToParent(event.position().toPoint())):
                self._column.select(self._index)
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        del event
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(qgray(layer(1)))
        p.drawRoundedRect(box, RADIUS, RADIUS)
        if self._stage.stale:
            p.setBrush(QColor(AMBER.red(), AMBER.green(), AMBER.blue(), 18))
            p.drawRoundedRect(box, RADIUS, RADIUS)
        pen = QPen(ACCENT if self._selected else qgray(layer(1) + LINE_LIFT), 1)
        if self._stage.src:
            pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(box, RADIUS, RADIUS)
        p.end()


class Overlay(QWidget):
    """Over the cards: paints the outlets, which straddle each card's foot."""

    def __init__(self, column: "ChainColumn") -> None:
        super().__init__(column)
        self._column = column
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

    def paintEvent(self, event) -> None:
        del event
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        for i, stage in enumerate(STAGES):
            if len(stage.alts) > 1:
                self._column.paint_outlets(p, i)
        p.end()


class ChainColumn(QWidget):
    """Cards on the ground, and between them the outlets, the arrow and the chips."""

    def __init__(self, pane: "ChainPane") -> None:
        super().__init__()
        self._pane = pane
        self.cards: list[StepCard] = []
        self._stale_timer = QTimer(self)
        self._stale_timer.setSingleShot(True)
        self._stale_timer.setInterval(900)
        self._stale_timer.timeout.connect(self._clear_stale)
        self.setFixedWidth(card_w() + 2 * PAD)
        column = QVBoxLayout(self)
        column.setContentsMargins(PAD, PAD, PAD, CARD_GAP // 2 + PAD)
        column.setSpacing(CARD_GAP)
        for index, stage in enumerate(STAGES):
            card = StepCard(index, stage, self)
            self.cards.append(card)
            column.addWidget(card)
        column.addStretch(1)
        self.cards[_current].set_selected(True)
        self._overlay = Overlay(self)
        self._overlay.raise_()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._overlay.setGeometry(self.rect())

    def select(self, index: int) -> None:
        global _current
        _current = index
        for i, card in enumerate(self.cards):
            card.set_selected(i == index)
        self._pane.refresh()
        self.update()

    def pick(self, index: int, k: int) -> None:
        global _current
        if STAGES[index].pick != k:
            STAGES[index].pick = k
            self._mark_stale(index)
        _current = index
        self._pane.rebuild()

    def split(self, index: int) -> None:
        global _current
        stage = STAGES[index]
        if len(stage.alts) >= MAX_ALTS:
            return
        stage.alts.append([list(k) for k in stage.alts[stage.pick]])
        stage.pick = len(stage.alts) - 1
        _current = index
        self._pane.rebuild()

    def drop(self, index: int) -> None:
        stage = STAGES[index]
        del stage.alts[stage.pick]
        stage.pick = min(stage.pick, len(stage.alts) - 1)
        self._mark_stale(index)
        self._pane.rebuild()

    def touched(self, index: int) -> None:
        was = [s.stale for s in STAGES]
        self._mark_stale(index)
        if was != [s.stale for s in STAGES]:
            self._pane.rebuild()   # the head grows a "recomputing" label

    def _mark_stale(self, index: int) -> None:
        for i, stage in enumerate(STAGES):
            stage.stale = i >= index and not stage.src
        self._stale_timer.start()

    def _clear_stale(self) -> None:
        for stage in STAGES:
            stage.stale = False
        self._pane.rebuild()

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

    def paintEvent(self, event) -> None:
        del event
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        for i in range(len(STAGES)):
            self._paint_gap(p, i)
        p.end()
        self._overlay.update()

    def paint_outlets(self, p: QPainter, index: int) -> None:
        stage = STAGES[index]
        r = OUTLET_D / 2
        p.setFont(mono_font())
        for k in range(len(stage.alts)):
            c = self._outlet_centre(index, k)
            picked = k == stage.pick
            if picked:
                p.setPen(QPen(ACCENT, 1))
                p.setBrush(ACCENT)
            else:
                p.setPen(QPen(qgray(layer(1) + LINE_LIFT), 1))
                p.setBrush(qgray(layer(1)))
            p.drawEllipse(c, r, r)
            p.setPen(QPen(qgray(HEAD) if picked else qgray(INK_2)))
            p.drawText(QRectF(c.x() - r, c.y() - r, OUTLET_D, OUTLET_D), Qt.AlignmentFlag.AlignCenter, str(k + 1))

    def _paint_gap(self, p: QPainter, index: int) -> None:
        stage = STAGES[index]
        rect = self.cards[index].geometry()
        n = len(stage.alts)
        last = index == len(STAGES) - 1
        count = lines_out(index)

        if not last:
            # the arrow: straight out of the viewed outlet, an S across, straight into the next head
            below = self.cards[index + 1].geometry()
            x0 = self._outlet_centre(index, stage.pick).x() if n > 1 else rect.center().x()
            x1 = below.center().x()
            top = rect.bottom() + 1 + (OUTLET_D / 2 if n > 1 else 0)
            end = below.top() - 6
            mid = (top + 6 + end - 9) / 2
            path = QPainterPath(QPointF(x0, top))
            path.lineTo(x0, top + 6)
            path.cubicTo(QPointF(x0, mid), QPointF(x1, mid), QPointF(x1, end - 9))
            path.lineTo(x1, end)
            p.setPen(QPen(ACCENT, 1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(ACCENT)
            p.drawPolygon(QPolygonF([QPointF(x1 - 4.5, end), QPointF(x1 + 4.5, end), QPointF(x1, end + 6)]))

        # the chips sit over the arrow: file pattern times count, and the count of lines
        p.setFont(mono_font())
        metrics = p.fontMetrics()
        chips: list[tuple[str, bool]] = []
        if stage.save:
            chips.append((f"⤓ {stage.save}_{suffix(index) or '…'}.{stage.ext}" + (f" ×{count}" if count > 1 else ""), True))
        chips.append((f"{count} line{'s' if count != 1 else ''}", False))
        y_mid = rect.bottom() + 1 + (CARD_GAP / 2 if not last else CARD_GAP / 4 + ROW_H / 2)
        x = rect.right() if not last else rect.center().x() + sum(metrics.horizontalAdvance(t) + 14 for t, _ in chips) / 2
        for text, boxed in reversed(chips):
            w = metrics.horizontalAdvance(text) + 12
            box = QRectF(x - w, y_mid - (ROW_H - 4) / 2, w, ROW_H - 4)
            if boxed:
                p.setPen(QPen(qgray(layer(1) + LINE_LIFT), 1))
                p.setBrush(qgray(layer(1)))
            else:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(qgray(GROUND))
            p.drawRoundedRect(box, RADIUS, RADIUS)
            p.setPen(QPen(qgray(INK_2)))
            p.drawText(box, Qt.AlignmentFlag.AlignCenter, text)
            x -= w + 4


class ChainPane(QWidget):
    """The strip that says which line is viewed, over the scrolling chain."""

    def __init__(self) -> None:
        super().__init__()
        self.setFixedWidth(card_w() + 2 * PAD + SCROLL_W + GAP)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(GAP)
        self._path = QLabel()
        self._path.setFont(mono_font())
        self._path.setProperty("role", "readout")
        self._path.setContentsMargins(PAD, 0, PAD, 0)
        self._path.setWordWrap(True)
        v.addWidget(self._path)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(
            "QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; }"
            f"QScrollBar:vertical {{ width: {SCROLL_W}px; margin: 0 0 0 {GAP}px; background: transparent; }}"
            f"QScrollBar::handle:vertical {{ background: {gray(layer(1) + LINE_LIFT)}; border-radius: {SCROLL_W // 2}px; min-height: 24px; }}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }")
        v.addWidget(self._scroll, 1)
        self.column: ChainColumn | None = None
        self._rebuild_now()

    def rebuild(self) -> None:
        """Deferred: callers are inside the signal or mouse event of a widget about to be destroyed."""
        QTimer.singleShot(0, self._rebuild_now)

    def _rebuild_now(self) -> None:
        self.column = ChainColumn(self)
        self._scroll.setWidget(self.column)
        self.refresh()

    def refresh(self) -> None:
        total = lines_out(len(STAGES) - 1)
        self._path.setText(f"viewing line {viewed_line() + 1} of {total}:  {path_text()}")


class Window(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("design language / layers")
        self.setStyleSheet(f"Window {{ background: {gray(GROUND)}; }}" + sheet())
        QApplication.setFont(ui_font())
        root = QVBoxLayout(self)
        root.setContentsMargins(PAD, PAD, PAD, PAD)
        root.setSpacing(GAP)
        row = QHBoxLayout()
        row.setSpacing(GAP)
        root.addLayout(row, 1)
        row.addWidget(ChainPane())
        row.addWidget(self.panel(), 2)
        row.addWidget(self.stack(), 1)
        root.addWidget(self.knobs())

    def panel(self) -> QWidget:
        """Layer 1 holds a tool; layer 2 a section of it; layer 3 the one open detail."""
        p = Layer(1, "tool")
        name = QLineEdit("colony 3, arena B")
        p.body.addWidget(form([
            ("name", name),
            ("input", ["camera 0", "camera 1", "file"]),
            ("colour", ["gray", "rgb", "lab"]),
            ("every", ["frame", "2nd frame", "4th frame"]),
            ("size", measured("462 × 456")),
            ("rate", measured("59.94 fps")),
        ]))
        sec = Layer(2, "motion")
        spin = QSpinBox()
        spin.setRange(4, 64)
        spin.setValue(16)
        on = QCheckBox("solve flow, not just change")
        sec.body.addWidget(form([
            ("method", ["lucas-kanade", "farneback", "difference"]),
            ("block", spin),
            ("flow", on),
        ]))
        detail = Layer(3, "window")
        detail.body.addWidget(form([
            ("sigma", ["1", "2", "4"]),
            ("reduce", ["mean", "max", "p95"]),
            ("mean speed", measured("3.2 px/s")),
            ("gated", measured("41 of 1 206 frames")),
        ]))
        sec.body.addWidget(detail)
        p.body.addWidget(sec)
        p.body.addStretch(1)
        return p

    def stack(self) -> QWidget:
        """The grays in order, plus the fourth we refuse, so the ceiling is visible."""
        outer = Layer(1, "layer 1")
        here: Layer = outer
        for d in range(2, MAX_DEPTH + 2):
            nxt = Layer(d, f"layer {d}" + ("  (not allowed)" if d > MAX_DEPTH else ""))
            here.body.addWidget(nxt)
            here = nxt
        here.body.addWidget(QLabel("ink on the deepest gray"))
        outer.body.addStretch(1)
        return outer

    def knobs(self) -> QWidget:
        k = Layer(1, "knobs")
        g = QGridLayout()
        g.setHorizontalSpacing(GAP)
        g.setVerticalSpacing(ROW_GAP)
        k.body.addLayout(g)
        self.readout = QLabel()
        self.readout.setProperty("role", "readout")
        self.readout.setWordWrap(True)
        specs = [("GROUND", 4, 60), ("STEP", 2, 24), ("LABEL_MIN", 0, 120), ("LABEL_MAX", 60, 240),
                 ("SELECTOR_W", 90, 260), ("ROW_H", 16, 32), ("PAD", 2, 24), ("GAP", 2, 24), ("ROW_GAP", 0, 12), ("HEAD_GAP", 0, 32), ("RADIUS", 0, 12),
                 ("INK", 140, 255), ("INK_2", 90, 200), ("LINE_LIFT", 0, 40), ("MEASURED_LIFT", 0, 60),
                 ("FONT_PX", 10, 16), ("FONT_WEIGHT", 300, 700), ("HINTING", 0, 3),
                 ("CARD_W", 0, 420), ("CARD_GAP", 24, 80), ("OUTLET_D", 14, 28), ("VALUE_W", 28, 60)]
        col = label_col([n.lower().replace("_", " ") for n, _, _ in specs])
        for i, (name, lo, hi) in enumerate(specs):
            s = QSlider(Qt.Orientation.Horizontal)
            s.setRange(lo, hi)
            s.setValue(globals()[name])
            s.setFixedWidth(SELECTOR_W)
            s.setFixedHeight(ROW_H)
            s.valueChanged.connect(lambda v, n=name: self.retune(n, v))
            s.sliderReleased.connect(self.rebuild)
            g.addWidget(desc_label(name.lower().replace("_", " "), col), i % 6, (i // 6) * 2)
            g.addWidget(s, i % 6, (i // 6) * 2 + 1)
        g.setColumnStretch(8, 1)
        k.body.addWidget(self.readout)
        self.show_values()
        return k

    def retune(self, name: str, v: int) -> None:
        globals()[name] = v
        self.show_values()

    def rebuild(self) -> None:
        global _live
        new = Window()
        new.setGeometry(self.geometry())
        new.show()
        paint_caption(new)
        _live = new
        self.close()

    def show_values(self) -> None:
        grays = "  ".join(f"L{d}={layer(d)}" for d in range(MAX_DEPTH + 1))
        self.readout.setText(
            f"GROUND={GROUND} STEP={STEP}  ({grays})  LABEL_MIN={LABEL_MIN} LABEL_MAX={LABEL_MAX} SELECTOR_W={SELECTOR_W} ROW_H={ROW_H}"
            f"  PAD={PAD} GAP={GAP} ROW_GAP={ROW_GAP} HEAD_GAP={HEAD_GAP} RADIUS={RADIUS}  HEAD={HEAD} INK={INK} INK_2={INK_2} LINE_LIFT={LINE_LIFT} MEASURED_LIFT={MEASURED_LIFT}"
            f"  font={QApplication.font().family()} FONT_PX={FONT_PX} FONT_WEIGHT={FONT_WEIGHT} HINTING={HINTING}"
            f"  CARD_W={CARD_W} CARD_GAP={CARD_GAP} OUTLET_D={OUTLET_D} VALUE_W={VALUE_W}"
        )


if __name__ == "__main__":
    if sys.platform == "win32":
        # DirectWrite ignores the hinting preference and draws ClearType colour fringes on a dark
        # ground; FreeType honours full hinting and renders grayscale. Must be set before the app.
        os.environ.setdefault("QT_QPA_PLATFORM", "windows:fontengine=freetype")
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.Round)  # 125% becomes 100%, 150% becomes 200%: no fractional blur
    app = QApplication(sys.argv)
    install_font(app)
    _live = Window()
    _live.resize(1100, 760)
    _live.show()
    paint_caption(_live)
    sys.exit(app.exec())
