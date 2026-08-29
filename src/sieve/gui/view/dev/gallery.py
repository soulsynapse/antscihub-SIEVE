"""A scrolling column of alternatives, each under its name and its argument.

The frame the card mock ups drew, lifted out of them once a second section
turned out to want the same picture — and lifted rather than copied for the
reason `primitives/sections.py` was: two sections drawing one column from two
files is two places a gutter, a ground colour or a scrollbar can come to differ,
and a gallery whose blocks are spaced differently from the gallery beside it is
one where the spacing reads as something the looks are saying.

What it owns is the column: the ground the alternatives are seen on, the scroll
that lets the list outgrow the bench, and the block a variant is drawn in — its
name, the sentence saying what it costs, the drawing, and the rule under it. What
it does not own is the drawing, or anything inside it: whether a variant is one
widget or a pair with captions over them is the section's, since that is the
question the section exists to ask.

The ground is `STACK_BG` and not the panel fill the rest of the bench wears,
because that is what a pane's contents are really seen against — a look whose
whole claim is a panel fill would vanish into a panel background, and the gallery
would be showing a fault the application does not have.
"""

from __future__ import annotations

from typing import Iterable, NamedTuple

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sieve.gui import metrics, palette
from sieve.gui.palette import DIM, LINE, PANEL, PANEL_HOT, STACK_BG, TEXT, rgb

#: The gap between blocks and the margin around the column, one number for both,
#: for the reason the project list uses one.
GUTTER = 10


class Variant(NamedTuple):
    """One alternative on the bench: what it is called, what it costs, and the
    drawing of it.

    `gloss` is the half worth reading. A gallery of shapes with no argument under
    them is a mood board, and none of these choices is about which is prettiest —
    they are about what a column of twenty, or a pane of one, does to the eye
    while a slider is being dragged.
    """

    name: str
    gloss: str
    drawing: QWidget


def sheet() -> str:
    """The gallery's own rules, for a section that sets a sheet of its own.

    A section standing inside a gallery is standing inside a card whose sheet is
    already set on an ancestor, so its own rules have to be scoped to object
    names the way these are — and it needs these back, because a second
    stylesheet set on a child widget replaces nothing but reaches everything
    under it.

    `#vgloss` is here rather than in the sections for the same reason the block
    is: it is what a caption inside a drawing is drawn in as well as what the
    argument under a name is drawn in, and two files answering *what does a quiet
    line in the gallery look like* is one of them being wrong later.
    """
    return f"""
        #gallery {{ background: {rgb(STACK_BG)}; border: 1px solid {rgb(LINE)}; }}
        #gscroll {{ background: {rgb(STACK_BG)}; border: 0; }}
        #gcolumn {{ background: {rgb(STACK_BG)}; }}
        #vname {{
            color: {rgb(TEXT)};
            font-size: {metrics.pt("name")}pt;
            font-weight: 600;
        }}
        #vgloss {{ color: {rgb(DIM)}; font-size: {metrics.pt("gloss")}pt; }}
        #vrule {{ background: {rgb(LINE)}; }}
        QScrollBar:vertical {{
            background: {rgb(STACK_BG)};
            width: 8px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {rgb(LINE)};
            min-height: 24px;
        }}
        QScrollBar::handle:vertical:hover {{ background: {rgb(PANEL_HOT)}; }}
        QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
        QScrollBar::add-page, QScrollBar::sub-page {{ background: {rgb(PANEL)}; }}
    """


class Gallery(QWidget):
    """The alternatives one under another, scrolling.

    It scrolls because any list of these outgrows the bench long before the list
    is finished, and a section that fixed its own height would be a section
    deciding how many alternatives are allowed.
    """

    def __init__(
        self, variants: Iterable[Variant], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("gallery")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        column = QWidget()
        column.setObjectName("gcolumn")
        stack = QVBoxLayout(column)
        stack.setContentsMargins(GUTTER, GUTTER, GUTTER, GUTTER)
        stack.setSpacing(GUTTER)
        for variant in variants:
            stack.addWidget(_block(variant))
        # Last, so a short list sits at the top of the panel.
        stack.addStretch(1)

        #: Held so a restyle can wake it — see `_restyle`.
        self._scroll = QScrollArea()
        self._scroll.setObjectName("gscroll")
        self._scroll.setWidget(column)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        body = QVBoxLayout(self)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._scroll)

        # Last, because the restyle reaches for the scroll and there has to be
        # one to reach for.
        self._restyle()
        palette.CHANGED.connect(self._restyle)
        metrics.CHANGED.connect(self._restyle)

    def _restyle(self) -> None:
        """The gallery's own rules again, and the scroll told to measure again.

        The second half is not optional here, and it is this scroll and not
        every scroll that needs it. A `QScrollArea` sizes the widget it holds
        from that widget's hint, and it recomputes on a layout request — one it
        has already answered by the time the drawings inside have finished
        changing shape, because a section's rebuild happens in a slot on the
        same signal. Left alone the column keeps the height it wanted before,
        and every block in it is squeezed to fit a column shorter than its
        contents.

        Deferred to a zero timer rather than posted as an event, and that is not
        style. Qt compresses queued layout requests: one posted while the
        scroll's own is still in the queue is dropped on the floor, and the
        surviving one is the early answer that was wrong. A timer is a different
        queue and cannot be folded into that, so it lands after the whole
        emission — whichever order the slots on `CHANGED` ran in.
        """
        self.setStyleSheet(sheet())
        QTimer.singleShot(0, self, self._remeasure)

    def _remeasure(self) -> None:
        """Ask the scroll to size its contents again, now that they have
        stopped changing shape."""
        QApplication.sendEvent(self._scroll, QEvent(QEvent.Type.LayoutRequest))


def _block(variant: Variant) -> QWidget:
    """One variant: what it is called, what it costs, the drawing, and the rule
    that says where the next one starts."""
    block = QWidget()

    title = QLabel(variant.name)
    title.setObjectName("vname")
    note = QLabel(variant.gloss)
    note.setObjectName("vgloss")
    note.setWordWrap(True)

    rule = QFrame()
    rule.setObjectName("vrule")
    rule.setFixedHeight(1)

    stack = QVBoxLayout(block)
    stack.setContentsMargins(0, 0, 0, 0)
    stack.setSpacing(4)
    stack.addWidget(title)
    stack.addWidget(note)
    stack.addWidget(variant.drawing)
    stack.addSpacing(2)
    stack.addWidget(rule)
    return block
