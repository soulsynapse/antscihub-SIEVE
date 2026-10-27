"""The design language, settled from mock-up/design-language: dark first, four grays, forms as tables.

Ground is a dark gray and everything sits on it. Each surface layered on top is one STEP lighter;
nothing is inset past layer 3, so there are exactly four grays. A form is a table: descriptions
left-aligned in one column sized to the widest, every control one width and one height in the
next. Editable controls are wells the ground shows through; measured results are flat fields
lifted above their surface, so depth alone says what can be touched. Section names are the only
white; inside a section there is one ink and a dimmer one for readouts.
"""
from __future__ import annotations

import ctypes
import sys
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QFontMetrics, QPainter, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QAbstractSpinBox, QApplication, QComboBox, QFrame, QGridLayout, QLabel,
                               QSplitter, QSplitterHandle,
                               QLineEdit, QPushButton, QVBoxLayout, QWidget)

GROUND = 31        # ground gray, 0-255
STEP = 9           # how much lighter each layer is
MAX_DEPTH = 3      # layers above ground
LABEL_MIN = 40     # a form's description column is its widest label, clamped to these, px
LABEL_MAX = 160
CONTROL_W = 160    # every control in a form, px
WIDE_W = 328       # a wide measured field, px: two controls and the gap between, for a file name
ROW_H = 22         # every form row and every control in it, px
PAD = 8            # inset per layer, px
GAP = 8            # between blocks inside a layer, px
ROW_GAP = 2        # between rows of a form, px
HEAD_GAP = 14      # below a section name, px; the room that makes it read as a title
RADIUS = 4
HEAD = 255         # section names, the only pure white on screen
INK = 200          # everything inside a section: descriptions and values alike
INK_2 = 140        # tertiary: readouts, slider handles, unchecked boxes
LINE_LIFT = 20     # a layer's hairline edge is this much lighter than the layer
MEASURED_LIFT = 18 # a measured result is a flat field this much lighter than the surface it sits on
HOVER_LIFT = 4     # a node under the pointer is this much lighter, its edge brightened to match
HOVER_EDGE = 125   # QColor.lighter() factor for that node's edge, percent
FONT_PX = 12       # integer pixels, never points, so glyphs sit on the grid under display scaling
FONT_WEIGHT = 500  # regular Inter reads thin on dark; 500 fills the stroke without reading bold
HINTING = 3        # QFont.HintingPreference: full. DirectWrite ignores it; see play()
VALUE_W = 36       # a slider's mono readout
GLYPH = 16         # a line icon beside 12px text, px
GLYPH_STROKE = 2.25  # Tabler ships 2, which reads thin at GLYPH; widened at render, never in the files
ACCENT = QColor(88, 146, 255)   # what is viewed: the loop window, the trace
AMBER = QColor(222, 160, 56)    # the gate
RED = QColor(232, 72, 72)       # an input nothing feeds, a wire whose types no longer fit
TYPE_HUES = {"bgr": 30, "gray": 165, "path": 275}   # a connector's hue per product type; a type not here is hashed
TYPE_SV = (150, 225)            # every connector's saturation and value, so the hue alone says the type
MONO = ["Cascadia Mono", "Consolas", "Menlo", "DejaVu Sans Mono", "monospace"]
FAMILIES = ["Inter", "Segoe UI Variable Text", "Segoe UI", "SF Pro Text", "Helvetica Neue", "Helvetica", "Arial"]
HERE = Path(__file__).parent
FONTS, GLYPHS = HERE / "fonts", HERE / "glyphs"   # bundled, so Mac and Windows render alike


def gray(v: int) -> str:
    v = max(0, min(255, v))
    return f"rgb({v},{v},{v})"


def qgray(v: int, alpha: int = 255) -> QColor:
    v = max(0, min(255, v))
    return QColor(v, v, v, alpha)


def layer(depth: int) -> int:
    return GROUND + STEP * depth


@lru_cache(maxsize=None)
def glyph(name: str, ink: int, size: int = GLYPH, ratio: float = 1.0) -> QPixmap:
    """GLYPHS/<name>.svg drawn in the gray `ink` at `size` px, for a screen of pixel `ratio`. The
    files keep Tabler's `currentColor` and 2-unit stroke; both are set here."""
    src = (GLYPHS / f"{name}.svg").read_text(encoding="utf-8")
    src = src.replace("currentColor", qgray(ink).name()).replace('stroke-width="2"', f'stroke-width="{GLYPH_STROKE}"')
    pm = QPixmap(round(size * ratio), round(size * ratio))
    pm.setDevicePixelRatio(ratio)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    QSvgRenderer(src.encode()).render(p, QRectF(0, 0, size, size))
    p.end()
    return pm


def install_font(app: QApplication) -> str:
    """Bundled faces first, then the first family the platform has; returns what was chosen."""
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


