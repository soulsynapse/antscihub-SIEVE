"""The utility's look: its grays, the stylesheet, the font, and line glyphs from its own glyphs/ folder
drawn on square buttons. It copies the player's layered grays by value rather than importing them,
so a later change to the player's theme does not reach it."""
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QAbstractButton, QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout

GLYPHS = Path(__file__).parent / "glyphs"
GROUND, STEP = 31, 9           # the ground gray and how much lighter each surface on it is
HEAD, INK, INK_2 = 255, 200, 140
LINE_LIFT = 20
RADIUS = 4
GLYPH = 18
GLYPH_STROKE = 2               # Tabler's own; read at 18px it needs no widening
BUTTON = 28                    # a glyph button's side
RAIL_BUTTON = 34               # a drawing mode's, in the rail
FAMILIES = ["Inter", "Segoe UI Variable Text", "Segoe UI", "SF Pro Text", "Helvetica Neue", "Arial"]


def layer(depth):
    return GROUND + STEP * depth


def gray(v, alpha=255):
    v = max(0, min(255, v))
    return QColor(v, v, v, alpha)


def css(v):
    return gray(v).name()


STYLE = f"""
QMainWindow, QWidget#ground {{ background: {css(GROUND)}; }}
QWidget {{ color: {css(INK)}; }}
QFrame#panel {{ background: {css(layer(1))}; border-radius: {RADIUS + 2}px; }}
QFrame#rail {{ background: {css(layer(1))}; border-radius: {RADIUS + 2}px; }}
QLabel {{ background: transparent; }}
QLabel[role="head"] {{ color: {css(HEAD)}; font-weight: 600; }}
QLabel[role="readout"] {{ color: {css(INK_2)}; }}
QLabel[role="name"] {{ color: {css(INK)}; }}
QLineEdit {{ background: {css(GROUND)}; border: none; border-radius: {RADIUS}px; padding: 3px 6px;
             selection-background-color: {css(layer(4))}; }}
QLineEdit:focus {{ border: 1px solid {css(layer(1) + LINE_LIFT + 30)}; }}
QTableWidget, QListWidget {{ background: {css(GROUND)}; border: none; border-radius: {RADIUS}px; outline: none;
                             gridline-color: transparent; selection-background-color: {css(layer(4))};
                             selection-color: {css(HEAD)}; }}
QTableWidget::item {{ padding: 2px 6px; border: none; }}
QTableWidget::item:selected {{ background: {css(layer(4))}; color: {css(HEAD)}; }}
QListWidget::item {{ padding: 3px 6px; border-radius: {RADIUS}px; }}
QListWidget::item:hover {{ background: {css(layer(2))}; }}
QListWidget::item:selected {{ background: {css(layer(4))}; color: {css(HEAD)}; }}
QHeaderView::section {{ background: {css(GROUND)}; color: {css(INK_2)}; border: none; padding: 3px 6px; }}
QSlider::groove:horizontal {{ height: 4px; background: {css(layer(3) + LINE_LIFT)}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ height: 4px; background: {css(INK_2)}; border-radius: 2px; }}
QSlider::handle:horizontal {{ width: 12px; margin: -5px 0; background: {css(INK)}; border-radius: 6px; }}
QToolTip {{ background: {css(layer(2))}; color: {css(INK)}; border: 1px solid {css(layer(2) + LINE_LIFT)}; }}
QScrollBar:vertical {{ background: transparent; width: 8px; }}
QScrollBar::handle:vertical {{ background: {css(layer(3))}; border-radius: 4px; min-height: 20px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 8px; }}
QScrollBar::handle:horizontal {{ background: {css(layer(3))}; border-radius: 4px; min-width: 20px; }}
QPushButton {{ background: {css(layer(2))}; border: none; border-radius: {RADIUS}px; padding: 4px 10px; }}
QPushButton:hover {{ background: {css(layer(3))}; }}
QMessageBox, QInputDialog {{ background: {css(layer(1))}; }}
"""


def styled(app):
    have = set(QFontDatabase.families())
    font = QFont(next((f for f in FAMILIES if f in have), app.font().family()))
    font.setPixelSize(12)
    app.setFont(font)
    app.setStyleSheet(STYLE)


@lru_cache(maxsize=None)
def glyph(name, ink, size=GLYPH, ratio=1.0):
    """glyphs/<name>.svg drawn in the gray `ink` at `size` px for a screen of pixel `ratio`."""
    src = (GLYPHS / f"{name}.svg").read_text(encoding="utf-8")
    src = src.replace("currentColor", gray(ink).name()).replace('stroke-width="2"', f'stroke-width="{GLYPH_STROKE}"')
    pm = QPixmap(round(size * ratio), round(size * ratio))
    pm.setDevicePixelRatio(ratio)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    QSvgRenderer(src.encode()).render(p, QRectF(0, 0, size, size))
    p.end()
    return pm


class GlyphButton(QAbstractButton):
    """A square button with a line glyph centred, lifted under the pointer and dim when disabled.
    `checkable` makes it hold a state, shown on a lighter well; `on`, when given, is the glyph shown
    while checked. `tip` is its tooltip, the only place its name is written."""

    def __init__(self, glyph_name, tip, checkable=False, on=None, side=BUTTON, parent=None):
        super().__init__(parent)
        self.off, self.on = glyph_name, on
        self.setCheckable(checkable)
        self.setFixedSize(side, side)
        self.setToolTip(tip)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def sizeHint(self):
        return QSize(self.width(), self.height())

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        lit = self.isEnabled() and (self.underMouse() or self.isDown())
        if self.isChecked():
            p.setPen(QPen(gray(layer(4) + LINE_LIFT), 1))
            p.setBrush(gray(layer(4)))
            p.drawRoundedRect(r, RADIUS, RADIUS)
        elif lit:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(gray(layer(3)))
            p.drawRoundedRect(r, RADIUS, RADIUS)
        name = self.on if self.isChecked() and self.on else self.off
        ink = INK_2 - 60 if not self.isEnabled() else HEAD if self.isChecked() or lit else INK
        pm = glyph(name, ink, GLYPH, self.devicePixelRatioF())
        p.drawPixmap(QPointF((self.width() - GLYPH) / 2, (self.height() - GLYPH) / 2), pm)
        p.end()

    def event(self, e):
        if e.type() in (e.Type.HoverEnter, e.Type.HoverLeave):
            self.update()
        return super().event(e)


def label(text="", role="readout"):
    lab = QLabel(text)
    lab.setProperty("role", role)
    return lab


class ElidedLabel(QLabel):
    """A one-line label that takes the width it is given rather than its text's, eliding the text in
    the middle to fit; `text()` stays the whole of it."""

    def __init__(self, text="", role="readout", parent=None):
        super().__init__(parent)
        self.setProperty("role", role)
        self._full = ""
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setText(text)

    def setText(self, text):
        self._full = text
        self._fit()

    def text(self):
        return self._full

    def _fit(self):
        super().setText(self.fontMetrics().elidedText(self._full, Qt.TextElideMode.ElideMiddle, max(0, self.width())))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fit()


class Panel(QFrame):
    """A surface one step above the ground, its `title` in white at the head of the row `head`, which
    takes buttons at the right; `body` is the column below."""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(10, 8, 10, 10)
        self.body.setSpacing(6)
        self.head = QHBoxLayout()
        self.head.setSpacing(2)
        self.head.addWidget(label(title, "head"))
        self.head.addStretch(1)
        self.body.addLayout(self.head)
