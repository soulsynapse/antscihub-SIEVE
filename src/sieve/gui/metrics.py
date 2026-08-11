"""How round the cards are and how large the text is, for every view at once.

The counterpart to `palette.py` and held beside it for the same reason: these
are the numbers a view draws at rather than numbers a view owns, and a corner
radius that lived in `primitives/card.py` would be a radius the section card
had to import out of the middle of the card it is not.

It is the same shape as the palette module, with one difference that decides
the whole file. A palette's live values are `QColor`s, and a `QColor` is
mutable — so a view that did `from palette import PANEL` at import is holding
the object that *becomes* the new colour, and a `paintEvent` needs nothing said
to it. An `int` cannot be mutated in place, so there is nothing to hand out and
hold: every reader here calls `radius()` or `pt()` at the moment it draws. That
is a function call in a paint path, which is affordable exactly because these
are cards and chrome and not the frame loop this project promises not to stall.

Text is one base size and a trim per role, not four independent sizes. The base
is what the whole application is set in — it is pushed into `QApplication`'s own
font, so it reaches every label the tree never named as well as the ones it did
— and a role's number says only how that role sits against it. That is the
arrangement that survives the gesture users actually make: *everything here is
too small* is one control, and the trims keep meaning what they meant. Four
absolutes would make the same gesture four edits, three of which the user would
have to remember to keep in step.

Every trim defaults to zero, so the tree comes up in exactly the type it had
before this module existed — one size, told apart by weight and by colour. What
these controls buy is the ability to pull those apart, not a scale imposed on a
user who never asked for one. A preferences section that restyled the
application on first sight of it would be a section deciding for them.

Nothing here is a preference the GUI may decide by itself: `use_radius` and
`use_text` write to the settings document, on the same terms and for the same
reason `palette.use()` does — so a size changed by something that is not the
preferences card is remembered too, and there is no way to change one that
skips the place that records it.
"""

from __future__ import annotations

from typing import NamedTuple

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from sieve import settings


class Text(NamedTuple):
    """One kind of text the application draws, and what it is called to a user.

    Named for what is on the screen — a heading, a name, the quiet line under a
    name — and never for the object name a stylesheet reaches it by: a role
    called `#pgloss` is a role only the person who wrote that sheet can find.

    `key` is both the settings key's tail and the token a sheet asks for, so
    there is one spelling of a role rather than one to store it under and
    another to draw it with.
    """

    key: str
    label: str
    gloss: str


#: The text the tree actually distinguishes, which is three things and not more.
#: A fourth role invented here would be a control with nothing behind it — the
#: sheets in `primitives/` and `view/` name exactly these, and a role no sheet
#: asks for is a slider that does nothing.
TEXTS: tuple[Text, ...] = (
    Text("heading", "headings", "the line naming a whole card or pane"),
    Text("name", "names", "the bold name on a card, a row, or a section"),
    Text("gloss", "glosses", "the quiet line under a name, saying what it is for"),
)

#: What a corner may be set to. Zero is a square card and is offered rather than
#: floored at one: a user who wants no rounding at all wants none, and the
#: smallest non-zero radius is not that. The top is where a column of cards stops
#: reading as a stack of cards and starts reading as a stack of buttons, which is
#: the argument `card.py` made for its 6 in the first place — past this the shape
#: is the pill that argument was against.
RADIUS_MIN = 0
RADIUS_MAX = 16
RADIUS_DEFAULT = 6

#: What the base may be set to, in points. The floor is where the hinting on a
#: normal-weight face stops resolving on a 1x display; the ceiling is a size at
#: which the fixed-height cards in this tree stop fitting their own rows, and it
#: is a ceiling and not a scaling rule because a card that resized itself to its
#: text would move the list the user is arrowing down (`sections.py`).
SIZE_MIN = 7
SIZE_MAX = 20

