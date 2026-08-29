"""Lucide line icons, tinted to the palette and returned as QPixmaps/QIcons."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from sieve.gui.palette import ACCENT, DIM, LINE, rgb

_SVG = Path(__file__).parent / "lucide"

#: Sized to the text it sits beside, not the SVG's 24-unit box.
SIZE = 16

#: Lucide's 2px stroke is too thin at SIZE; widened here, not in vendored files.
_STROKE = 2.25


def names() -> tuple[str, ...]:
    """Available glyph names, read fresh from the folder each call."""
    return tuple(sorted(path.stem for path in _SVG.glob("*.svg")))


@lru_cache(maxsize=None)
def _source(name: str) -> str:
    path = _SVG / f"{name}.svg"
    if not path.is_file():
        raise KeyError(f"no vendored lucide icon named {name!r} (looked in {_SVG})")
    return path.read_text(encoding="utf-8")


def _dressed(name: str, colour: QColor, filled: bool) -> bytes:
    # rgb() not QColor.name() — Qt writes #AARRGGBB, SVG expects #RRGGBBAA.

    ink = rgb(colour)
    svg = _source(name).replace('stroke="currentColor"', f'stroke="{ink}"')
    svg = svg.replace('stroke-width="2"', f'stroke-width="{_STROKE}"')
    if filled:
        svg = svg.replace('fill="none"', f'fill="{ink}"')
    return svg.encode("utf-8")


def _ratio() -> float:
    app = QGuiApplication.instance()
    screen = app.primaryScreen() if app is not None else None
    return max(1.0, screen.devicePixelRatio() if screen is not None else 1.0)


def pixmap(name: str, colour: QColor, size: int = SIZE, filled: bool = False) -> QPixmap:
    # Cache key is colour.rgba(), not the QColor — QColor is mutable.

    return _cached(name, colour.rgba(), size, filled, _ratio())


@lru_cache(maxsize=None)
def _cached(name: str, rgba: int, size: int, filled: bool, ratio: float) -> QPixmap:
    colour = QColor.fromRgba(rgba)
    out = QPixmap(round(size * ratio), round(size * ratio))
    out.setDevicePixelRatio(ratio)
    out.fill(Qt.GlobalColor.transparent)
    painter = QPainter(out)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    QSvgRenderer(_dressed(name, colour, filled)).render(
        painter, QRectF(0, 0, size, size)
    )
    painter.end()
    return out


def icon(
    name: str,
    normal: QColor = DIM,
    active: QColor = ACCENT,
    disabled: QColor = LINE,
    size: int = SIZE,
    filled: bool = False,
) -> QIcon:
    """Build a QIcon with Normal / Active / Disabled pixmaps."""
    out = QIcon()
    out.addPixmap(pixmap(name, normal, size, filled), QIcon.Mode.Normal)
    out.addPixmap(pixmap(name, active, size, filled), QIcon.Mode.Active)
    out.addPixmap(pixmap(name, disabled, size, filled), QIcon.Mode.Disabled)
    return out
