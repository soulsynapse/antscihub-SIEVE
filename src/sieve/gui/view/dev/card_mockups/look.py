"""Card-look candidates: dress × arrangement pairs for the gallery bench."""

from __future__ import annotations

from typing import Callable, NamedTuple

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from sieve.gui import icons, palette
from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, PANEL_HOT, STACK_BG, TEXT, rgb

_VERBS: tuple[tuple[str, str], ...] = (
    ("arrow-right", "Open this card's settings"),
    ("arrow-right-left", "Swap for another tool"),
    ("pin", "Pin below the canvas"),
    ("x", "Remove this"),
)

# Public: view.py also reads these via line() to fill the real baseline card.
TITLE = "threshold"
KNOBS: tuple[tuple[str, str], ...] = (("sensitivity", "0.42"), ("min area", "120 px"))

GLYPH = "sliders-horizontal"
FULL = 0.62


def line(knob: tuple[str, str]) -> str:
    """A knob as the single string the card as built shows it as."""
    return f"{knob[0]} — {knob[1]}"


class Look(NamedTuple):
    """A candidate card design: name, gloss, dress callback, shape callback."""

    name: str
    gloss: str
    dress: Callable[[bool], str]
    shape: Callable[["MockCard"], None]
    fade: bool = False


def _as_built(selected: bool) -> str:
    edge = ACCENT if selected else PANEL
    return f"""
        #mock {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(LINE)};
            border-left: 3px solid {rgb(edge)};
        }}
        #mock:hover {{ background: {rgb(PANEL_HOT)}; }}
        #mocktitle {{ color: {rgb(TEXT)}; font-weight: 600; }}
        #mockline {{ color: {rgb(DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _bar(selected: bool) -> str:
    return f"""
        #mock {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(ACCENT if selected else LINE)};
        }}
        #mock:hover {{ background: {rgb(PANEL_HOT)}; }}
        #mockbar {{
            background: {rgb(STACK_BG)};
            border-bottom: 1px solid {rgb(LINE)};
        }}
        #mocktitle {{
            color: {rgb(ACCENT if selected else TEXT)};
            font-weight: 600;
        }}
        #mockname {{ color: {rgb(DIM)}; }}
        #mockvalue {{ color: {rgb(TEXT)}; }}
        #mockmeter {{ background: {rgb(STACK_BG)}; }}
        #mockfull {{ background: {rgb(ACCENT if selected else DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _bar_lines(selected: bool) -> str:
    return f"""
        #mock {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(ACCENT if selected else LINE)};
        }}
        #mock:hover {{ background: {rgb(PANEL_HOT)}; }}
        #mockbar {{
            background: {rgb(STACK_BG)};
            border-bottom: 1px solid {rgb(LINE)};
        }}
        #mocktitle {{
            color: {rgb(ACCENT if selected else TEXT)};
            font-weight: 600;
        }}
        #mockline {{ color: {rgb(DIM)}; }}
        #mockmeter {{ background: {rgb(STACK_BG)}; }}
        #mockfull {{ background: {rgb(ACCENT if selected else DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _bar_values(selected: bool) -> str:
    return f"""
        #mock {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(ACCENT if selected else LINE)};
        }}
        #mock:hover {{ background: {rgb(PANEL_HOT)}; }}
        #mockbar {{
            background: {rgb(STACK_BG)};
            border-bottom: 1px solid {rgb(LINE)};
        }}
        #mocktitle {{
            color: {rgb(ACCENT if selected else TEXT)};
            font-weight: 600;
        }}
        #mockname {{ color: {rgb(DIM)}; }}
        #mockbig {{ color: {rgb(TEXT)}; font-size: 15px; font-weight: 600; }}
        #mockmeter {{ background: {rgb(STACK_BG)}; }}
        #mockfull {{ background: {rgb(ACCENT if selected else DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _bar_collapsed(selected: bool) -> str:
    return f"""
        #mock {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(ACCENT if selected else LINE)};
        }}
        #mock:hover {{ background: {rgb(PANEL_HOT)}; }}
        #mockbar {{
            background: {rgb(STACK_BG)};
            border-bottom: 1px solid {rgb(LINE)};
        }}
        #mocktitle {{
            color: {rgb(ACCENT if selected else TEXT)};
            font-weight: 600;
        }}
        #mocksum {{ color: {rgb(DIM)}; }}
        #mockname {{ color: {rgb(DIM)}; }}
        #mockvalue {{ color: {rgb(TEXT)}; }}
        #mockmeter {{ background: {rgb(STACK_BG)}; }}
        #mockfull {{ background: {rgb(ACCENT if selected else DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _bar_accent(selected: bool) -> str:
    # Selected text uses STACK_BG — light text on accent teal has no contrast.
    strip = ACCENT if selected else STACK_BG
    return f"""
        #mock {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(LINE)};
        }}
        #mock:hover {{ background: {rgb(PANEL_HOT)}; }}
        #mockbar {{
            background: {rgb(strip)};
            border-bottom: 1px solid {rgb(strip if selected else LINE)};
        }}
        #mocktitle {{
            color: {rgb(STACK_BG if selected else TEXT)};
            font-weight: 600;
        }}
        #mockname {{ color: {rgb(DIM)}; }}
        #mockvalue {{ color: {rgb(TEXT)}; }}
        #mockmeter {{ background: {rgb(STACK_BG)}; }}
        #mockfull {{ background: {rgb(ACCENT if selected else DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _bar_numbered(selected: bool) -> str:
    return f"""
        #mock {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(ACCENT if selected else LINE)};
        }}
        #mock:hover {{ background: {rgb(PANEL_HOT)}; }}
        #mockbar {{
            background: {rgb(STACK_BG)};
            border-bottom: 1px solid {rgb(LINE)};
        }}
        #mocklead {{ color: {rgb(ACCENT if selected else DIM)}; font-weight: 600; }}
        #mocktitle {{
            color: {rgb(ACCENT if selected else TEXT)};
            font-weight: 600;
        }}
        #mockname {{ color: {rgb(DIM)}; }}
        #mockvalue {{ color: {rgb(TEXT)}; }}
        #mockmeter {{ background: {rgb(STACK_BG)}; }}
        #mockfull {{ background: {rgb(ACCENT if selected else DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _bar_borderless(selected: bool) -> str:
    return f"""
        #mock {{
            background: {rgb(PANEL_HOT if selected else PANEL)};
            border: 0;
        }}
        #mock:hover {{ background: {rgb(PANEL_HOT)}; }}
        #mockbar {{ background: {rgb(STACK_BG)}; }}
        #mocktitle {{
            color: {rgb(ACCENT if selected else TEXT)};
            font-weight: 600;
        }}
        #mockname {{ color: {rgb(DIM)}; }}
        #mockvalue {{ color: {rgb(TEXT)}; }}
        #mockmeter {{ background: {rgb(STACK_BG)}; }}
        #mockfull {{ background: {rgb(ACCENT if selected else DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _bar_meter_high(selected: bool) -> str:
    # Groove is PANEL (not STACK_BG) — on the body fill, STACK_BG reads as a second divider.
    return f"""
        #mock {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(ACCENT if selected else LINE)};
        }}
        #mock:hover {{ background: {rgb(PANEL_HOT)}; }}
        #mockbar {{
            background: {rgb(STACK_BG)};
            border-bottom: 1px solid {rgb(LINE)};
        }}
        #mocktitle {{
            color: {rgb(ACCENT if selected else TEXT)};
            font-weight: 600;
        }}
        #mockname {{ color: {rgb(DIM)}; }}
        #mockvalue {{ color: {rgb(TEXT)}; }}
        #mockmeter {{ background: {rgb(PANEL)}; }}
        #mockfull {{ background: {rgb(ACCENT if selected else DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _bar_meter_inset(selected: bool) -> str:
    return f"""
        #mock {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(ACCENT if selected else LINE)};
        }}
        #mock:hover {{ background: {rgb(PANEL_HOT)}; }}
        #mockbar {{
            background: {rgb(STACK_BG)};
            border-bottom: 1px solid {rgb(LINE)};
        }}
        #mocktitle {{
            color: {rgb(ACCENT if selected else TEXT)};
            font-weight: 600;
        }}
        #mockname {{ color: {rgb(DIM)}; }}
        #mockvalue {{ color: {rgb(TEXT)}; }}
        #mockmeter {{ background: {rgb(STACK_BG)}; border-radius: 3px; }}
        #mockfull {{
            background: {rgb(ACCENT if selected else DIM)};
            border-radius: 3px;
        }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _bar_meter_divider(selected: bool) -> str:
    return f"""
        #mock {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(ACCENT if selected else LINE)};
        }}
        #mock:hover {{ background: {rgb(PANEL_HOT)}; }}
        #mockbar {{ background: {rgb(STACK_BG)}; }}
        #mocktitle {{
            color: {rgb(ACCENT if selected else TEXT)};
            font-weight: 600;
        }}
        #mockname {{ color: {rgb(DIM)}; }}
        #mockvalue {{ color: {rgb(TEXT)}; }}
        #mockmeter {{ background: {rgb(LINE)}; }}
        #mockfull {{ background: {rgb(ACCENT if selected else DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _bar_percent(selected: bool) -> str:
    return f"""
        #mock {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(ACCENT if selected else LINE)};
        }}
        #mock:hover {{ background: {rgb(PANEL_HOT)}; }}
        #mockbar {{
            background: {rgb(STACK_BG)};
            border-bottom: 1px solid {rgb(LINE)};
        }}
        #mocktitle {{
            color: {rgb(ACCENT if selected else TEXT)};
            font-weight: 600;
        }}
        #mockpct {{ color: {rgb(DIM)}; }}
        #mockname {{ color: {rgb(DIM)}; }}
        #mockvalue {{ color: {rgb(TEXT)}; }}
        #mockmeter {{ background: {rgb(STACK_BG)}; }}
        #mockfull {{ background: {rgb(ACCENT if selected else DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


