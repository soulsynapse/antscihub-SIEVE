"""Corner radius and text sizes for every view — the shape counterpart to palette."""

from __future__ import annotations

from typing import NamedTuple

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from sieve import settings


class Text(NamedTuple):
    """A text role: its settings key, user-facing label, and gloss."""

    key: str
    label: str
    gloss: str


TEXTS: tuple[Text, ...] = (
    Text("heading", "headings", "the line naming a whole card or pane"),
    Text("name", "names", "the bold name on a card, a row, or a section"),
    Text("gloss", "glosses", "the quiet line under a name, saying what it is for"),
)

RADIUS_MIN = 0
RADIUS_MAX = 16  # past this a stack of cards reads as a stack of buttons
RADIUS_DEFAULT = 6

SIZE_MIN = 7  # where hinting stops resolving on a 1x display
SIZE_MAX = 20  # where the fixed-height cards stop fitting their rows

# Asymmetric on purpose: headings are what gets enlarged, and a gloss more
# than three under the base would fall below the base's own floor.
TRIM_MIN = -3
TRIM_MAX = 8

_RADIUS_KEY = "visuals.radius"
_SIZE_KEY = "text.size"


def _trim_key(role: str) -> str:
    return f"text.{role}"


class _Notifier(QObject):
    changed = Signal()


# prevent GC: a bound Signal does not prevent its owner's collection
_notifier = _Notifier()

CHANGED = _notifier.changed

_system: int | None = None


def radius() -> int:
    """Corner radius in pixels; call at draw time, not import."""
    return _clamp(settings.stored(_RADIUS_KEY, RADIUS_DEFAULT), RADIUS_MIN, RADIUS_MAX)


def size() -> int:
    """Base text size in points; defaults to the platform's own."""
    return _clamp(settings.stored(_SIZE_KEY, _system_size()), SIZE_MIN, SIZE_MAX)


def trim(role: str) -> int:
    """Offset from the base for this role, in points (default 0)."""
    return _clamp(settings.stored(_trim_key(role), 0), TRIM_MIN, TRIM_MAX)


def pt(role: str) -> int:
    """Resolved font-size for this role; floored at SIZE_MIN."""
    return max(SIZE_MIN, size() + trim(role))


def use_radius(pixels: int) -> None:
    """Round every card to this from here on, and again next run."""
    _set(_RADIUS_KEY, _clamp(pixels, RADIUS_MIN, RADIUS_MAX))


def use_size(points: int) -> None:
    """Set the base size; pushes onto QApplication.font before emitting CHANGED."""
    if not _set(_SIZE_KEY, _clamp(points, SIZE_MIN, SIZE_MAX), announce=False):
        return
    _install()
    CHANGED.emit()


def use_text(role: str, points: int) -> None:
    """Draw this role this far off the base from here on, and again next run."""
    _set(_trim_key(role), _clamp(points, TRIM_MIN, TRIM_MAX))


def reset() -> None:
    """Forget all stored metrics; keys are deleted, not written back at defaults."""
    for key in (_RADIUS_KEY, _SIZE_KEY, *(_trim_key(text.key) for text in TEXTS)):
        settings.forget(key)
    _install()
    CHANGED.emit()


def install() -> None:
    """Call once after QApplication exists; reads the platform size before overwriting it."""
    # must snapshot platform size before _install overwrites the app font
    _system_size()
    _install()


def _install() -> None:
    application = QApplication.instance()
    if application is None:
        return
    font = application.font()
    if font.pointSize() == size():
        return
    font.setPointSize(size())
    application.setFont(font)


def _system_size() -> int:
    """Platform font size, cached on first call — read-once because use_size overwrites the app font."""
    global _system
    if _system is not None:
        return _system
    application = QApplication.instance()
    if application is None:
        return 9
    font = application.font()
    if font.pointSize() > 0:
        _system = font.pointSize()
    elif font.pixelSize() > 0:
        # pointSize() is -1 on some Linux desktops; convert from pixels
        _system = max(SIZE_MIN, round(font.pixelSize() * 72 / 96))
    else:
        _system = 9
    return _system


def _clamp(value: object, low: int, high: int) -> int:
    """Coerce to int in [low, high]; non-numeric values become low."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return low
    return max(low, min(high, int(value)))


def _set(key: str, value: int, announce: bool = True) -> bool:
    """Write to settings and return whether the clamped value changed.

    Written before the comparison, not after — `palette.use()`'s bargain:
    re-picking the value already on screen is the user insisting on it, and
    the document may not hold it.
    """
    changed = _current(key) != value
    settings.remember(key, value)
    if changed and announce:
        CHANGED.emit()
    return changed


def _current(key: str) -> int:
    """Clamped value in force, so a stored out-of-range value compares equal to its clamp."""
    if key == _RADIUS_KEY:
        return radius()
    if key == _SIZE_KEY:
        return size()
    return trim(key.split(".", 1)[1])
