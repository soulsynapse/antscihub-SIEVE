"""How round the cards are and how large each kind of text is, on five sliders.

The second section of preferences to hold anything, and it holds its choices on
the same terms the palette section holds its own: the pick applies where it is
made, the surface you are setting it on is the preview, and so there is no
*apply* and nothing to confirm. That is not a convention borrowed for
consistency — it is forced by what these settings are. The card under these
sliders is a card, drawn at the corner radius the top slider sets and in the
text the four below it set, and a section that made you confirm a corner would
be a section that showed you the old corner while you decided.

Sliders and not fields, because every one of these is a value with a small range
where the *right* answer is whichever looks right and no number names it. A
spin box asks the user to guess and then to look; a slider is a way of looking.
The number is still shown, because it is what has to be typed into the settings
document by someone undoing this by hand, and because "one more than before" is
a thing people want to know they have done.

The text rows read out the size that role is actually drawn at, in points, and
never the trim `metrics.py` stores. The trim is the right thing to *keep* — it
is what survives the base being moved, which is the whole argument of that
module — and the wrong thing to show, because nobody knows what a heading at
"+2" looks like. Move the base and all four readouts move together, which is
also the clearest possible statement of what the base does.

What is *not* here is every rectangle in the tree. `metrics.radius()` reaches
the cards and the panel a card is, and leaves the nav's entries, the palette
rows and the placeholder square — the reasons are in `primitives/sections.py`,
which is where the distinction is drawn rather than restated. A slider called
*card corners* that rounded a scrollbar would be a slider that had stopped being
about cards.

The section writes nothing itself. `metrics.use_radius` and `metrics.use_text`
are what record a choice, for the reason `palette.use()` records the palette:
a size changed by something that is not this card — a hotkey, a future import of
someone else's settings — has to be remembered on the same terms, and a section
that saved its own slider would be right only while it was the only way to move
one.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from sieve.gui import metrics, palette
from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, PANEL_HOT, STACK_BG, TEXT, rgb
from sieve.gui.primitives import Slider

#: The gap between rows and the margin around them, one number for both, for the
#: reason every other column here uses one: the outermost row sits off the
#: panel's edge by the distance it sits off its neighbour.
_GUTTER = 8

#: The widest reading a value can take — a sign, two digits, a space, a unit.
#: Measured rather than fixed at a pixel count, because the readouts are drawn in
#: a size this section can change; held as a string so the measurement is made in
#: whatever font is current when it is asked for.
_WIDEST = "+00 px"


def _sheet() -> str:
    """Scoped to this section's own objects, for the reason `sections.py` gives:
    it is set on a widget standing inside a card whose sheet is already on an
    ancestor, and a bare `QLabel` rule here would reach the card's heading.

    There is no exception to that any more. The sliders dress themselves
    (`primitives/slider.py`), which is where the class-scoped `QSlider` rules
    this used to carry went — they were safe only while this widget held no
    slider it had not made.
    """
    return f"""
        #mvpanel {{
            background: {rgb(PANEL_HOT)};
            border: 1px solid {rgb(LINE)};
        }}
        #mvscroll {{ background: {rgb(PANEL_HOT)}; border: 0; }}
        #mvcolumn {{ background: {rgb(PANEL_HOT)}; }}
        #mvgroup {{
            color: {rgb(DIM)};
            font-size: {metrics.pt("gloss")}pt;
            font-weight: 600;
        }}
        #mvrow {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(LINE)};
        }}
        #mvname {{
            color: {rgb(TEXT)};
            font-size: {metrics.pt("name")}pt;
            font-weight: 600;
        }}
        #mvgloss {{ color: {rgb(DIM)}; font-size: {metrics.pt("gloss")}pt; }}
        #mvvalue {{ color: {rgb(ACCENT)}; font-size: {metrics.pt("name")}pt; }}
        QScrollBar:vertical {{
            background: {rgb(PANEL_HOT)};
            width: 8px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {rgb(LINE)};
            min-height: 24px;
        }}
        QScrollBar::handle:vertical:hover {{ background: {rgb(STACK_BG)}; }}
        QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
        QScrollBar::add-page, QScrollBar::sub-page {{ background: {rgb(PANEL_HOT)}; }}
    """


class MinorVisuals(QWidget):
    """The corner and the four text sizes, grouped, each on its own slider.

    It scrolls, for the reason the palette list does and one more: the rows are
    drawn in a size these rows set, so the height the column wants is not fixed
    even though the number of rows is. A section that assumed its own height
    would be a section that clipped its last slider at the size that made
    reaching that slider urgent.

    The rows are grouped because the two questions are not one question. *How
    round is a card* and *how large is a name* are answered on different days,
    and a flat run of five sliders makes the user find the boundary themselves
    every time they open this.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("mvpanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._rows: list[_Row] = []

        column = QWidget()
        column.setObjectName("mvcolumn")
        stack = QVBoxLayout(column)
        stack.setContentsMargins(_GUTTER, _GUTTER, _GUTTER, _GUTTER)
        stack.setSpacing(_GUTTER)

        stack.addWidget(_heading("corners"))
        corner = _Row(
            "card corners",
            "how far the corner of a card is cut — 0 leaves it square",
            metrics.RADIUS_MIN,
            metrics.RADIUS_MAX,
            "px",
        )
        corner.moved.connect(metrics.use_radius)
        corner.reads(metrics.radius)
        stack.addWidget(corner)
        self._rows.append(corner)

        stack.addSpacing(_GUTTER)
        stack.addWidget(_heading("text size"))
        # The base first and the roles under it, which is the order the controls
        # are reached in: one slider answers everything being too small, and the
        # three below it trim the sizes *relative to each other*.
        base = _Row(
            "everything",
            "the size the application is set in, and what the three below are off",
            metrics.SIZE_MIN,
            metrics.SIZE_MAX,
            "pt",
        )
        base.moved.connect(metrics.use_size)
        base.reads(metrics.size)
        stack.addWidget(base)
        self._rows.append(base)

        for text in metrics.TEXTS:
            # The slider moves in trim and the readout says points, so the two
            # are separate arguments — see the module docstring.
            row = _Row(
                text.label,
                text.gloss,
                metrics.TRIM_MIN,
                metrics.TRIM_MAX,
                "pt",
                shown=lambda role=text.key: metrics.pt(role),
            )
            row.moved.connect(lambda points, role=text.key: metrics.use_text(role, points))
            row.reads(lambda role=text.key: metrics.trim(role))
            stack.addWidget(row)
            self._rows.append(row)

        # A stretch under the last row: this column is shorter than the panel at
        # any size a slider here can reach, and the slack pooled at the foot
        # reads as the list ending.
        stack.addStretch(1)

        scroll = QScrollArea()
        scroll.setObjectName("mvscroll")
        scroll.setWidget(column)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        body = QVBoxLayout(self)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(scroll)

        self._restyle()
        palette.CHANGED.connect(self._restyle)
        # This section's own rows are what emit `CHANGED`, and every row is told
        # here rather than keeping the value it just set. Moving the base changes
        # what all three trim rows read out with none of their sliders moving.
        metrics.CHANGED.connect(self._refresh)

    def _restyle(self) -> None:
        """Wear the palette and the sizes now in use, and say the values again.

        Both, and not the sheet alone: the readouts are sized in a font this
        sheet sets, and the width they are held at is measured in that font
        (`_Row.refresh`). A restyle that left the widths alone would size the
        text and not the box around it.
        """
        self.setStyleSheet(_sheet())
        self._refresh()

    def _refresh(self) -> None:
        for row in self._rows:
            row.refresh()


def _heading(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("mvgroup")
    return label


class _Row(QFrame):
    """One setting: its name, what it is for, a slider, and where that lands.

    The name and the readout share the top line and the gloss has the next to
    itself, which is what lets the gloss be a sentence rather than a fragment
    cut to fit beside a control. The slider is under both and takes the row's
    whole width — the range is small enough that a short slider would put two
    values on one pixel, and there is nothing to its right worth the room. That
    the wheel rolls past it rather than moving it is `primitives/slider.py`'s,
    and matters most here: these rows live in a scroll deep enough to need one.

    It reports where it was dragged to and sets nothing. Which is the same split
    the palette rows make and for the stronger reason here: the value this row
    *shows* is not always the value its slider holds, so a row that wrote its
    own readout on being dragged would have to know the arithmetic between the
    two — which is `metrics.py`'s, and is exactly what changes when the base
    moves under it.
    """

    #: The slider was dragged, or arrowed, to this. The number is in whatever
    #: units the row's slider is in, which for the trim rows is not points.
    moved = Signal(int)

    def __init__(
        self,
        name: str,
        gloss: str,
        low: int,
        high: int,
        unit: str,
        shown=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("mvrow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        self._unit = unit
        #: What the slider is at, and what the row says it is at. The same
        #: function on the rows where the two agree, which is every row but the
        #: three trims — see the class docstring.
        self._held = lambda: low
        self._shown = shown

        title = QLabel(name)
        title.setObjectName("mvname")

        self._value = QLabel()
        self._value.setObjectName("mvvalue")
        self._value.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(_GUTTER)
        head.addWidget(title, 1)
        head.addWidget(self._value)

        note = QLabel(gloss)
        note.setObjectName("mvgloss")
        note.setWordWrap(True)

        self._slider = Slider(low, high)
        self._slider.valueChanged.connect(self.moved)

        column = QVBoxLayout(self)
        column.setContentsMargins(8, 6, 8, 6)
        column.setSpacing(2)
        column.addLayout(head)
        column.addWidget(note)
        column.addSpacing(2)
        column.addWidget(self._slider)

    def reads(self, held) -> None:
        """Where this row's slider sits, as a question rather than an answer.

        Handed a callable and not a number, because the row is rebuilt from it
        every time anything changes and the value at construction is only the
        first of those. It also keeps this file from holding a copy of any
        setting: `metrics.py` is asked, always, and there is nowhere here for
        the two to drift apart.
        """
        self._held = held
        self.refresh()

    def refresh(self) -> None:
        """Put the slider where the setting is and say what that comes to.

        `show_value` is the silent move and is what makes this safe to call from
        the slot the slider's own move ends up in — which is exactly where it is
        called from, since every row refreshes on `metrics.CHANGED` and one of
        the rows is what caused it.
        """
        self._slider.show_value(self._held())
        shown = self._shown() if self._shown is not None else self._held()
        self._value.setText(f"{shown} {self._unit}")
        # Measured now rather than fixed at a pixel count, because the font this
        # is drawn in is one of the things these rows set: the widest reading is
        # a different width at 7pt and at 20.
        self._value.setFixedWidth(self._value.fontMetrics().horizontalAdvance(_WIDEST))