def _bar_hover(selected: bool) -> str:
    return f"""
        #mock {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(ACCENT if selected else LINE)};
        }}
        #mock:hover {{ background: {rgb(PANEL_HOT)}; }}
        #mockbar {{
            background: {rgb(STACK_BG)};
            border-bottom: 1px solid {rgb(LINE)};
        }}
        #mocktitle {{
            color: {rgb(ACCENT if selected else TEXT)};
            font-weight: 600;
        }}
        #mockname {{ color: {rgb(DIM)}; }}
        #mockvalue {{ color: {rgb(TEXT)}; }}
        #mockmeter {{ background: {rgb(STACK_BG)}; }}
        #mockfull {{ background: {rgb(ACCENT if selected else DIM)}; }}
        QToolButton {{ border: 0; padding: 0 4px; background: transparent; }}
    """


# Fixed so all looks align in the gallery column.
_STRIP = 28
# Body left margin matches strip's leading inset so names align under titles.
_BODY = (8, 7, 8, 8)
_METER = 4


def _chassis(card: MockCard, *pieces: QWidget | QLayout) -> None:
    card.column.setContentsMargins(0, 0, 0, 0)
    card.column.setSpacing(0)
    for piece in pieces:
        if isinstance(piece, QWidget):
            card.column.addWidget(piece)
        else:
            card.column.addLayout(piece)


