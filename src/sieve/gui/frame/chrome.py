"""What the window wears where no pane covers it.

Selectors are anchored to the splitter or to named objects, never to bare widget
classes — those reach into the panes and fight the views' own stylesheets.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QWidget

from sieve.gui import palette
from sieve.gui.palette import ACCENT, LINE, PANEL, PANEL_HOT, STACK_BG, TEXT, rgb
from sieve.gui.primitives import menu


def stylesheet() -> str:
    return f"""
        QMainWindow, QSplitter {{ background: {rgb(STACK_BG)}; }}
        QSplitter::handle {{ background: {rgb(LINE)}; }}
        QSplitter::handle:horizontal {{ width: 3px; }}
        QSplitter::handle:vertical {{ height: 3px; }}
        QSplitter::handle:hover {{ background: {rgb(ACCENT)}; }}
        #seam {{ background: {rgb(LINE)}; }}
        #bottom {{ background: {rgb(STACK_BG)}; }}
        #bottom QLabel {{ color: {rgb(TEXT)}; }}

        /* Menu bar: closes with the same hairline the seams use. */
        #menubar {{
            background: {rgb(STACK_BG)};
            color: {rgb(TEXT)};
            border-bottom: 1px solid {rgb(LINE)};
            padding: 2px 4px;
        }}
        #menubar::item {{ background: transparent; padding: 4px 10px; }}
        #menubar::item:selected {{ background: {rgb(PANEL_HOT)}; }}
        #menubar::item:pressed {{ background: {rgb(PANEL)}; }}

        /* Drop-down menu rules live in primitives/menu.py. */
        {menu.sheet()}

        /* Dialogs are not panes — scope to the class. */
        QMessageBox {{ background: {rgb(PANEL)}; }}
        QMessageBox QLabel {{ color: {rgb(TEXT)}; }}
    """


def dress_title_bar(window: QWidget) -> None:
    """Set DWM dark-mode title bar to match the palette.

    Re-called on every palette change — some palettes want the light bar back.
    Attr 20 is DWMWA_USE_IMMERSIVE_DARK_MODE; fails silently on older Windows.
    """
    if sys.platform != "win32":
        return
    try:
        from ctypes import byref, c_int, windll

        dark = c_int(1 if palette.current().dark else 0)
        windll.dwmapi.DwmSetWindowAttribute(int(window.winId()), 20, byref(dark), 4)
    except (OSError, AttributeError, ImportError):
        pass