#: How far a role may be trimmed off the base. Asymmetric on purpose: a heading
#: is the role anyone reaches for room to enlarge, and a gloss dropped more than
#: three points under the base is smaller than the floor the base itself has.
TRIM_MIN = -3
TRIM_MAX = 8

#: What the settings document calls these. Dotted rather than nested, because the
#: document is one flat object by decision (`settings.py`) and a dot is how a key
#: says which group it belongs to without the file growing a tree.
_RADIUS_KEY = "visuals.radius"
_SIZE_KEY = "text.size"


def _trim_key(role: str) -> str:
    return f"text.{role}"


class _Notifier(QObject):
    """Carrier for the one signal — a `Signal` has to live on a `QObject`."""

    changed = Signal()


#: Held so it is not collected out from under the signal: a bound `Signal` does
#: not keep its owner alive.
_notifier = _Notifier()

#: A size or a radius has moved. Whoever built a stylesheet out of one has to
#: build it again, and whoever paints with one needs only a repaint — the same
#: two obligations `palette.CHANGED` carries, and connected in the same slots.
#: They are two signals and not one because they are two questions: a view that
#: only paints its corner has nothing to redo when a colour changes, and vice
#: versa, and a single "redress" signal would make every widget in the tree pay
#: for both every time either moved.
CHANGED = _notifier.changed

#: The platform's own interface size, or `None` until something has asked for it
#: — see `_system_size()`, which is the only thing allowed to fill it.
_system: int | None = None


def radius() -> int:
    """How round a card's corners are, in pixels.

    Read at the moment of drawing rather than handed out at import, for the
    reason the module docstring gives: an `int` cannot become a different `int`
    under a holder the way a `QColor` becomes a different colour.
    """
    return _clamp(settings.stored(_RADIUS_KEY, RADIUS_DEFAULT), RADIUS_MIN, RADIUS_MAX)


def size() -> int:
    """The base text size in points — what the application is set in.

    The default is the platform's own, and that is deliberate: a number written
    here would be this project overriding a system-wide accessibility setting on
    every machine whose user had already answered this question once, for the
    whole desktop.
    """
    return _clamp(settings.stored(_SIZE_KEY, _system_size()), SIZE_MIN, SIZE_MAX)


def trim(role: str) -> int:
    """How far this role sits off the base, in points. Zero for a role that has
    never been set, which is every one of them until a user moves it."""
    return _clamp(settings.stored(_trim_key(role), 0), TRIM_MIN, TRIM_MAX)


def pt(role: str) -> int:
    """What this role is drawn at, in points, for a stylesheet's `font-size`.

    Floored at `SIZE_MIN` rather than allowed to follow the arithmetic down: the
    base and the trim are each in range on their own, and the pair at their
    extremes is a legal setting that reaches four points. A control the user
    cannot see the effect of is one they cannot undo.
    """
    return max(SIZE_MIN, size() + trim(role))


def use_radius(pixels: int) -> None:
    """Round every card to this from here on, and again next run."""
    _set(_RADIUS_KEY, _clamp(pixels, RADIUS_MIN, RADIUS_MAX))


def use_size(points: int) -> None:
    """Set the whole application in this size from here on, and again next run.

    `QApplication`'s own font is what carries it to the text no sheet names — a
    tooltip, a menu entry, a scrollbar's own label — and the roles below pick it
    up through `pt()` when they rebuild on `CHANGED`. Pushed before the signal
    goes out, so a sheet built in a slot is built against the size now in force
    rather than the one being replaced.
    """
    if not _set(_SIZE_KEY, _clamp(points, SIZE_MIN, SIZE_MAX), announce=False):
        return
    _install()
    CHANGED.emit()


def use_text(role: str, points: int) -> None:
    """Draw this role this far off the base from here on, and again next run."""
    _set(_trim_key(role), _clamp(points, TRIM_MIN, TRIM_MAX))