def _strip_row(card: MockCard, lead: QWidget, *tail: QWidget) -> QWidget:
    bar = QWidget()
    bar.setObjectName("mockbar")
    bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    bar.setFixedHeight(_STRIP)
    inside = QHBoxLayout(bar)
    inside.setContentsMargins(8, 0, 6, 0)
    inside.setSpacing(4)
    inside.addWidget(lead)
    inside.addWidget(_label(TITLE, "mocktitle"), 1)
    for extra in tail:
        inside.addWidget(extra)
    inside.addWidget(card.verbs)
    return bar


def _meter(full: float, height: int = _METER) -> QWidget:
    # WA_StyledBackground on both children — plain QWidget ignores sheet background.
    bar = QWidget()
    bar.setObjectName("mockmeter")
    bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    bar.setFixedHeight(height)

    done = QWidget()
    done.setObjectName("mockfull")
    done.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    inside = QHBoxLayout(bar)
    inside.setContentsMargins(0, 0, 0, 0)
    inside.setSpacing(0)
    filled = max(0, min(1000, round(full * 1000)))
    inside.addWidget(done, filled)
    inside.addStretch(1000 - filled)
    return bar


def _glyph(name: str, colour: QColor) -> QLabel:
    # QLabel not QToolButton — no press semantics. Colour at call site because stylesheets can't reach inside a pixmap.
    label = QLabel()
    label.setPixmap(icons.pixmap(name, colour))
    label.setFixedSize(QSize(icons.SIZE, icons.SIZE))
    return label


