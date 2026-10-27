"""Dev > Reference > Icons: every icon in the Lucide catalogue, drawn by Qt the way the window would
draw it, with the knobs that decide how a vendored one will look: size, stroke, ink, filled.

The catalogue is mock-up/reference/lucide.zip, written by mock-up/reference/build_icons.py; this
reads it and never fetches. The sheet paints its own tiles, so two thousand icons cost one widget
and one pixmap each per knob setting. The filter matches names and Lucide's tags; a click puts
the name on the clipboard; the tooltip is the tags.
"""
from __future__ import annotations

import json
import math
import zipfile
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLineEdit, QScrollArea, QToolTip, QVBoxLayout, QWidget

from ... import theme
from ...theme import GAP, HEAD, INK, INK_2, PAD, RADIUS, layer, qgray
from ...widgets import ParamWidget

ZIP = Path(__file__).resolve().parents[3] / "mock-up" / "reference" / "lucide.zip"
SIZE = 16       # the icon beside 12px text; Lucide's box is 24
STROKE = 2.25   # Lucide ships 2, which reads thin at SIZE; widened here, never in the files
TILE_W = 128


@dataclass
class Icon:
    name: str
    body: str                               # the svg's children: paths in a 24-unit box
    tags: list[str] = field(default_factory=list)
    cats: list[str] = field(default_factory=list)

    def svg(self, ink: QColor, stroke: float = STROKE, filled: bool = False) -> bytes:
        fill = ink.name() if filled else "none"
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{fill}" '
                f'stroke="{ink.name()}" stroke-width="{stroke}" stroke-linecap="round" '
                f'stroke-linejoin="round">{self.body}</svg>').encode()


def read_icons(path: Path = ZIP) -> tuple[list[Icon], str, str]:
    """(icons by name, the release tag, the licence text) from a zip build_icons.py wrote."""
    icons: dict[str, Icon] = {}
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        for n in names:
            p = Path(n)
            if p.suffix == ".svg":
                src = z.read(n).decode("utf-8")
                body = " ".join(src.split(">", 1)[1].rsplit("</svg>", 1)[0].split())
                icons.setdefault(p.stem, Icon(p.stem, "")).body = body
        for n in names:
            p = Path(n)
            if p.suffix == ".json" and p.stem in icons:
                meta = json.loads(z.read(n))
                icons[p.stem].tags = list(meta.get("tags", []))
                icons[p.stem].cats = list(meta.get("categories", []))
        version = z.read("VERSION").decode().strip() if "VERSION" in names else "?"
        licence = z.read("LICENSE").decode("utf-8") if "LICENSE" in names else ""
    return [icons[k] for k in sorted(icons)], version, licence


@lru_cache(maxsize=None)
def _pixmap(svg: bytes, size: int, ratio: float) -> QPixmap:
    pm = QPixmap(round(size * ratio), round(size * ratio))
    pm.setDevicePixelRatio(ratio)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    QSvgRenderer(svg).render(p, QRectF(0, 0, size, size))
    p.end()
    return pm