def mono_font() -> QFont:
    font = QFont()
    font.setFamilies(MONO)
    font.setPixelSize(FONT_PX)
    font.setHintingPreference(QFont.HintingPreference(HINTING))
    return font


def paint_caption(w: QWidget) -> None:
    """Windows 11: the title bar takes the ground gray too. Elsewhere, or on failure, a no-op."""
    if sys.platform != "win32":
        return
    try:
        hwnd = int(w.winId())
        dwm = ctypes.windll.dwmapi
        colorref = ctypes.c_int((GROUND << 16) | (GROUND << 8) | GROUND)
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(colorref), 4)   # DWMWA_CAPTION_COLOR
        text = ctypes.c_int((INK << 16) | (INK << 8) | INK)
        dwm.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(text), 4)       # DWMWA_TEXT_COLOR
    except (AttributeError, OSError):
        pass


def sheet() -> str:
    """The application stylesheet. Controls are wells: the ground shows through them at every depth."""
    ctl = GROUND
    return f"""
    QWidget {{ color: {gray(INK)}; }}
    QMainWindow, QMainWindow > QWidget {{ background: {gray(GROUND)}; }}
    QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QSplitter::handle {{ background: {gray(GROUND)}; }}
    QMenuBar {{ background: {gray(GROUND)}; }}
    QMenuBar::item:selected {{ background: {gray(layer(1))}; }}
    QMenu {{ background: {gray(layer(2))}; border: 1px solid {gray(layer(2) + LINE_LIFT)}; }}
    QMenu::item:selected {{ background: {gray(layer(3))}; }}
    QLabel[role="desc"] {{ color: {gray(INK)}; }}
    QLabel[role="name"] {{ color: {gray(HEAD)}; }}
    QLabel[role="readout"] {{ color: {gray(INK_2)}; }}
    QLabel[role="measured"] {{ border: none; border-radius: {RADIUS}px; padding: 0px 6px;
                               background: {gray(layer(1) + MEASURED_LIFT)}; }}
    """ + "".join(
        f'Layer[depth="{d}"] QLabel[role="measured"] {{ background: {gray(layer(d) + MEASURED_LIFT)}; }} '
        for d in range(MAX_DEPTH + 1)   # deepest rule last, so the nearest layer wins
    ) + f"""
    QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit, QPushButton {{
        background: {gray(ctl)};
        border: none;
        border-radius: {RADIUS}px;
        padding: 0px 6px;
    }}
    QPushButton:hover {{ background: {gray(layer(2))}; }}
    QPushButton:pressed {{ background: {gray(layer(3))}; }}
    QPushButton:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{ color: {gray(INK_2 - 50)}; }}
    QComboBox::drop-down {{ border: none; width: 18px; }}
    QSpinBox::up-button, QSpinBox::down-button,
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ subcontrol-origin: padding; width: 18px; border: none; }}
    QComboBox QAbstractItemView {{
        background: {gray(layer(2))};
        border: 1px solid {gray(layer(2) + LINE_LIFT)};
        selection-background-color: {gray(layer(3))};
        outline: none;
    }}
    QCheckBox::indicator {{
        width: 14px; height: 14px; border-radius: 3px;
        background: {gray(ctl)}; border: 1px solid {gray(layer(2) + LINE_LIFT)};
    }}
    QCheckBox::indicator:checked {{
        background: {ACCENT.name()}; border: 1px solid {ACCENT.name()};
        image: url("{(GLYPHS / 'check.svg').as_posix()}");
    }}
    QSlider::groove:horizontal {{
        height: 4px; border-radius: 2px; background: {gray(layer(MAX_DEPTH) + LINE_LIFT)};
    }}
    QSlider::sub-page:horizontal {{ height: 4px; border-radius: 2px; background: {gray(INK_2)}; }}
    QSlider::handle:horizontal {{
        width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; background: {gray(INK)};
    }}
    QSlider::handle:horizontal:hover {{ background: {gray(HEAD)}; }}
    QScrollBar:vertical {{ width: 8px; margin: 0; background: transparent; }}
    QScrollBar::handle:vertical {{ background: {gray(layer(1) + LINE_LIFT)}; border-radius: 4px; min-height: 24px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
    QToolTip {{ background: {gray(layer(2))}; color: {gray(INK)}; border: 1px solid {gray(layer(2) + LINE_LIFT)}; padding: 2px 6px; }}
    """


class Layer(QFrame):
    """A surface one step lighter than whatever it sits on, named in white if it has a name."""

    def __init__(self, depth: int, name: str = "", parent=None) -> None:
        super().__init__(parent)
        self.depth = depth
        self.setProperty("depth", str(depth))
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(PAD, PAD, PAD, PAD)
        self.body.setSpacing(GAP)
        self.head = None
        if name:
            self.head = QLabel(name[0].upper() + name[1:])
            self.head.setProperty("role", "name")
            self.body.addWidget(self.head)
            self.body.addSpacing(max(0, HEAD_GAP - GAP))

    def add(self, w: QWidget, stretch: int = 0) -> None:
        self.body.addWidget(w, stretch)

    def paintEvent(self, event) -> None:
        del event
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QPen(qgray(layer(self.depth) + LINE_LIFT), 1) if self.depth else Qt.PenStyle.NoPen)
        p.setBrush(qgray(layer(self.depth)))
        p.drawRoundedRect(box, RADIUS, RADIUS)
        p.end()