def _kind(card: MockCard) -> QLabel:
    return _glyph(GLYPH, ACCENT if card.selected else DIM)


def _shape_head(card: MockCard) -> None:
    card.column.addLayout(_head(_label(TITLE, "mocktitle"), card.verbs))
    for knob in KNOBS:
        card.column.addWidget(_label(line(knob), "mockline"))


def _shape_bar(card: MockCard) -> None:
    _chassis(card, _strip_row(card, _kind(card)), _inset(_knob_grid()), _meter(FULL))


def _shape_bar_lines(card: MockCard) -> None:
    _chassis(card, _strip_row(card, _kind(card)), _inset(_line_stack()), _meter(FULL))


def _shape_bar_values(card: MockCard) -> None:
    grid = QGridLayout()
    grid.setHorizontalSpacing(8)
    grid.setVerticalSpacing(2)
    for row, (name, value) in enumerate(KNOBS):
        grid.addWidget(_label(value, "mockbig"), row, 0)
        label = _label(name, "mockname")
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(label, row, 1)
    grid.setColumnStretch(1, 1)
    _chassis(card, _strip_row(card, _kind(card)), _inset(grid), _meter(FULL))


def _shape_bar_collapsed(card: MockCard) -> None:
    if card.selected:
        body: QLayout = _knob_grid()
    else:
        body = QVBoxLayout()
        body.setSpacing(0)
        body.addWidget(_label(" · ".join(v for _, v in KNOBS), "mocksum"))
    _chassis(card, _strip_row(card, _kind(card)), _inset(body), _meter(FULL))


def _shape_bar_numbered(card: MockCard) -> None:
    lead = _label(str(card.index), "mocklead")
    lead.setFixedWidth(icons.SIZE)
    lead.setAlignment(Qt.AlignmentFlag.AlignCenter)
    _chassis(card, _strip_row(card, lead), _inset(_knob_grid()), _meter(FULL))


def _shape_bar_meter_high(card: MockCard) -> None:
    _chassis(
        card, _strip_row(card, _kind(card)), _meter(FULL), _inset(_knob_grid())
    )


def _shape_bar_meter_inset(card: MockCard) -> None:
    held = QHBoxLayout()
    held.setContentsMargins(8, 0, 8, 8)
    held.addWidget(_meter(FULL, 6))
    body = _inset(_knob_grid())
    body.setContentsMargins(8, 7, 8, 6)
    _chassis(card, _strip_row(card, _kind(card)), body, held)


def _shape_bar_meter_divider(card: MockCard) -> None:
    _chassis(
        card, _strip_row(card, _kind(card)), _meter(FULL, 2), _inset(_knob_grid())
    )


def _shape_bar_percent(card: MockCard) -> None:
    percent = _label(f"{round(FULL * 100)}%", "mockpct")
    _chassis(
        card,
        _strip_row(card, _kind(card), percent),
        _inset(_knob_grid()),
        _meter(FULL),
    )


def _shape_bar_accent(card: MockCard) -> None:
    # Verbs rebuilt with STACK_BG — pixmap colours can't be restyled by sheet.
    if card.selected:
        card.verbs = _verb_row(STACK_BG, STACK_BG)
    lead = _glyph(GLYPH, STACK_BG if card.selected else DIM)
    _chassis(card, _strip_row(card, lead), _inset(_knob_grid()), _meter(FULL))


