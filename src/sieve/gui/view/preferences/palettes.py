"""The palettes on offer, light then dark, with the one in use marked.

The first section of preferences to hold anything, and it holds a choice the
rest of the card cannot: a palette is the one setting whose effect is the card
you are setting it on. So the pick applies where it is made — the whole tree
redresses under the pointer — and the row is the preview, which is why there is
no *apply* and nothing to confirm.

What a row shows is the palette's own colours and not the current ones. Every
other surface in the application follows `palette.CHANGED`; the swatches are the
one thing that must not, because they are what the choice is *between*, and a
strip that redrew itself in the palette already in use would show every row
identical. They are set once, from literals, and never restyled.

Which palettes there are, what each is for, and how they sort into dark and
light is `palette.py`'s — this file draws them and reads none of the values. It
is the split preferences makes everywhere else too: the view is where a setting
is reachable, never where its content is decided.

The pick outlasts the run, and nothing here writes it. `palette.use()` is what
records it, so a palette changed by something that is not this section is
remembered on the same terms — the same reason the mark is moved off
`palette.CHANGED` and not off the click. This section reports a row was picked;
what that means, and how long it lasts, is the palette's.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor
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

#: The gap between rows and the margin around them, one number for both, for the
#: reason every other column here uses one: the outermost row sits off the
#: panel's edge by the distance it sits off its neighbour.
_GUTTER = 8

#: How wide the accent edge on the chosen row is, and how wide the same edge is
#: on every other — only its colour changes, so a row's text does not step
#: sideways as the selection arrives (`primitives/nav.py` makes the same point).
_EDGE = 3

#: One swatch, and the six roles a strip shows. Not all eight: `scrim` is
#: translucent and would draw as whatever is behind it, and `dim` sits between
#: `text` and `line` closely enough that a 14px block cannot tell the three
#: apart. What is left is the run a palette is actually recognised by — its two
#: grounds, the panel a card is, the hairline, the ink, and the accent.
_SWATCH = 14
_ROLES = ("stack_bg", "panel", "panel_hot", "line", "text", "accent")


def _sheet() -> str:
    """Scoped to this section's own objects, for the reason `sections.py` gives:
    it is set on a widget standing inside a card whose sheet is already on an
    ancestor, and a bare `QLabel` rule here would reach the card's heading."""
    return f"""
        #palettes {{
            background: {rgb(PANEL_HOT)};
            border: 1px solid {rgb(LINE)};
        }}
        #pscroll {{ background: {rgb(PANEL_HOT)}; border: 0; }}
        #pcolumn {{ background: {rgb(PANEL_HOT)}; }}
        #pgroup {{
            color: {rgb(DIM)};
            font-size: {metrics.pt("gloss")}pt;
            font-weight: 600;
        }}
        #prow {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(LINE)};
            border-left: {_EDGE}px solid {rgb(PANEL)};
        }}
        #prow:hover {{ background: {rgb(PANEL_HOT)}; }}
        #prow[chosen="true"] {{ border-left-color: {rgb(ACCENT)}; }}
        #pname {{
            color: {rgb(TEXT)};
            font-size: {metrics.pt("name")}pt;
            font-weight: 600;
        }}
        #pgloss {{ color: {rgb(DIM)}; font-size: {metrics.pt("gloss")}pt; }}
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


class Palettes(QWidget):
    """Every palette as a row, under the two headings, one of them chosen.

    It scrolls, because the list is a catalogue and a section that fixed its own
    height would be a section deciding how many palettes are allowed.

    The rows are grouped rather than sorted into one run: light against dark is
    the first thing the user is choosing between, and a flat list of every name
    at once makes them find the boundary themselves every time they open this.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("palettes")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._rows: list[_Row] = []

        column = QWidget()
        column.setObjectName("pcolumn")
        stack = QVBoxLayout(column)
        stack.setContentsMargins(_GUTTER, _GUTTER, _GUTTER, _GUTTER)
        stack.setSpacing(_GUTTER)
        # Light first, and this is the section's order rather than
        # `palette.PALETTES`'. That sequence is dark-first because dark is the
        # default and the longer list; a chooser is answering a different
        # question, and the group a user is most often coming here to *find* is
        # the one that is not already on. Reached by filtering the one sequence
        # twice rather than by concatenating two, so the order within a group
        # stays the palette module's to decide.
        for dark, heading in ((False, "light"), (True, "dark")):
            label = QLabel(heading)
            label.setObjectName("pgroup")
            stack.addWidget(label)
            for entry in palette.PALETTES:
                if entry.dark != dark:
                    continue
                row = _Row(entry)
                row.chosen.connect(palette.use)
                stack.addWidget(row)
                self._rows.append(row)
        # No stretch under the last row, unlike every other column here. A
        # stretch is what keeps a short list at the top of its panel, and this
        # list is not short — it is taller than the card, so the stretch would
        # never be holding anything up. What it would do instead is take the
        # slack between what the rows ask for and what the scroll gives them and
        # pool it into one block of empty ground under the last palette, which
        # reads as the end of the list arriving early. Spread across the rows it
        # is a few pixels each and reads as the rows being roomy.

        scroll = QScrollArea()
        scroll.setObjectName("pscroll")
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
        # The rows carry the two text sizes, so a size change is this sheet
        # again. The swatches are untouched by either signal — they are drawn
        # from literals and never restyled, which is the whole point of them.
        metrics.CHANGED.connect(self._restyle)

    def _restyle(self) -> None:
        """Wear the palette now in use, and move the mark to the row that is it.

        Both on the one signal rather than on the click: the palette can be
        changed by something that is not this widget, and a section that marked
        the row it was told about would be right only while it was the only way
        to change one.
        """
        self.setStyleSheet(_sheet())
        for row in self._rows:
            row.mark(row.scheme is palette.current())