class Grip(QSplitterHandle):
    """A splitter handle that says it can be dragged: five dots down its middle, tertiary ink,
    white under the pointer."""
    DOT, STEP = 2, 6   # a dot's diameter and the pitch between dots, px

    def __init__(self, orientation, parent) -> None:
        super().__init__(orientation, parent)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(qgray(HEAD if self.underMouse() else INK_2))
        cx, cy, r = self.width() / 2, self.height() / 2, self.DOT / 2
        for i in range(-2, 3):
            if self.orientation() == Qt.Orientation.Horizontal:
                p.drawEllipse(QPointF(cx, cy + i * self.STEP), r, r)
            else:
                p.drawEllipse(QPointF(cx + i * self.STEP, cy), r, r)
        p.end()

    def event(self, e):
        if e.type() in (e.Type.HoverEnter, e.Type.HoverLeave):
            self.update()
        return super().event(e)


class Splitter(QSplitter):
    """A QSplitter whose handles are Grips."""

    def createHandle(self) -> QSplitterHandle:
        return Grip(self.orientation(), self)


def label_col(texts: list[str]) -> int:
    """Wide enough for the widest description, so the control sits one gap from it."""
    metrics = QFontMetrics(ui_font())
    widest = max((metrics.horizontalAdvance(t) for t in texts), default=0)
    return max(LABEL_MIN, min(LABEL_MAX, widest + 2))


def desc_label(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setProperty("role", "desc")
    lab.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    return lab


def readout(text: str = "", mono: bool = False, wrap: bool = True) -> QLabel:
    """A line in the dimmer ink: a path, a status, what the pipeline said."""
    lab = QLabel(text)
    lab.setProperty("role", "readout")
    if mono:
        lab.setFont(mono_font())
    lab.setWordWrap(wrap)
    lab.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return lab


def measured(text: str = "", wide: bool = False) -> QLabel:
    """A result the pipeline produced. Same slot as a control, flat and lighter, no edge, no hand
    cursor. `wide` is two controls' width, for a file name; the caller elides what is longer."""
    lab = QLabel(text)
    lab.setProperty("role", "measured")
    lab.setFont(mono_font())
    lab.setFixedHeight(ROW_H)
    if wide:
        lab.setMinimumWidth(CONTROL_W)
        lab.setMaximumWidth(WIDE_W)   # yields to the row when the column is narrow
    else:
        lab.setFixedWidth(CONTROL_W)
    lab.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    lab.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return lab


class Form(QWidget):
    """A table: descriptions in one left-aligned column, controls in the next. Rows may be added
    after construction; the description column is resized to the widest each time. A line is a
    row with no description, indented to the control column: a value that belongs to the row
    above, a path, a status."""

    def __init__(self, rows: list[tuple[str, QWidget]] = (), parent=None) -> None:
        super().__init__(parent)
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(GAP)
        self._grid.setVerticalSpacing(ROW_GAP)
        self._grid.setColumnStretch(2, 1)
        self._descs: list[QLabel] = []
        self.rows: list[tuple[QLabel | None, QWidget]] = []
        for desc, ctl in rows:
            self.add_row(desc, ctl)

    def add_line(self, w: QWidget) -> QWidget:
        r = len(self.rows)
        self.rows.append((None, w))
        self._grid.addWidget(w, r, 1, 1, 2)
        return w

    def add_row(self, desc: str, ctl: QWidget) -> QWidget:
        r = len(self.rows)
        ctl.setFixedHeight(ROW_H)
        if isinstance(ctl, (QComboBox, QAbstractSpinBox, QLineEdit, QPushButton)):
            ctl.setFixedWidth(CONTROL_W)
        lab = desc_label(desc)
        self._descs.append(lab)
        self.rows.append((lab, ctl))
        self._grid.setRowMinimumHeight(r, ROW_H)
        self._grid.addWidget(lab, r, 0)
        if ctl.property("role") == "measured" and ctl.maximumWidth() > CONTROL_W:
            self._grid.addWidget(ctl, r, 1, 1, 2)   # a wide field takes the row
        else:
            self._grid.addWidget(ctl, r, 1, Qt.AlignmentFlag.AlignLeft)
        col = label_col([d.text() for d in self._descs])
        for d in self._descs:
            d.setFixedWidth(col)
        return ctl

    def set_row_visible(self, r: int, on: bool) -> None:
        for w in self.rows[r]:
            if w is not None:
                w.setVisible(on)
        self._grid.setRowMinimumHeight(r, ROW_H if on else 0)   # a hidden row leaves no gap
