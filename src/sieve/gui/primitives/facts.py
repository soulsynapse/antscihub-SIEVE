"""The fact list: what is known about one thing, each name beside its answer.

Lifted from `mockup/paper_primitives.py`, where it stands in the `Status and
figure` panel as a two-column grid — *Emits · 32 × 22 blocks*, *Cost · 2.4 ms ·
10% of frame*, *Reads · background subtract*, *Written · no*. It is the fifth
mark, after `pill.py`, `banner.py`, `meter.py` and `empty.py`, and it is the
plainest of the five: a pill says what state a thing is in, a banner says what
happened to it, a meter says how much of something it is, and this says
everything else that is known about it and takes no gesture for any of it.

It is `table.py` turned on its side, and the relationship is worth stating
because it is what decides that these are two files. A table is many rows of the
same facts, so a column is declared at a width and every row puts that fact in
the same place; this is one thing's different facts, so there is no second row to
line up with and a declared width would be a number nobody could check. The
widest name sets the column instead, which is what a `QGridLayout` does for free
and what a table cannot do — a table sized to its widest cell would relay itself
every time a row was added. Same pair of columns, opposite answer to *who picks
the width*, and the reason is the same fact about the data in each.

It arrives on `menu.py`'s and `empty.py`'s grounds rather than ahead of a view:
the tree was already paying. `view/project_list/card.py` writes a project's
`holds` and `opened` as two lines under its name, `view/dev/card_mockups/look.py`
lays its knobs out in a grid of label and value, and the step card the whole
mockup is built around is a name over exactly this list. That is three places
that have each decided how a named fact is written, and the fourth would have
been a fourth.

The name and the value are the same size, and that is the one place this refuses
the tree's usual pairing. `banner.py` and `empty.py` write a name at `name` with
a quiet line under it at `gloss`, and that pair is *vertical* — the second line
is subordinate because it is underneath. Here the two are read across, and a name
set smaller than its value would read as a caption over the column rather than as
the left half of one line. So both take `name` and the ink does the whole of the
telling apart: `DIM` for what the fact is called, `TEXT` for what it says. Which
is the right way round and not the obvious one — the value is the thing the user
came to read, and the name is the label on the drawer.

A value elides and a name does not, and the split is what each is for. The name
is how the fact is found; half a name names nothing, so it sets the column's
floor and the column widens rather than cutting it. The value is what the fact
says, and a long one cut at the right is still a fact partly read. Neither wraps,
which is `table.py`'s rule kept for a reason that file does not have: a wrapped
value would be fine on its own, since there is no row below that has to align
with it, but a block of facts is read by running the eye down the names, and a
list whose rows are different heights is one the eye has to track rather than
scan. A value that genuinely needs a paragraph is not a fact — it is a gloss, and
the head in `view.py` is where a view says that kind of thing.

A fact with no value draws an em dash in `DIM` rather than nothing, and this is
the one thing here the mockup does not draw. A blank right-hand side and a fact
that was never in the list look identical, and they are different claims: *this
was measured and came back empty* against *this does not apply*. The dash is
already the tree's mark for it — `table.py` names `—` as the thing that lands in
a numeric column beside `1.2 MB` — so what happens here is that the idiom gets
written down rather than invented.

There is no rule between the facts and no fill under them. `table.py` argues both
into existence for a list of the same thing repeated, where the hairline is what
lets the eye run along one row across six columns; two columns need no help, and
a rule per fact would turn four lines into a grid of eight cells. What holds this
together is the alignment, which is the whole of what the shape is.
"""

from __future__ import annotations

from typing import NamedTuple, Sequence

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QGridLayout, QLabel, QSizePolicy, QWidget

from sieve.gui import metrics, palette
from sieve.gui.palette import DIM, TEXT, rgb

#: What stands in for a value that is not there. An em dash and not a hyphen or
#: the word "none": it is the width of the type rather than of a minus sign, so a
#: column of them is a column, and it is not a word a caller could also have
#: meant literally.
ABSENT = "—"

#: Between one fact and the next. Tighter than the air between two cards, because
#: these are lines of one paragraph and not things standing near each other — the
#: same reading `empty.py` takes of the gap between its two lines, at the size a
#: run of them rather than a pair of them needs.
_LEAD = 5

#: Between a name and its value. Wide enough that the two columns are two, narrow
#: enough that the eye crosses without losing the line — this is the only thing
#: keeping the pair together, since there is no rule and no fill to do it.
_GAP = 18


def sheet() -> str:
    """The rules for the three kinds of label, for a caller that sets a sheet of
    its own.

    Handed out for `empty.sheet()`'s reason, which is `stack.sheet()`'s: a sheet
    set on an *ancestor* reaches in here, so a view that dresses itself has to be
    able to put these back. Scoped to object names and never to a bare `QLabel`,
    since a rule on the class would reach every label the view holds.
    """
    return f"""
        #factname {{
            color: {rgb(DIM)};
            background: transparent;
            border: 0;
        }}
        #factvalue {{
            color: {rgb(TEXT)};
            background: transparent;
            border: 0;
        }}
        #factabsent {{
            color: {rgb(DIM)};
            background: transparent;
            border: 0;
        }}
    """


class Fact(NamedTuple):
    """One fact: what it is called, and what it says.

    Both are strings and neither is a number, for `view/project_list/project.py`'s
    reason: a widget handed `6` and asked to write *6 sources* would be the place
    a decision about what a source is had been recorded. The caller writes the
    line it wants read, and this puts it where the fact above it is.
    """

    name: str
    value: str = ""