LOOKS: tuple[Look, ...] = (
    Look(
        "as built, redrawn",
        "the current dress, drawn by this file — if it differs from the real "
        "card above, this file has drifted and is what to fix. The only look "
        "here with no header bar, kept as the thing the rest are changes from",
        _as_built,
        _shape_head,
    ),
    Look(
        "header bar",
        "the title in a full-bleed strip in the ground colour, its kind as an "
        "icon ahead of the name and the verbs at the far end — the head becomes "
        "chrome and everything below it is contents, which is what tells a "
        "reader where one card's values stop. The strip is drawn identically on "
        "both cards, so it stays a strip rather than becoming a second selection "
        "mark. A 4px meter across the foot says how far along the step is, which "
        "is the one number a long crop or a full-clip pass has that no knob row "
        "can hold. Costs a second fill per card, takes the hover tint off the "
        "head, and adds four pixels every card pays whether or not it is running",
        _bar,
        _shape_bar,
    ),
    Look(
        "lines, not a table",
        "the same chassis with `sensitivity — 0.42` per knob instead of two "
        "columns. A line is read as a sentence and a table as data; the table "
        "puts every value in a chain on one x, and the line keeps the knob's "
        "name at the weight of the thing it names. Cheapest to fill from a step "
        "that has not decided how many knobs it has",
        _bar_lines,
        _shape_bar_lines,
    ),
    Look(
        "values first",
        "the numbers at fifteen pixels in the body, reachable from the far side "
        "of the pane, with the step's name left to the strip — the pairing the "
        "old `values first` could not make, since it had to spend the head on an "
        "eyebrow to get the numbers top billing. Costs the most height here, and "
        "a chain nobody has tuned yet is a column of large meaningless numbers",
        _bar_values,
        _shape_bar_values,
    ),
    Look(
        "collapsed until current",
        "values folded to one dim summary line at rest and opened to the table "
        "only on the current card — twenty steps fit in the pane at once, and "
        "the chrome above and below the fold does not move when selection does. "
        "Costs the thing the fold is for: the values you scan a chain for are "
        "the ones now hidden",
        _bar_collapsed,
        _shape_bar_collapsed,
    ),
    Look(
        "accent strip",
        "the lid itself takes the accent on the current card and the border "
        "gives it up — one selection mark instead of two, and it reads from "
        "across the room. This is the arrangement the committed look wrote a "
        "paragraph refusing: with the strip painted differently, the eye reads a "
        "different *kind* of card rather than the same card selected. Drawn so "
        "the refusal can be checked instead of taken. Costs the verbs their "
        "hover tint on the current card — the accent is under them now",
        _bar_accent,
        _shape_bar_accent,
    ),
    Look(
        "numbered strip",
        "the step's index in the lead position instead of its kind — the chain "
        "is ordered and nothing else on the card says so, and the strip says it "
        "for a dozen pixels where the old index rail spent 22 of every card's "
        "width. Costs the lead: a glyph says what kind of step this is before "
        "the name says which one, and a number says neither",
        _bar_numbered,
        _shape_bar_numbered,
    ),
    Look(
        "borderless",
        "the hairline dropped: a dark lid and a dark foot already give the card "
        "a top and a bottom edge, and the gutter holds the sides. Quietest thing "
        "on the bench in a long column. Costs the one thing a border does that a "
        "lid and a gutter cannot — saying where a card ends when the pane behind "
        "it is the card's own colour",
        _bar_borderless,
        _shape_bar,
    ),
    Look(
        "meter under the head",
        "the meter moved from the foot to under the strip, so all the chrome is "
        "one block at the top and the card's bottom edge stays a plain hairline. "
        "Costs the meter its subject: a bar directly under a title is the shape "
        "every installer uses for *this title is loading*, and the eye attaches "
        "it to the header rather than to the step",
        _bar_meter_high,
        _shape_bar_meter_high,
    ),
    Look(
        "inset meter",
        "6px, rounded, held off the card's edges by the body's margin — a bar "
        "with ends reads as a measurement of the card, where a full-bleed 4px "
        "strip reads as an edge that happens to be two colours. Costs about "
        "triple the height, and makes the card look like it contains a control "
        "it does not contain",
        _bar_meter_inset,
        _shape_bar_meter_inset,
    ),
    Look(
        "meter as the divider",
        "no foot at all: the 2px line under the strip is the meter, so progress "
        "costs the card nothing in height over the divider it already had. Costs "
        "legibility, which is the whole point of a meter — on the long full-clip "
        "pass where progress matters most, it is the hardest thing on the card "
        "to see",
        _bar_meter_divider,
        _shape_bar_meter_divider,
    ),
    Look(
        "percent in the strip",
        "the meter's number written out before the verbs, because a bar answers "
        "*roughly how far* at any length and never answers *how much longer*. "
        "Costs the title its room — the strip is four things wide now — and puts "
        "the only text on the card that changes while nothing is being dragged "
        "into twenty cards at once",
        _bar_percent,
        _shape_bar_percent,
    ),
    Look(
        "verbs on hover",
        "the strip holds only the kind and the name until the pointer arrives. "
        "Four icons on every card is twenty-four in a six-step chain, and a "
        "fixed-height strip can drop them and get them back without the card "
        "moving a pixel — which is what made this unaffordable when the head "
        "sized itself. Costs the old thing hover costs: a verb nobody hovers is "
        "a verb nobody finds",
        _bar_hover,
        _shape_bar,
        fade=True,
    ),
)