class Sheet(QWidget):
    """The grid, painted: only the rows in view are drawn, each icon rendered once per knob setting."""

    def __init__(self, icons: list[Icon], parent=None):
        super().__init__(parent)
        self.all, self.shown = icons, icons
        self.size, self.stroke, self.ink, self.filled = SIZE, STROKE, INK, False
        self.cols = 1
        self.setMouseTracking(True)
        self.setMinimumWidth(TILE_W)

    def tile_h(self) -> int:
        return self.size + 32

    def set_knobs(self, size: int, stroke: float, ink: int, filled: bool) -> None:
        self.size, self.stroke, self.ink, self.filled = size, stroke, ink, filled
        self._relayout()

    def filter(self, text: str) -> int:
        q = text.strip().lower()
        self.shown = [i for i in self.all if not q or q in i.name or any(q in t for t in i.tags)]
        self._relayout()
        return len(self.shown)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._relayout()

    def _relayout(self):
        self.cols = max(1, self.width() // TILE_W)
        rows = math.ceil(len(self.shown) / self.cols)
        self.setMinimumHeight(rows * self.tile_h())
        self.update()

    def _at(self, pos) -> Icon | None:
        c, r = pos.x() // TILE_W, pos.y() // self.tile_h()
        k = r * self.cols + c
        return self.shown[k] if c < self.cols and 0 <= k < len(self.shown) else None

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setFont(theme.mono_font())
        ratio, th, s = self.devicePixelRatioF(), self.tile_h(), self.size
        ink, under = qgray(self.ink), self._at(self.mapFromGlobal(self.cursor().pos()))
        clip = e.rect()
        for r in range(clip.top() // th, clip.bottom() // th + 1):
            for c in range(self.cols):
                k = r * self.cols + c
                if k >= len(self.shown):
                    break
                icon = self.shown[k]
                box = QRect(c * TILE_W, r * th, TILE_W, th).adjusted(1, 1, -1, -1)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(qgray(layer(2 if icon is under else 1)))
                p.drawRoundedRect(box, RADIUS, RADIUS)
                pm = _pixmap(icon.svg(ink, self.stroke, self.filled), s, ratio)
                p.drawPixmap(box.center().x() - s // 2, box.top() + 7, pm)
                p.setPen(qgray(INK_2))
                name = p.fontMetrics().elidedText(icon.name, Qt.TextElideMode.ElideMiddle, box.width() - 6)
                p.drawText(box.adjusted(3, s + 9, -3, -3), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, name)
        p.end()

    def mouseMoveEvent(self, e):
        icon = self._at(e.position().toPoint())
        QToolTip.showText(e.globalPosition().toPoint(), f"{icon.name}\n{', '.join(icon.tags)}" if icon else "", self)
        self.update()

    def leaveEvent(self, e):
        super().leaveEvent(e)
        self.update()

    def mousePressEvent(self, e):
        icon = self._at(e.position().toPoint())
        if icon is not None:
            QApplication.clipboard().setText(icon.name)


class Icons(QWidget):
    """The window: the knobs in a layer on the left, the sheet scrolling on the right."""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setStyleSheet(theme.sheet())
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.resize(TILE_W * 8 + theme.CONTROL_W + theme.LABEL_MAX + PAD * 4 + GAP * 3, 640)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(PAD, PAD, PAD, PAD)
        lay.setSpacing(GAP)

        knobs = theme.Layer(1, "icons")
        self.find = QLineEdit()
        self.find.setPlaceholderText("name or tag")
        self.params = ParamWidget()
        self.params.form.add_row("find", self.find)
        self.params.add_int("size", 8, 48, SIZE)
        self.params.add_float("stroke", 1.0, 4.0, STROKE, decimals=2)
        self.params.add_int("ink", INK_2 - 60, HEAD, INK)
        self.params.add_bool("filled", False)
        knobs.add(self.params)
        self.count = theme.readout(mono=True)
        knobs.add(self.count)
        knobs.body.addStretch(1)
        self.note = theme.readout()
        knobs.add(self.note)
        knobs.setFixedWidth(theme.LABEL_MAX + theme.CONTROL_W + GAP + PAD * 2)
        lay.addWidget(knobs, 0)

        try:
            icons, version, _ = read_icons()
        except (OSError, zipfile.BadZipFile) as e:
            self.setWindowTitle("Icons")
            self.note.setText(f"no catalogue at {ZIP}: {e}. Run mock-up/reference/build_icons.py <release>.")
            self.params.setEnabled(False)
            return
        self.setWindowTitle(f"Lucide {version}")
        self.note.setText("click a tile to copy its name; the tooltip is Lucide's tags")
        self.sheet = Sheet(icons)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(self.sheet)
        lay.addWidget(scroll, 1)
        self.find.textChanged.connect(self._filter)
        self.params.changed.connect(self._knobs)
        self._filter("")
        self.find.setFocus()

    def _knobs(self):
        p = self.params.params()
        self.sheet.set_knobs(int(p["size"]), float(p["stroke"]), int(p["ink"]), bool(p["filled"]))

    def _filter(self, text):
        n = self.sheet.filter(text)
        self.count.setText(f"{n} of {len(self.sheet.all)}")