class _Row(QFrame):
    """One palette: its name, what it is for, and a strip of its own colours.

    It reports being picked and marks nothing — the section holds which row is
    chosen, for the reason the nav holds it rather than its entries: the one
    thing true of the whole column is that exactly one is, and a row that
    decided for itself would have to hear about all the others to stop being it.

    The pointer is the only way in. ↑ and ↓ inside the card belong to the
    section nav and mean *the next section*, and a list that took them would
    trap the keyboard in whichever section happened to hold one.
    """

    #: The palette on this row was asked for. Carried rather than looked up by
    #: index, so the section can wire it straight to `palette.use`.
    chosen = Signal(object)

    def __init__(self, entry: palette.Palette, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("prow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # The height a row wants depends on the width it is given, because the
        # gloss wraps. Said out loud, or the column asks each row how tall it is
        # without saying how wide it will be — every gloss answers as if it had
        # wrapped to two lines, and the scroll ends up with a screen of nothing
        # under the last palette.
        policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)

        #: Not `self.palette`: `QWidget.palette()` is Qt's own, called from
        #: inside the style machinery, and an attribute of that name replaces it
        #: with something that is not callable and does not return a `QPalette`.
        self.scheme = entry

        name = QLabel(entry.name)
        name.setObjectName("pname")
        gloss = _Gloss(entry.gloss)

        words = QVBoxLayout()
        words.setContentsMargins(0, 0, 0, 0)
        words.setSpacing(1)
        words.addWidget(name)
        words.addWidget(gloss)

        row = QHBoxLayout(self)
        row.setContentsMargins(8, 6, 8, 6)
        row.setSpacing(_GUTTER)
        row.addLayout(words, 1)
        for role in _ROLES:
            row.addWidget(_swatch(getattr(entry, role), entry.line))

    def mark(self, chosen: bool) -> None:
        """Wear the accent edge, or give it back.

        A dynamic property and not a re-set sheet, unlike the nav's entries: the
        rows hold swatches whose colours are theirs and not the palette's, and a
        per-row stylesheet is the thing most likely to grow a rule that reaches
        one. The unpolish/polish pair is what makes a property take.
        """
        if self.property("chosen") == chosen:
            return
        self.setProperty("chosen", chosen)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.chosen.emit(self.scheme)
        super().mousePressEvent(event)


class _Gloss(QLabel):
    """What a palette is for, wrapping, and honest about how tall that leaves it.

    Wrapping is what keeps the swatches on the card: a label that does not wrap
    reports its whole run of text as the width it must have, so the row's
    minimum would be the longest gloss and the strip would be pushed off the
    right edge with no horizontal scrollbar to reach it.

    But `QLabel.sizeHint()` on a wrapping label is a guess made without a width.
    Qt picks a shape it thinks reads well and answers two lines for a sentence
    that will land on one, and the column here lives in a scroll, which sizes
    its contents from that hint — so the guess becomes a screen of empty space
    under the last palette. Asked at the width the label actually has, the
    answer is right; `resizeEvent` is where it becomes possible to ask, which is
    why the geometry is invalidated there.
    """

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("pgloss")
        self.setWordWrap(True)
        policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)

    def sizeHint(self) -> QSize:
        hint = super().sizeHint()
        if self.width() <= 0:
            return hint
        return QSize(hint.width(), self.heightForWidth(self.width()))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Only on a change of width, which is the only thing the answer depends
        # on: an unconditional `updateGeometry` is a relayout on every resize,
        # and a relayout that can resize this label again is a loop.
        if event.size().width() != event.oldSize().width():
            self.updateGeometry()


def _swatch(colour: QColor, edge: QColor) -> QWidget:
    """One role of one palette, at its own colour, inside that palette's own
    hairline.

    The hairline is not decoration. A row is drawn on the panel fill of whatever
    palette is *in use*, so a dark palette's `panel` swatch shown while a dark
    palette is on is a block the same colour as the ground under it — the one
    role in the strip that would vanish is the one the whole application is
    mostly made of. Bordered in the swatch's own palette's `line`, the strip
    shows that palette against itself and stays legible on either ground.

    Dressed from literals and left alone: this is the one drawing in the tree
    that does not follow `palette.CHANGED`, because it is showing a palette that
    is mostly not the one in use. Given no object name the section's sheet
    mentions, so nothing there can reach in and repaint it.
    """
    block = QFrame()
    block.setFixedSize(_SWATCH, _SWATCH)
    block.setStyleSheet(f"background: {rgb(colour)}; border: 1px solid {rgb(edge)};")
    return block