class MockCard(QFrame):
    """Inert card mock: same step content, dressed and arranged by a Look."""

    def __init__(
        self, look: Look, selected: bool, index: int = 3, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("mock")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(look.dress(selected))
        self._look = look
        self.selected = selected
        self.index = index
        self.verbs = _verb_row()

        self.column = QVBoxLayout(self)
        self.column.setContentsMargins(8, 6, 8, 8)
        self.column.setSpacing(4)
        look.shape(self)

        self._fades = look.fade
        if self._fades:
            self.verbs.setVisible(False)

        palette.CHANGED.connect(self._restyle)

    def _restyle(self) -> None:
        # Full rebuild — pixmap colours baked at creation can't be restyled by sheet.
        self.setStyleSheet(self._look.dress(self.selected))
        _empty(self.column)
        self.verbs = _verb_row()
        self._look.shape(self)
        if self._fades:
            self.verbs.setVisible(False)

    def enterEvent(self, event) -> None:
        if self._fades:
            self.verbs.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        if self._fades:
            self.verbs.setVisible(False)
        super().leaveEvent(event)


def _empty(layout: QLayout) -> None:
    # Must unparent widgets — takeAt alone leaves old children painted underneath.
    while (item := layout.takeAt(0)) is not None:
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()
        inner = item.layout()
        if inner is not None:
            _empty(inner)
            inner.deleteLater()


def _inset(body: QLayout) -> QLayout:
    body.setContentsMargins(*_BODY)
    return body


def _head(title: QLabel, verbs: QWidget) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(4)
    row.addWidget(title, 1)
    row.addWidget(verbs)
    return row


def _knob_grid() -> QGridLayout:
    grid = QGridLayout()
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(8)
    grid.setVerticalSpacing(4)
    for row, (name, value) in enumerate(KNOBS):
        grid.addWidget(_label(name, "mockname"), row, 0)
        value_label = _label(value, "mockvalue")
        value_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        grid.addWidget(value_label, row, 1)
    grid.setColumnStretch(0, 1)
    return grid


def _line_stack() -> QVBoxLayout:
    stack = QVBoxLayout()
    stack.setContentsMargins(0, 0, 0, 0)
    stack.setSpacing(4)
    for knob in KNOBS:
        stack.addWidget(_label(line(knob), "mockline"))
    return stack


def _verb_row(normal: QColor = DIM, active: QColor = ACCENT) -> QWidget:
    # Colours are args because pixmaps bake colour at creation — can't restyle via sheet.
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    for glyph, tip in _VERBS:
        button = QToolButton()
        button.setIcon(icons.icon(glyph, normal, active))
        button.setIconSize(QSize(icons.SIZE, icons.SIZE))
        button.setAutoRaise(True)
        button.setToolTip(tip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(button)
    return row


def _label(text: str, name: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName(name)
    return label