def reset() -> None:
    """Put the corner and all four sizes back to what they came at.

    The keys are forgotten rather than written back at their defaults, and for
    the base that is the whole of the argument: its default is the platform's
    own size (`size()`), so a reset that stored today's reading would override a
    system-wide accessibility setting the moment the user next changed it there
    — which is the thing this module refuses to do on a first run and should not
    do on a reset either. The radius and the trims are forgotten on the milder
    version of the same point: a default here is a number this file may revise.

    One `CHANGED` for all five, with the font installed before it goes out —
    `use_size`'s order, for `use_size`'s reason.
    """
    for key in (_RADIUS_KEY, _SIZE_KEY, *(_trim_key(text.key) for text in TEXTS)):
        settings.forget(key)
    _install()
    CHANGED.emit()


def install() -> None:
    """Put the remembered base size on the application, before anything is built.

    Called once on the way up, from the entry point that made the
    `QApplication`, and not at import: this module is imported by widget modules
    whose own import happens before there is an application to set a font on, and
    a `QApplication.instance()` of `None` at that moment is not an error to
    handle but the ordinary case.

    Skipping it costs a size and never a crash. Every reader here goes to the
    settings document rather than to the application's font, so the roles are
    right either way; what is lost is the size of the text no sheet names, which
    stays at the platform's until the user next moves the control.
    """
    # The platform's size is read here rather than left to whoever first needs
    # it, and this is the only moment it can be: the line below writes the
    # remembered size onto the application's own font, and every reading after
    # that is this module's answer coming back (`_system_size()`). The reader
    # that would otherwise be first is `reset()`, which runs after a whole
    # session of the font carrying something else.
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
    """The size the platform sets its own interface in, as it was before this
    module touched it.

    Held after the first ask, and that is not an optimisation. `use_size` writes
    the chosen size into the application's own font, so a second reading of that
    font afterwards is this module's own answer coming back — and the platform's
    size is the value a forgotten setting has to fall back to. Asked once,
    before anything has been set, it is the platform's; asked again later it
    would be whatever was last chosen, which would quietly make "no setting"
    mean "the last setting" for every run after the first.

    `pointSize()` is -1 for a font specified in pixels, which is what some Linux
    desktops hand over, so the pixel size is converted rather than trusted to be
    absent — and the last fallback is a number reached only when there is no
    application at all, which is a test and not a run, and is not remembered so
    that the real answer is still available once there is one.
    """
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
        # 72 points to the inch against the 96 dpi Qt assumes for a logical
        # pixel; the exact ratio matters less than not returning -1.
        _system = max(SIZE_MIN, round(font.pixelSize() * 72 / 96))
    else:
        _system = 9
    return _system


def _clamp(value: object, low: int, high: int) -> int:
    """A stored number brought into range, and anything that is not a number
    brought into existence at the low end.

    The document outlives the run that wrote it and is a file the user is invited
    to edit (`settings.py`), so a string, a float, or a radius of 400 all arrive
    here — and every one of them has to come out as an `int` a `paintEvent` can
    use, because the alternative is a traceback in a paint path.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return low
    return max(low, min(high, int(value)))


def _set(key: str, value: int, announce: bool = True) -> bool:
    """Remember a number and say whether it was a change.

    Written before the comparison rather than after it, which is `palette.use()`'s
    bargain and made here for the same reason: what the document holds and what
    the run is drawing at can differ — an unwritable settings file leaves the run
    at a size nothing recorded — and re-picking the value already on screen is
    exactly the gesture a user makes to insist on it.
    """
    changed = _current(key) != value
    settings.remember(key, value)
    if changed and announce:
        CHANGED.emit()
    return changed


def _current(key: str) -> int:
    """What is in force under `key` now, through the same clamp a reader uses —
    so a stored 400 and a stored 16 both compare equal to the 16 being set, and
    neither redraws the tree for a change nobody would see."""
    if key == _RADIUS_KEY:
        return radius()
    if key == _SIZE_KEY:
        return size()
    return trim(key.split(".", 1)[1])
