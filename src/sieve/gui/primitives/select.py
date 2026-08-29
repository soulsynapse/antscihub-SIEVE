"""The select: one of many, from a list that is not standing open.

Lifted from `mockup/paper_primitives.py`, and the fifth control after
`button.py`, `field.py`, `slider.py` and `check.py`. It arrives ahead of a view
asking, the way the first two did, and the budget it settles is *what a list that
appears over the work looks like* — which is spent by the first dropdown, the
first completer and the first inline menu alike, and would otherwise be set by
whichever of them landed first.

It is the third answer to "pick one" and the split between the three is the
whole reason there are three. A radio (`check.py`) is a fixed few, all of them
visible, each one a fact the user can read without acting — a codec's two modes.
A section list (`sections.py`) is a few, visible, and picking one *moves* you.
This is many: a set too long to stand open at all, where the cost of hiding the
options is paid back by the row not being twelve lines tall. The question a view
should ask itself is how many, and it has an answer at each size rather than one
control that stretches badly across all three.

The popup takes the menu's dress and not the mockup's, and that is a deliberate
departure. `menu.py` answers what a list appearing over the work looks like — a
`PANEL` fill inside a `LINE` hairline, with the highlighted row in `PANEL_HOT` —
and the mockup's accent wash under the highlighted item would make a dropped
select and a dropped menu two different objects on one screen. The rule is
restated here rather than reached for, because a combo's popup is a
`QAbstractItemView` and not a `QMenu`, so there is no selector the two can share;
what is not restated is the decision, which is `menu.py`'s. It was chrome's when
this file was written, and these two copies with a comment between them are the
reason it moved.

The chevron is painted and not styled, for `check.py`'s reason exactly.
`QComboBox::down-arrow` takes its whole appearance from an `image:` the moment a
sheet touches it, so an arrow in the tree's greys means shipping a bitmap that
does not follow a palette the user changes mid-run. Two line segments read the
live roles at the moment of drawing and need nothing said to them.

Focus is a ring drawn outside the box, which means a `Field` around it — this is
a *styled* control like `LineField` and not a painted one like `Check`, and a
stylesheet cannot draw outside its own rect. That is also why the corner is
`field.RADIUS` rather than a 4 named here: `Field` draws the ring at its
control's corner plus the inset, and a select with a corner of its own would get
a ring that does not follow the box it is around.

The wheel is refused unless the select already has focus, and that is not in the
mockup because the mockup has nothing to scroll. Qt's own combo takes the wheel
whenever the pointer is over it, so a select sitting in a column of settings
changes its value as the user scrolls past — a silent edit to a stored choice,
made by a gesture that meant *move down the page*. Focus is the test because it
is what the user does to say they are on this control.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QComboBox, QStyledItemDelegate, QWidget

from sieve.gui import metrics, palette
from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, PANEL_HOT, TEXT, mix, rgb
from sieve.gui.primitives.field import EDGE, EDGE_HOVER, RADIUS

#: The box around the current item. `_PAD_RIGHT` is the room the chevron is drawn
#: in as well as the air beside it, which is why it is wider than `_PAD_X`: the
#: text stops clear of the mark that says this is a list.
_PAD_X = 8
_PAD_Y = 4
_PAD_RIGHT = 24

#: The chevron: how wide, how far it falls, how thick, and how far its right
#: point sits in from the box's edge. Rounded at the ends and the join, so the
#: two segments read as one stroke — the treatment the tick in `check.py` gets,
#: for the same reason at the same size.
_MARK_W = 8.0
_MARK_H = 3.5
_MARK_PEN = 1.4
_MARK_INSET = 9.0

#: How much of the popup's own height one row takes, and the air it keeps from
#: the list's edge. Stated here rather than left to Qt, because a sheet that
#: dresses the view at all takes over its metrics.
_ITEM_PAD_X = 10
_ITEM_PAD_Y = 5


class Select(QComboBox):
    """A row of text with a chevron, and the list it stands for.

    It knows what it looks like and nothing about what choosing means, which is
    `currentIndexChanged` and the caller's — the same split every primitive here
    makes. Handed its options rather than fetching any: what is on offer is the
    view's, and a select that reached for a list of estimators would be the one
    file where two views' contents met.
    """

    def __init__(
        self,
        options: list[str] | None = None,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("select")
        self._hovered = False
        if options:
            self.addItems(options)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Asked for explicitly, as `card.py` and `check.py` do: this widget
        # paints the chevron's colour, so it has to be told about the hover
        # state rather than leaving it to the sheet.
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        # As wide as its longest option and no wider. The mockup's fixed width
        # suits a select holding the same three words everywhere; here the
        # options are a view's, and every one of them stays readable.
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        # Qt's own combo delegate draws its rows without consulting the
        # stylesheet, so `::item` rules reach nothing until the plain styled
        # delegate is put back. Without this the popup wears the palette and the
        # rows keep the platform's metrics.
        self.setItemDelegate(QStyledItemDelegate(self))
        self._dress()
        # Bound methods and never lambdas, for the reason `button.py` gives:
        # PySide6 drops a connection to a bound method when the receiver goes,
        # where a lambda closing over `self` keeps a dead select subscribed.
        palette.CHANGED.connect(self._dress)
        metrics.CHANGED.connect(self._dress)

    def _dress(self) -> None:
        """The sheet, in the palette and at the size now in use.

        Scoped to `#select` rather than to `QComboBox`, for the reason
        `field.py` gives: this stands inside a card whose sheet is set on an
        ancestor, and a bare class rule would reach every combo in the pane.

        The fill is `PANEL` and the edge is a field's, because that step off
        `LINE` is the whole of what "the user may change this" is made of in
        this tree — a select that wore a lighter fill would be a `SUBTLE` button
        with a chevron on it.

        The native arrow is not hidden by width alone: `image: none` is what
        stops the platform pixmap being drawn, and the zero width is what stops
        it reserving room the painted one is already paying for.
        """
        self.setStyleSheet(f"""
            #select {{
                background: {rgb(PANEL)};
                color: {rgb(TEXT)};
                border: 1px solid {rgb(mix(LINE, TEXT, EDGE))};
                border-radius: {RADIUS}px;
                padding: {_PAD_Y}px {_PAD_RIGHT}px {_PAD_Y}px {_PAD_X}px;
                font-size: {metrics.pt("name")}pt;
            }}
            #select:hover {{ border-color: {rgb(mix(LINE, TEXT, EDGE_HOVER))}; }}
            #select:focus {{ border-color: {rgb(ACCENT)}; }}
            #select:disabled {{
                background: {rgb(PANEL_HOT)};
                color: {rgb(DIM)};
                border-color: {rgb(LINE)};
            }}
            #select::drop-down {{ border: 0; width: 0; background: transparent; }}
            #select::down-arrow {{ image: none; width: 0; height: 0; }}

            /* The dropped list, in the dress `menu.py` gives a menu. */
            #select QAbstractItemView {{
                background: {rgb(PANEL)};
                color: {rgb(TEXT)};
                border: 1px solid {rgb(LINE)};
                outline: 0;
                selection-background-color: {rgb(PANEL_HOT)};
                selection-color: {rgb(TEXT)};
            }}
            #select QAbstractItemView::item {{
                padding: {_ITEM_PAD_Y}px {_ITEM_PAD_X}px;
            }}
        """)

    def wheelEvent(self, event) -> None:
        """Scroll the choice only when this is the control the user is on.

        Ignored rather than swallowed when it is not: an ignored wheel event
        goes up to whatever is scrolling, so the column moves as the user meant
        rather than stopping dead over each select on the way down.
        """
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        """The box from the sheet, then the chevron over it.

        `super()` first and not last: the sheet draws the fill, the border and
        the current item, and a mark painted before them would be painted over
        by the box it is supposed to sit in.
        """
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        right = self.width() - _MARK_INSET
        middle = self.height() / 2
        mark = QPainterPath(QPointF(right - _MARK_W, middle - _MARK_H / 2))
        mark.lineTo(right - _MARK_W / 2, middle + _MARK_H / 2)
        mark.lineTo(right, middle - _MARK_H / 2)
        # `DIM` at rest and the ink under the pointer, the quieter half of what
        # the hover says — the border has moved too, and the accent is reserved
        # for the selection.
        if not self.isEnabled():
            ink = DIM
        else:
            ink = TEXT if (self._hovered or self.hasFocus()) else DIM
        pen = QPen(ink, _MARK_PEN)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(mark)
        painter.end()
