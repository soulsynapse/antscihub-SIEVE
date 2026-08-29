"""Styled popup menu with grouped verbs, captions, and shortcut columns.

A checked row is lit by its word going to the accent, never by a tick:
`QMenu::indicator` takes its whole appearance from an `image:` the moment a
sheet touches it, and a bitmap cannot follow a palette changed mid-run.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QLabel, QMenu, QWidget, QWidgetAction

from sieve.gui import metrics, palette
from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, PANEL_HOT, TEXT, rgb

_ITEM_LEFT = 20
_ITEM_RIGHT = 28
_ITEM_Y = 5

_PAD_Y = 4

_RULE_Y = 4
_RULE_X = 8

_CAPTION_TOP = 8
_CAPTION_BOTTOM = 3

_CAPTION_TRACK = 1.2


def sheet() -> str:
    """Stylesheet rules for all dropped menus; callers with their own sheet must include these.

    Anchored to `QMenu` by class — the one departure from this package's
    object-name rule. A menu is a popup window, not a widget in a pane, so the
    bare selector cannot reach into the panes; naming each menu would give a
    view that forgot the name the platform's list beside the tree's.
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
    """Self-dressing popup menu that follows palette and metrics changes."""

    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(title, parent)
        self._dress()
        # Bound methods so PySide6 drops the connection when the receiver dies.
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
        """Add a verb. Disabled when ``on`` is None; ``reason`` tooltips a disabled row."""
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
        """Add a non-interactive group heading above subsequent verbs."""
        label = QLabel(caption, self)
        label.setObjectName("menucaption")
        holder = QWidgetAction(self)
        holder.setDefaultWidget(label)
        holder.setEnabled(False)
        self.addAction(holder)
        return holder

    def separator(self) -> QAction:
        return self.addSeparator()

    def submenu(self, title: str) -> Menu:
        """Add a child Menu (not a bare QMenu) so palette connections propagate."""
        child = Menu(title, self)
        self.addMenu(child)
        return child

    # -- what it wears -----------------------------------------------------

    def _dress(self) -> None:
        self.setStyleSheet(sheet())