class Facts(QWidget):
    """A column of named facts about one thing, aligned on the names.

    It knows what it looks like and what it was handed, and nothing about what
    any of it means — the same split every primitive here makes. Like `Banner`
    and `Empty` it offers no gesture at all: no focus, no cursor, no answer to
    the pointer. A fact the user can act on is a control and belongs in a
    `Field`; this is the interface stating what it knows.

    As wide as it is given and as tall as its lines need, which is the policy the
    other marks take. The name column is as wide as its widest name and the value
    column takes what is left, so two of these in one card do *not* line up with
    each other unless their names happen to be the same length — which is honest,
    since they are two lists about two things, and a caller wanting one list says
    so by putting the facts in one.
    """

    def __init__(
        self,
        facts: Sequence[Fact] = (),
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # Expanding and not `Preferred`, which is `Empty`'s policy and the one
        # the class docstring's claim actually needs: the values are `Ignored`
        # horizontally, so this widget's own width hint is barely wider than the
        # names, and a `Preferred` list in a card would be handed that hint and
        # elide every value to nothing beside whatever else was in the row.
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._facts: tuple[Fact, ...] = ()
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(_GAP)
        self._grid.setVerticalSpacing(_LEAD)
        # The names take what they need and the values take the rest. Column 0 is
        # left unstretched rather than fixed at a number, which is the whole of
        # this file's difference from `table.py` — see the module docstring.
        self._grid.setColumnStretch(1, 1)

        self.set_facts(facts)
        self.setStyleSheet(sheet())
        # Bound methods, never lambdas: PySide6 drops a connection to a bound
        # method when the receiver goes, where a lambda closing over `self` would
        # keep a dead widget subscribed for the life of the run.
        palette.CHANGED.connect(self._restyle)
        metrics.CHANGED.connect(self._resize)

    def facts(self) -> tuple[Fact, ...]:
        """What is listed, for a caller that built the list out of what it found
        and has to read back what it made."""
        return self._facts

    def set_facts(self, facts: Sequence[Fact]) -> None:
        """Replace the list.

        The whole list and not a fact at a time, for `Empty.set_message`'s
        reason: the facts about a thing change when the thing does, and a setter
        per fact would put a frame on screen pairing one thing's cost with
        another's name. It is also what keeps the name column honest — the widest
        name decides the width, so a fact added alone would relay every line
        above it anyway.
        """
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        self._facts = tuple(facts)
        for row, fact in enumerate(self._facts):
            name = QLabel(fact.name)
            name.setObjectName("factname")
            # Top-aligned rather than centred: the two labels are one line of
            # text, and a name centred against a value that Qt has given a
            # taller box would sit a pixel low for no reason a reader could name.
            self._grid.addWidget(name, row, 0, Qt.AlignmentFlag.AlignTop)
            self._grid.addWidget(_Value(fact.value), row, 1)

        self._resize()

    def _restyle(self) -> None:
        """The three inks again, at the palette now in force. A sheet is a string
        built out of colours as they were, which is the obligation
        `palette.CHANGED` carries."""
        self.setStyleSheet(sheet())
        self.update()

    def _resize(self) -> None:
        """Every label at the size now in force, and the room that needs.

        One role for both columns — see the module docstring on why a name and
        its value are the same size here and not the `name`/`gloss` pair the
        marks written vertically use. Set as a font rather than in the sheet so
        the values can re-elide against it: a size arriving through a stylesheet
        reaches `_Value` as a `FontChange`, which is what that class waits for.

        Its own slot rather than a repaint, for `check.py`'s reason: a size
        changes how much of the column this takes, so the layout has to be told
        and `updateGeometry` is how.
        """
        points = metrics.pt("name")
        for index in range(self._grid.count()):
            widget = self._grid.itemAt(index).widget()
            if widget is None:
                continue
            font = widget.font()
            font.setPointSize(points)
            widget.setFont(font)
        self.updateGeometry()
        self.update()


class _Value(QLabel):
    """What a fact says, kept whole and drawn as much of as there is room for.

    Elided rather than clipped or wrapped, on the module docstring's grounds. The
    full string is held, so a pane widened later brings the rest of it back
    rather than having been thrown away — which is `table._Cell`'s bargain, and
    the reason this is a class and not a `setText` at the call site.
    """

    def __init__(self, text: str) -> None:
        super().__init__()
        self._full = text
        # The dash is a stand-in and not the value, so it is told apart by object
        # name rather than by being written into `_full`: a caller reading back
        # `facts()` gets what it handed in, and a widened pane still has nothing
        # to un-elide.
        self.setObjectName("factvalue" if text else "factabsent")
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        # Ignored, so the grid hands this whatever is left after the names rather
        # than widening the whole list to fit one long value — which is the same
        # arrangement `table._Cell` stands in, with the stretched column playing
        # the part the declared width plays there.
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._elide()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._elide()

    def changeEvent(self, event) -> None:
        """The type size moved, so the same string needs a different cut.

        `FontChange` and not `metrics.CHANGED`, for `table._Cell`'s reason: the
        size arrives as a font set from above, and Qt tells a widget when the
        font it has been given is replaced. Subscribing to the signal instead
        would mean re-eliding against the font that has not reached here yet.
        """
        super().changeEvent(event)
        if event.type() == QEvent.Type.FontChange:
            self._elide()

    def _elide(self) -> None:
        text = self._full or ABSENT
        super().setText(
            self.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, self.width())
        )
