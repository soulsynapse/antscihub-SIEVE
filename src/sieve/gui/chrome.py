"""The colours the window is drawn in, and the two sheets that apply them.

One home for the palette because two homes is how a card and the gap it sits in
stop matching. Every surface that paints itself — the cards, the rail, the plots
— reads the constants here; every surface Qt paints reads one of the two
stylesheets below.

**The two sheets are separate because their selectors must not meet.** The
window's is anchored to `QMainWindow` and `QSplitter` and never to a bare widget
class: a `QWidget` or `QLabel` rule set on the window reaches down into the stack
and the plots, and the two sheets would then fight over every card. The stack's
is `.QWidget` — instances of exactly `QWidget`, not subclasses — which is what
keeps the background off the scrollbars: a plain `QWidget` selector reaches
`QScrollBar` too, and any rule on a scrollbar makes Qt draw the whole complex
control from the stylesheet, groove and arrows and a handle no longer
distinguishable from the track. v2 styles nothing there and gets the platform's,
which is the one this is meant to match.

The consequence for a widget that wants the stack's background is that it must be
a plain `QWidget` or paint its own — a subclass is deliberately outside the
selector, not accidentally.
"""

from __future__ import annotations

import sys

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget

#: The gap between cards, and every surface behind them.
STACK_BG = QColor(24, 26, 30)
#: A card's fill.
PANEL = QColor(31, 33, 38)
#: A control's fill, and a card's fill under the cursor.
PANEL_HOT = QColor(38, 41, 47)
#: A hairline: a card's edge when it is not the walk's.
LINE = QColor(55, 58, 66)
TEXT = QColor(230, 231, 235)
DIM = QColor(139, 142, 152)
#: What "current" looks like — the selected card's edge, and nothing else's.
ACCENT = QColor(94, 200, 180)


def rgb(color: QColor) -> str:
    """`color` as a stylesheet function call."""
    return f"rgb({color.red()},{color.green()},{color.blue()})"


def window_stylesheet() -> str:
    """The surface the panes leave uncovered: the window's own, and the seams."""
    return f"""
        QMainWindow, QSplitter {{ background: {rgb(STACK_BG)}; }}
        QSplitter::handle {{ background: {rgb(LINE)}; }}
        QSplitter::handle:horizontal {{ width: 3px; }}
        QSplitter::handle:vertical {{ height: 3px; }}
        QSplitter::handle:hover {{ background: {rgb(ACCENT)}; }}
    """


def stack_stylesheet() -> str:
    """The stack's own surface: every position that holds cards wears this."""
    return f"""
        .QWidget {{ background: {rgb(STACK_BG)}; }}
        QLabel {{ color: {rgb(TEXT)}; }}
        QDoubleSpinBox, QSpinBox, QComboBox {{
            background: {rgb(PANEL_HOT)};
            color: {rgb(TEXT)};
            border: 1px solid {rgb(LINE)};
            padding: 1px 3px;
        }}
        QScrollArea {{ border: 0; }}
    """


def darken_title_bar(window: QWidget) -> None:
    """Ask DWM for the dark frame, since Qt does not carry the palette there.

    The title bar is the OS's, not Qt's: without this the window wears the system
    light frame over a dark app whatever the stylesheet says. Attribute 20 is
    `DWMWA_USE_IMMERSIVE_DARK_MODE`; on anything that is not a recent Windows the
    call simply fails and the frame stays the platform's, which is why every way
    it can fail is swallowed rather than reported — there is nothing a caller
    could do with the news, and a window that refused to open over a title bar
    would be trading the app for its chrome.
    """
    if sys.platform != "win32":
        return
    try:
        from ctypes import byref, c_int, windll

        windll.dwmapi.DwmSetWindowAttribute(int(window.winId()), 20, byref(c_int(1)), 4)
    except (OSError, AttributeError, ImportError):
        pass
