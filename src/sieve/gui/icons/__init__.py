"""Lucide's line icons, tinted to the palette and handed out as `QIcon`s.

Held beside `palette.py` and above `frame` for the same reason it is: a card, a
nav entry and a menu all draw the same arrow, and an icon set owned by any one
of them would be imported back out of it by the others.

The glyphs these replace were single characters — → ⇄ ◆ ✕ — which the widget
could hand to `setText` and the stylesheet could recolour with `color:`. An icon
is a pixmap and neither is true of it: it has to be drawn at the colour it will
be seen at, and every state that used to be a stylesheet rule is now a separate
drawing. So `icon()` returns all of them at once, as the three modes Qt already
switches between — `Normal`, `Active` under the pointer, `Disabled` — and the
call site keeps the one line it had.

The SVGs are vendored under `lucide/` rather than depended on: they are a
handful of files of two paths each, the set changes on Lucide's release schedule
and not ours, and a tuning loop that must not stall is not somewhere to discover
an icon went missing. `lucide/LICENSE` is the ISC notice they arrive under,
which the copies have to carry. What is vendored at any moment is what `names()`
answers, and that folder is the only authority on it.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from sieve.gui.palette import ACCENT, DIM, LINE, rgb

_SVG = Path(__file__).parent / "lucide"

#: How big an icon is where nothing says otherwise. Sized against the text it
#: sits in a row with rather than against the 24px the SVGs are drawn at, so the
#: label sets the height of a row like the card's head.
SIZE = 16

#: Lucide draws its strokes 2 units wide in a 24-unit box, which lands near one
#: physical pixel at `SIZE` and reads as grey rather than as a line. Widened
#: here, at the one place the number is applied, rather than in the vendored
#: files, which stay byte-identical to what upstream shipped.
_STROKE = 2.25


def names() -> tuple[str, ...]:
    """Every glyph there is to ask for, in the order a list of them reads in.

    The folder and not a written-down list, because the two would be a pair that
    can disagree and only one of them can be drawn: a name here with no file
    behind it raises at the first `icon()`, and a file nobody listed would be
    invisible to the bench that exists to show what is vendored. Uncached, so a
    glyph dropped in while the tree is being edited is there the next time the
    bench is opened rather than the next time the process starts — which is the
    only caller, and the cost is one directory listing.
    """
    return tuple(sorted(path.stem for path in _SVG.glob("*.svg")))


@lru_cache(maxsize=None)
def _source(name: str) -> str:
    """The SVG as Lucide ships it. Read once per name and kept — the file is a
    few hundred bytes and the alternative is a stat per repaint."""
    path = _SVG / f"{name}.svg"
    if not path.is_file():
        raise KeyError(f"no vendored lucide icon named {name!r} (looked in {_SVG})")
    return path.read_text(encoding="utf-8")


def _dressed(name: str, colour: QColor, filled: bool) -> bytes:
    """The SVG with its `currentColor` resolved, since nothing here is CSS.

    Lucide's convention is `stroke="currentColor" fill="none"`, which a browser
    resolves against the surrounding text colour and `QSvgRenderer` does not
    resolve at all. Substituting the literal is the whole of the tint.

    Written through the palette's own `rgb()`, which is a functional notation
    SVG shares with the stylesheets. Not `QColor.name()`: Qt spells an alpha
    channel `#AARRGGBB` and SVG reads a trailing `#RRGGBBAA`, so a colour with
    an alpha would be silently rejected by the renderer and the icon would come
    back with no stroke at all — invisible rather than wrong.

    `filled` paints the interior in the same colour, which is how a state that
    was two glyphs — hollow ◇ against solid ◆ — stays one icon: the same shape,
    with and without its inside, rather than two drawings that could drift.
    """
    ink = rgb(colour)
    svg = _source(name).replace('stroke="currentColor"', f'stroke="{ink}"')
    svg = svg.replace('stroke-width="2"', f'stroke-width="{_STROKE}"')
    if filled:
        svg = svg.replace('fill="none"', f'fill="{ink}"')
    return svg.encode("utf-8")


def _ratio() -> float:
    """The device pixel ratio to draw for. The primary screen's, because a
    pixmap is drawn once and Qt will scale it down onto a coarser screen more
    gracefully than it invents detail scaling one up."""
    app = QGuiApplication.instance()
    screen = app.primaryScreen() if app is not None else None
    return max(1.0, screen.devicePixelRatio() if screen is not None else 1.0)


def pixmap(name: str, colour: QColor, size: int = SIZE, filled: bool = False) -> QPixmap:
    """One icon, one colour, at `size` logical pixels.

    Drawn at the screen's ratio and then told what that ratio was, so the pixmap
    reports `size` to the layout while holding enough pixels to be sharp — a
    16px icon rendered at 16 physical pixels on a 200% display is the blurry
    result that makes a line icon set look worse than the glyphs it replaced.

    Cached on the colour's `rgba` rather than the `QColor` itself, which is
    mutable and hands the cache a key that can change under it; and on the ratio
    as well as the size, so a pixmap drawn before there was a screen to ask is
    not the one still being handed out after there is one.
    """
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
    """A lucide icon in the three colours a button is ever seen in.

    The defaults are what the cards already wore: dim at rest, accent under the
    pointer, and the hairline colour when refused. A button that means something
    while it sits there — the pinned ◆ — passes its own `normal` and gets the
    accent without the hover having to be involved.

    `Active` and not `Selected`: `Active` is the mode Qt asks for while the
    pointer is over the widget, which is what the `:hover` rule these replace
    was keyed on.
    """
    out = QIcon()
    out.addPixmap(pixmap(name, normal, size, filled), QIcon.Mode.Normal)
    out.addPixmap(pixmap(name, active, size, filled), QIcon.Mode.Active)
    out.addPixmap(pixmap(name, disabled, size, filled), QIcon.Mode.Disabled)
    return out
