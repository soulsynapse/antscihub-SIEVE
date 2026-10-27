"""Dev > Reference > Icons: every icon in the Tabler catalogue, drawn by Qt the way the window would
draw it, with the knobs that decide how a vendored one will look: size, stroke, ink, filled.

The catalogue is tabler.zip beside this file, written by build_icons.py beside it; it is not in
the repo, so the sheet offers the download when it is missing. The sheet paints its own tiles, so five thousand icons cost one widget
and one pixmap each per knob setting. Tabler draws its filled style as separate icons, so the filled
knob shows those and only those. The filter matches names and Tabler's tags; a click puts the name
on the clipboard; the tooltip is the tags.

Two marks record Kendrick's judgement and persist in marks.json beside this file, which is in the
repo: a double-click makes an icon a favourite (accent outline), a right-click marks it no use
(drawn dim). Three show knobs, unmarked / favourites / no use, pick which kinds the sheet shows;
no use starts hidden.
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLineEdit, QPushButton, QScrollArea, QToolTip,
                               QVBoxLayout, QWidget)

from ... import theme
from ...theme import ACCENT, GAP, HEAD, INK, INK_2, PAD, RADIUS, layer, qgray
from ...widgets import ParamWidget
from . import build_icons

ZIP = build_icons.ZIP
MARKS = Path(__file__).with_name("marks.json")
KINDS = ("unmarked", "favorites", "no use")
SIZE = 20       # the sheet opens at this; the window's glyphs sit at 16 beside 12px text
STROKE = 2.25   # Tabler ships 2, which reads thin at SIZE; widened here, never in the files
TILE_W = 128    # a tile with its name under the icon; nameless tiles are square


@dataclass
class Icon:
    name: str
    body: str                               # the outline svg's children: paths in a 24-unit box
    filled: str = ""                        # the filled style's children, for the icons that have one
    tags: list[str] = field(default_factory=list)
    cats: list[str] = field(default_factory=list)

    def svg(self, ink: QColor, stroke: float = STROKE, filled: bool = False) -> bytes:
        if filled and self.filled:
            inner, paint = self.filled, f'fill="{ink.name()}" stroke="none"'
        else:
            inner, paint = self.body, (f'fill="none" stroke="{ink.name()}" stroke-width="{stroke}" '
                                       f'stroke-linecap="round" stroke-linejoin="round"')
        return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {paint}>{inner}</svg>'.encode()


_BACKDROP = '<path stroke="none" d="M0 0h24v24H0z" fill="none" />'   # Tabler's invisible first path


def read_icons(path: Path = ZIP) -> tuple[list[Icon], str, str]:
    """(icons by name, the release version, the licence text) from a zip build_icons.py wrote."""
    icons: dict[str, Icon] = {}
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        for n in names:
            p = Path(n)
            if p.suffix == ".svg" and p.parent.name in ("outline", "filled"):
                src = z.read(n).decode("utf-8")
                body = " ".join(src.split(">", 1)[1].rsplit("</svg>", 1)[0].split())
                body = body.replace(_BACKDROP, "").strip()
                icon = icons.setdefault(p.stem, Icon(p.stem, ""))
                if p.parent.name == "filled":
                    icon.filled = body
                else:
                    icon.body = body
        if "icons.json" in names:
            for name, meta in json.loads(z.read("icons.json")).items():
                if name in icons:
                    icons[name].tags = [str(t) for t in meta.get("tags", [])]   # a tag can be a bare number
                    icons[name].cats = [meta["category"]] if meta.get("category") else []
        version = z.read("VERSION").decode().strip() if "VERSION" in names else "?"
        licence = z.read("LICENSE").decode("utf-8") if "LICENSE" in names else ""
    return [icons[k] for k in sorted(icons) if icons[k].body], version, licence


class Marks:
    """The two sets of names, read from and written to MARKS as they change."""

    def __init__(self, path: Path | None = None):
        self.path = path = MARKS if path is None else path
        self.favorites: set[str] = set()
        self.no_use: set[str] = set()
        if path.exists():
            d = json.loads(path.read_text(encoding="utf-8"))
            self.favorites, self.no_use = set(d.get("favorites", [])), set(d.get("no_use", []))

    def toggle(self, which: set[str], name: str) -> None:
        which.symmetric_difference_update({name})
        d = {"favorites": sorted(self.favorites), "no_use": sorted(self.no_use)}
        self.path.write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8")

    def kind(self, name: str) -> str:
        return "favorites" if name in self.favorites else "no use" if name in self.no_use else "unmarked"


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

    def __init__(self, icons: list[Icon], marks: Marks, parent=None):
        super().__init__(parent)
        self.all, self.shown, self.marks = icons, icons, marks
        self.size, self.stroke, self.ink, self.filled = SIZE, STROKE, INK, False
        self.names, self.tips = False, False
        self.show = {"unmarked", "favorites"}
        self.query, self.cols = "", 1
        self.setMouseTracking(True)
        self.setMinimumWidth(TILE_W)

    def tile_w(self) -> int:
        return TILE_W if self.names else self.size + 16

    def tile_h(self) -> int:
        return self.size + (32 if self.names else 16)

    def set_knobs(self, size: int, stroke: float, ink: int, filled: bool, names: bool, tips: bool,
                  show: set[str] = frozenset(KINDS)) -> None:
        self.size, self.stroke, self.ink, self.filled = size, stroke, ink, filled
        self.names, self.tips = names, tips
        self.show = show
        self.filter(self.query)

    def filter(self, text: str) -> int:
        q = self.query = text.strip().lower()
        m = self.marks
        self.shown = [i for i in self.all if (not q or q in i.name or any(q in t for t in i.tags))
                      and (i.filled or not self.filled)
                      and m.kind(i.name) in self.show]
        self._relayout()
        return len(self.shown)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._relayout()

    def _relayout(self):
        self.cols = max(1, self.width() // self.tile_w())
        rows = math.ceil(len(self.shown) / self.cols)
        self.setMinimumHeight(rows * self.tile_h())
        self.update()

    def _at(self, pos) -> Icon | None:
        c, r = pos.x() // self.tile_w(), pos.y() // self.tile_h()
        k = r * self.cols + c
        return self.shown[k] if c < self.cols and 0 <= k < len(self.shown) else None

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setFont(theme.mono_font())
        ratio, tw, th, s = self.devicePixelRatioF(), self.tile_w(), self.tile_h(), self.size
        ink, under = qgray(self.ink), self._at(self.mapFromGlobal(self.cursor().pos()))
        dim, m = qgray(INK_2 - 50), self.marks
        clip = e.rect()
        for r in range(clip.top() // th, clip.bottom() // th + 1):
            for c in range(self.cols):
                k = r * self.cols + c
                if k >= len(self.shown):
                    break
                icon = self.shown[k]
                box = QRect(c * tw, r * th, tw, th).adjusted(1, 1, -1, -1)
                p.setPen(ACCENT if icon.name in m.favorites else Qt.PenStyle.NoPen)
                p.setBrush(qgray(layer(2 if icon is under else 1)))
                p.drawRoundedRect(box, RADIUS, RADIUS)
                pm = _pixmap(icon.svg(dim if icon.name in m.no_use else ink, self.stroke, self.filled), s, ratio)
                p.drawPixmap(box.center().x() - s // 2, box.top() + 7, pm)
                if self.names:
                    p.setPen(qgray(INK_2))
                    name = p.fontMetrics().elidedText(icon.name, Qt.TextElideMode.ElideMiddle, box.width() - 6)
                    p.drawText(box.adjusted(3, s + 9, -3, -3), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, name)
        p.end()

    def mouseMoveEvent(self, e):
        icon = self._at(e.position().toPoint())
        if self.tips:
            QToolTip.showText(e.globalPosition().toPoint(), f"{icon.name}\n{', '.join(icon.tags)}" if icon else "", self)
        self.update()

    def leaveEvent(self, e):
        super().leaveEvent(e)
        self.update()

    def mousePressEvent(self, e):
        icon = self._at(e.position().toPoint())
        if icon is None:
            return
        if e.button() == Qt.MouseButton.RightButton:
            self.marks.toggle(self.marks.no_use, icon.name)
            self.filter(self.query)
        else:
            QApplication.clipboard().setText(icon.name)

    def mouseDoubleClickEvent(self, e):
        icon = self._at(e.position().toPoint())
        if icon is not None and e.button() == Qt.MouseButton.LeftButton:
            self.marks.toggle(self.marks.favorites, icon.name)
            self.filter(self.query)


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
        self.params.add_bool("names", False)
        self.params.add_bool("tooltips", False)
        for k in KINDS:
            self.params.add_bool(f"show {k}", k != "no use")
        knobs.add(self.params)
        self.count = theme.readout(mono=True)
        knobs.add(self.count)
        knobs.body.addStretch(1)
        self.note = theme.readout()
        knobs.add(self.note)
        knobs.setFixedWidth(theme.LABEL_MAX + theme.CONTROL_W + GAP + PAD * 2)
        lay.addWidget(knobs, 0)

        self.fetch = QPushButton(f"Download Tabler Icons {build_icons.VERSION}")
        self.fetch.clicked.connect(self._download)
        knobs.body.insertWidget(knobs.body.indexOf(self.count), self.fetch)
        self.sheet = None
        self.setWindowTitle("Icons")
        self._load()

    def _load(self) -> None:
        """Show the catalogue if it is here, else the download button in its place."""
        try:
            icons, version, _ = read_icons()
        except (OSError, zipfile.BadZipFile) as e:
            self.note.setText(f"no catalogue at {ZIP}" + (f": {e}" if ZIP.exists() else "") +
                              ". It is an MIT download, gitignored; the button fetches it.")
            self.params.setEnabled(False)
            self.fetch.show()
            return
        self.fetch.hide()
        self.params.setEnabled(True)
        self.setWindowTitle(f"Tabler Icons {version}")
        self.note.setText("click copies the name; double-click marks a favourite; right-click marks no use; "
                          "tooltips show the name and Tabler's tags; filled shows only the icons Tabler also draws filled")
        self.sheet = Sheet(icons, Marks())
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(self.sheet)
        self.layout().addWidget(scroll, 1)
        self.find.textChanged.connect(self._filter)
        self.params.changed.connect(self._knobs)
        self._filter("")
        self.find.setFocus()

    def _download(self) -> None:
        self.fetch.setEnabled(False)
        self.note.setText(f"fetching {build_icons.RELEASE.format(v=build_icons.VERSION)}…")
        QApplication.processEvents()
        try:
            build_icons.download()
        except OSError as e:
            self.note.setText(f"download failed: {e}")
            self.fetch.setEnabled(True)
            return
        self._load()

    def _knobs(self):
        p = self.params.params()
        self.sheet.set_knobs(int(p["size"]), float(p["stroke"]), int(p["ink"]), bool(p["filled"]),
                             bool(p["names"]), bool(p["tooltips"]), {k for k in KINDS if p[f"show {k}"]})
        self._count()

    def _filter(self, text):
        self.sheet.filter(text)
        self._count()

    def _count(self):
        self.count.setText(f"{len(self.sheet.shown)} of {len(self.sheet.all)}")
