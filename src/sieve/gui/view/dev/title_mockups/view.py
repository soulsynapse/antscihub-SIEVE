"""The heads laid out one under another, each over a stub of the pane it heads.

Every look is drawn twice, side by side, holding a short name and a long one.
That is the pair this gallery has instead of the cards' at-rest-and-selected:
nothing about a head changes with state, and everything about it changes with
how much room the name is left — so the two drawings are the two names, and a
look that reads well on the left and elides to `colony 7 — entr…` on the right
is a look whose cost is visible rather than argued.

Each drawing carries two blank cards under the head. Half of these looks are
arguments about the boundary between the head and the contents — `rule under`
and `filled strip` are about nothing else — and a head drawn over empty ground
would show every one of them separating the pane from nothing. The stubs are
blank on purpose: they are there to be a border and a fill at the right
distance, and a stub holding a title would be a second thing on screen making a
claim about titles.

The column, the ground and the block each look sits in are the bench's
(`gallery.py`), which leaves this file holding only the pair and the pane.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from sieve.gui.palette import LINE, PANEL, STACK_BG, rgb
from sieve.gui.view.dev.gallery import GUTTER, Gallery, Variant
from sieve.gui.view.dev.title_mockups.look import LONG_NAME, LOOKS, NAME, Look, MockHead

#: How wide a mock pane is drawn. Fixed rather than sharing the row, because
#: every argument here is an answer to a width and two panes of different widths
#: in one row would be comparing looks and widths at once. Near what the left
#: pane gives the library at an even split, which is where these will be seen.
_PANE = 300

#: How tall a stub card is drawn. Enough to read as a card rather than as a
#: rule, and no taller: what is being judged is the first few pixels under the
#: head, and a pane of full-height cards would push the next look off the bench.
_STUB = 26


def _sheet() -> str:
    """The pane's own ground and the stubs on it, scoped to this section's
    objects — it stands inside the gallery, whose sheet is set on an ancestor,
    and a bare-class rule here would be the second stylesheet reaching the
    labels inside every mock head.

    The pane is given an edge it does not paint for itself. In the window that
    line is the splitter's seam or the window's own border (`frame/panes.py`
    draws it), and here it is the only thing saying where the pane stops — a
    head that bleeds to the edge and a head inset from it are the same drawing
    once the edge is invisible, which is half of what `filled strip` is about.
    """
    return f"""
        #pane {{ background: {rgb(STACK_BG)}; border: 1px solid {rgb(LINE)}; }}
        #stub {{ background: {rgb(PANEL)}; border: 1px solid {rgb(LINE)}; }}
    """


class TitleMockups(Gallery):
    """Every candidate pane head, drawn at both the lengths a name arrives in."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            (Variant(look.name, look.gloss, _pair(look)) for look in LOOKS), parent
        )


def _pair(look: Look) -> QWidget:
    """One look at both names, with the labels saying which is which.

    Both panes fixed to `_PANE` and a stretch after them: the width is the whole
    question, and a pair that grew with the bench would be judged at a width no
    splitter will ever be dragged to.

    Pinned to the top of the row rather than stretched to match, so a look that
    is taller than its neighbour — `tally under the name`, `name at fifteen` —
    shows that as height, which is the cost it is being charged for.
    """
    short = QLabel("a short name")
    short.setObjectName("vgloss")
    long = QLabel("a long one")
    long.setObjectName("vgloss")

    labels = QHBoxLayout()
    labels.setSpacing(GUTTER)
    labels.addWidget(short, 0)
    labels.addSpacing(_PANE - short.sizeHint().width())
    labels.addWidget(long, 0)
    labels.addStretch(1)

    panes = QHBoxLayout()
    panes.setSpacing(GUTTER)
    panes.addWidget(_pane(look, NAME), 0, Qt.AlignmentFlag.AlignTop)
    panes.addWidget(_pane(look, LONG_NAME), 0, Qt.AlignmentFlag.AlignTop)
    panes.addStretch(1)

    pair = QWidget()
    pair.setStyleSheet(_sheet())
    stack = QVBoxLayout(pair)
    stack.setContentsMargins(0, 0, 0, 0)
    stack.setSpacing(2)
    stack.addLayout(labels)
    stack.addLayout(panes)
    return pair


def _pane(look: Look, title: str) -> QWidget:
    """A head over the top of the column it heads.

    The stubs are inset by the head's own margin and spaced by it, which is what
    makes the gap under the head comparable across looks: the distance from the
    last thing in the head to the first card is the head's bottom margin plus
    this spacing, in every drawing, so a look that appears to sit closer to the
    contents is one that actually does.
    """
    pane = QWidget()
    pane.setObjectName("pane")
    pane.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    pane.setFixedWidth(_PANE)

    column = QVBoxLayout(pane)
    column.setContentsMargins(0, 0, 0, MockHead.MARGIN)
    column.setSpacing(MockHead.MARGIN)
    column.addWidget(MockHead(look, title))
    for _ in range(2):
        stub = QFrame()
        stub.setObjectName("stub")
        stub.setFixedHeight(_STUB)
        row = QHBoxLayout()
        row.setContentsMargins(MockHead.MARGIN, 0, MockHead.MARGIN, 0)
        row.addWidget(stub)
        column.addLayout(row)
    return pane
