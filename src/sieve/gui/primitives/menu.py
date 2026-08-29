"""The menu: a list of verbs standing over the work, grouped, with its keys shown.

Lifted from `mockup/paper_primitives.py`, and the sixth surface. It is not a
control — nothing here holds a value — and it is not a mark, because it takes
the one gesture a mark refuses: it is the room a verb is *chosen* in, which is
what a card's ⇄, a right-click on a row and every title on the window's bar all
open.

It arrives later than the argument for it did. `select.py` needed a list that
appears over the work, found the question already answered in `frame/chrome.py`,
took that answer deliberately over the mockup's, and then had to write the rules
out a second time — because Qt scopes a popup's sheet through the widget that
owns it, and a combo's popup is not on the window. That was two copies of one
decision with nothing between them but a comment naming which was the original,
and the third caller was always going to be a view. So the decision moves here,
where a decision that more than one file draws from belongs, and chrome keeps
the window it dresses rather than also being the tree's answer to *what does a
dropped list look like*.

The name it shares with `frame/menu.py` is the honest one for both, and the
split is worth saying out loud: that file is *what the window's menus contain* —
which verbs the frame can be asked for, in what order, disabled where the wiring
has not landed — and this is *what any dropped menu looks like*, the window's
included. Neither knows the other's half, which is why a card that grows a
context menu takes this without going near the frame.

Three of the mockup's decisions are declined, each on a case already argued in
this package.

The danger red goes on `button.py`'s grounds, and it is the same refusal
`pill.py` and `banner.py` make: a hue past the accent is a ninth role every
palette below has to answer. What the mockup paints red is a destructive verb,
and what carries that here is the word — *Delete project*, not a coloured
*Delete* — which is the same bargain the banner strikes when four kinds cost no
role at all.

The accent wash under the highlighted row goes on `chrome.py`'s, which is not a
refusal so much as the point of moving the file: the highlight is `PANEL_HOT`,
the step every hovered thing in this tree takes, so a dropped select and a
dropped menu are one object on one screen.

The corner goes, and this one is Qt rather than taste. A menu is a top-level
popup window; a `border-radius` on one leaves the four corners outside the
rounded path unpainted rather than transparent, and making them transparent
means `WA_TranslucentBackground` and a compositor that agrees. `metrics.radius()`
is *card corners* and every control here declines to follow it — this declines
the mockup's fixed radius as well, and what the eye actually uses to tell a menu
from the pane under it is the hairline and the shadow the platform already puts
behind a popup.

What is kept from the mockup and is not in chrome is the two things that make a
menu of fifteen verbs readable rather than a wall: the captioned group, and the
shortcut standing in its own column at the right. The caption is a disabled row
holding a label rather than Qt's own `addSection`, whose drawing is the
platform's — the same reason `segmented.py` does not use a `QTabBar`. The
shortcut is Qt's: an action that has one already draws it right-aligned, so what
this file supplies is the room for it, and a menu whose keys are set on the
actions gets the column for free.

A checked item is lit by its word going to the accent and not by a tick, and
that is `check.py`'s trap rather than a preference. `QMenu::indicator` takes its
whole appearance from an `image:` the moment a sheet touches it, so a tick means
shipping a bitmap that does not follow a palette the user changes mid-run. The
mockup already lights the word; a stylesheet can do that in a live role, and the
indicator is left to the platform for the menus that want one.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QLabel, QMenu, QWidget, QWidgetAction

from sieve.gui import metrics, palette
from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, PANEL_HOT, TEXT, rgb

#: The room inside a row. `_ITEM_RIGHT` is where the shortcut column lives as
#: well as the air past it, which is why it is wider than `_ITEM_LEFT`: the key
#: stands off the hairline. A menu with no shortcuts keeps the column, so adding
#: one to a single entry leaves every other row's text where it is.
_ITEM_LEFT = 20
_ITEM_RIGHT = 28
_ITEM_Y = 5

#: The air the list keeps at its own top and bottom. None at the sides, so a
#: highlighted row runs edge to edge inside the hairline and reads as *this
#: row*.
_PAD_Y = 4

#: The separator's hairline and the air around it, and how far it is held off
#: each end. Inset rather than full width, so a rule between two groups reads as
#: a divider inside the list.
_RULE_Y = 4
_RULE_X = 8

#: Where a group's caption sits. Deeper at the top than at the bottom, because a
#: caption belongs to what is under it.
_CAPTION_TOP = 8
_CAPTION_BOTTOM = 3

#: How far the caption's letters are spread. A word set in `gloss` and `DIM` is
#: quiet enough to miss in a column of verbs; tracking makes it read as a heading
#: at the same weight and size. Not uppercased, for `table.py`'s reason — that
#: edits the caller's word.
_CAPTION_TRACK = 1.2


def sheet() -> str:
    """The dress every dropped list in the tree wears.

    Anchored to `QMenu` and not to an object name, which is the one place this
    package departs from the rule the rest of it keeps. A menu is a popup
    *window* rather than a widget standing in a pane, so a bare class selector
    here cannot reach down into whatever the panes come to hold — the risk
    `chrome.py`'s own docstring names — and naming each menu would mean a view
    that forgot the name got the platform's list beside the tree's.

    Handed out as a string for the reason `view.sheet()` is: a caller that sets
    a sheet of its own on the window, or on a widget that owns a popup, replaces
    what was there, and has to include these back.
    """
    return f"""
        QMenu {{
            background: {rgb(PANEL)};
            color: {rgb(TEXT)};
            border: 1px solid {rgb(LINE)};
            padding: {_PAD_Y}px 0;
            font-size: {metrics.pt("name")}pt;
        }}
        QMenu::item {{
            padding: {_ITEM_Y}px {_ITEM_RIGHT}px {_ITEM_Y}px {_ITEM_LEFT}px;
            background: transparent;
        }}
        QMenu::item:selected {{ background: {rgb(PANEL_HOT)}; }}
        QMenu::item:checked {{ color: {rgb(ACCENT)}; }}
        QMenu::item:disabled {{ color: {rgb(DIM)}; }}
        QMenu::separator {{
            height: 1px;
            background: {rgb(LINE)};
            margin: {_RULE_Y}px {_RULE_X}px;
        }}
        #menucaption {{
            color: {rgb(DIM)};
            font-size: {metrics.pt("gloss")}pt;
            letter-spacing: {_CAPTION_TRACK}px;
            padding: {_CAPTION_TOP}px {_ITEM_RIGHT}px {_CAPTION_BOTTOM}px {_ITEM_LEFT}px;
        }}
    """


class Menu(QMenu):
    """A list of verbs, optionally grouped, that dresses itself and keeps doing so.

    It knows what it looks like and what it was told to offer, and nothing about
    what choosing means — every entry is handed the callable it fires, which is
    the caller's, the same split every primitive here makes.

    Subclassed rather than offered as a `dress(menu)` function so that the
    redress on `palette.CHANGED` has somewhere to hang. A menu built once and
    kept — a card's context menu is exactly that — would otherwise be the one
    thing on screen still wearing the greys it was built in, and a menu rebuilt
    on every right-click is a cost paid to avoid a connection.
    """

    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(title, parent)
        self._dress()
        # A bound method and never a lambda, for the reason `button.py` gives:
        # PySide6 drops a connection to a bound method when the receiver goes,
        # where a lambda closing over `self` keeps a dead menu subscribed.
        palette.CHANGED.connect(self._dress)
        metrics.CHANGED.connect(self._dress)

    # -- what it offers ----------------------------------------------------

    def add(
        self,
        text: str,
        on: Callable[[], None] | None = None,
        *,
        shortcut: str = "",
        enabled: bool = True,
        checked: bool | None = None,
        reason: str = "",
    ) -> QAction:
        """One verb, with the key that reaches it and what it does.

        `on` is optional and `enabled` is separate from it, because those are two
        different absences: a verb the frame cannot do yet is built and disabled
        so the menu shows its shape from the start — `frame/menu.py`'s bargain —
        and a verb that is real but not available *now* is disabled with a
        `reason` in its tooltip. A disabled row wearing the tooltip it had when it
        worked says what it would do and not why it will not, which is the same
        refusal `card.py` makes for its ✕.

        `checked` is `None` for the ordinary verb and a bool for a row that
        states which of something is in force — lit by the accent on its word,
        never by a tick. See the module docstring on why.
        """
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(shortcut)
        if checked is not None:
            action.setCheckable(True)
            action.setChecked(checked)
        if on is not None:
            action.triggered.connect(on)
        action.setEnabled(enabled and on is not None)
        if reason and not action.isEnabled():
            action.setToolTip(reason)
        self.addAction(action)
        return action

    def group(self, caption: str) -> QAction:
        """A heading over the verbs that follow it.

        A `QWidgetAction` holding a label rather than `addSection`, whose drawing
        is the platform's — and disabled, so the pointer walks past it instead of
        highlighting a row that cannot be chosen. The label carries no sheet of
        its own: it is a child of this menu, so the `#menucaption` rule in
        `sheet()` reaches it, and it is redressed with everything else when the
        palette moves.

        A caption and not a separator, and the two are different tools: a rule
        says *these are apart*, a caption says *these are the export ones*. A
        menu long enough to want grouping usually wants the second, and
        `separator()` is still here for the one place a rule alone is honest.
        """
        label = QLabel(caption, self)
        label.setObjectName("menucaption")
        holder = QWidgetAction(self)
        holder.setDefaultWidget(label)
        holder.setEnabled(False)
        self.addAction(holder)
        return holder

    def separator(self) -> QAction:
        """A rule between two runs of verbs that need no name between them."""
        return self.addSeparator()

    def submenu(self, title: str) -> Menu:
        """A `Menu` under one of this menu's rows, and not a bare `QMenu`.

        The dress reaches a submenu either way — Qt gives a child menu its
        parent's stylesheet — but the connection does not, and a submenu built as
        a plain `QMenu` would be the branch of the tree that stops following the
        palette. One line here is cheaper than that being true only sometimes.
        """
        child = Menu(title, self)
        self.addMenu(child)
        return child

    # -- what it wears -----------------------------------------------------

    def _dress(self) -> None:
        """The sheet again in the palette and at the size now in use.

        One slot for both signals, unlike `card.py`'s two: everything this menu
        wears is a stylesheet, there are no pixmaps to redraw, and the two
        changes cost exactly the same work.
        """
        self.setStyleSheet(sheet())
